"""Nhãn yếu BIO cho WM2 (tập train PhoBERT): tag kỹ năng của chính tin + từ điển alias, đem dò trong câu.

    uv run python -m ie.weak_labels                      # sinh data/weak/wm2_weak_v1.bio.jsonl
    uv run python -m ie.weak_labels --eval-only          # chỉ đo độ chính xác nhãn yếu trên dev

- Nguồn tag: VietJobs `technical_skills`, TopCV `skill_tags` (bỏ tag kỹ năng mềm – lấy từ cột `soft_skills` của VietJobs).
- **Không lấy câu của tin thuộc dev (skill_batch1) hay test (skill_test1)** – loại theo job_uid trong manifest.
- Đo trên dev: cùng cách gán đem áp lên 300 câu dev đã gán tay (tag của chính tin dev), chấm seqeval strict.
  Đây là ước lượng độ nhiễu của tập train, không phải kết quả mô hình.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from seqeval.metrics import f1_score, precision_score, recall_score
from seqeval.scheme import IOB2

from annotation.export_bio import TOKEN_RE
from annotation.preannotate_dict import SKIP_ALIASES, load_aliases
from annotation.sample_skill_batch import SECTIONS, mask_pii, split_sentences
from ie.baseline_dict import build_index, tag

ROOT = Path(__file__).resolve().parents[1]
VIETJOBS = ROOT / "data" / "vietjobs" / "it_v1.parquet"
TOPCV = ROOT / "data" / "crawl" / "topcv" / "topcv_v1.parquet"
MANIFESTS = [ROOT / "data" / "annotation" / f"{b}.manifest.json" for b in ("skill_batch1", "skill_test1")]
DEV_BIO = ROOT / "data" / "annotation" / "skill_batch1.bio.jsonl"
OUT = ROOT / "data" / "weak" / "wm2_weak_v1.bio.jsonl"
VERSION = "weak-tags+dict-v1"


def _list(v) -> list[str]:
    return [] if v is None else [str(x).strip() for x in v if str(x).strip()]


def clean_tags(tags: list[str], soft: set[str]) -> list[str]:
    """Bỏ kỹ năng mềm, tag quá ngắn hoặc quá dài (cụm mô tả), alias bị loại trong từ điển."""
    out = []
    for t in tags:
        n_tok = len(TOKEN_RE.findall(t))
        if t.lower() in soft or t in SKIP_ALIASES or len(t) < 2 or n_tok > 5:
            continue
        out.append(t)
    return out


def excluded_uids(paths: list[Path] = MANIFESTS) -> set[str]:
    uids: set[str] = set()
    for p in paths:
        uids |= set(json.loads(p.read_text(encoding="utf-8"))["job_uids"])
    return uids


def label_tokens(tokens: list[str], forms: list[str]) -> list[str]:
    index, max_len = build_index(forms)
    return tag(tokens, index, max_len)


def postings(soft: set[str]) -> list[dict]:
    """Mỗi tin: job_uid, nguồn, câu (description + requirements), tag kỹ năng đã lọc."""
    vj = pd.read_parquet(VIETJOBS)
    out = [
        {
            "job_uid": r["job_uid"],
            "source": "vietjobs",
            "texts": {c: r[c] for c in SECTIONS},
            "tags": clean_tags(_list(r["technical_skills"]), soft),
        }
        for r in vj.to_dict("records")
    ]
    if TOPCV.exists():
        for r in pd.read_parquet(TOPCV).to_dict("records"):
            out.append(
                {
                    "job_uid": r["job_uid"],
                    "source": "topcv",
                    "texts": {c: r[c] for c in SECTIONS},
                    "tags": clean_tags(_list(r["skill_tags"]), soft),
                }
            )
    return out


def soft_vocab() -> set[str]:
    vj = pd.read_parquet(VIETJOBS, columns=["soft_skills"])
    return {s.lower() for v in vj["soft_skills"] for s in _list(v)}


def eval_on_dev(dict_forms: list[str], tags_by_uid: dict[str, list[str]]) -> dict[str, dict[str, float]]:
    rows = [json.loads(x) for x in DEV_BIO.read_text(encoding="utf-8").splitlines() if x]
    gold = [r["tags"] for r in rows]
    kw = {"mode": "strict", "scheme": IOB2}
    variants = {
        "dict": lambda r: label_tokens(r["tokens"], dict_forms),
        "tags": lambda r: label_tokens(r["tokens"], tags_by_uid.get(r["job_uid"], []) or ["\x00"]),
        "tags+dict": lambda r: label_tokens(r["tokens"], dict_forms + tags_by_uid.get(r["job_uid"], [])),
    }
    res = {}
    for name, fn in variants.items():
        pred = [fn(r) for r in rows]
        res[name] = {
            "precision": precision_score(gold, pred, **kw),
            "recall": recall_score(gold, pred, **kw),
            "f1": f1_score(gold, pred, **kw),
        }
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-only", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    soft = soft_vocab()
    dict_forms = load_aliases()
    posts = postings(soft)
    tags_by_uid = {p["job_uid"]: p["tags"] for p in posts}

    print(f"Nhãn yếu trên dev {DEV_BIO.name} (so với nhãn tay, seqeval strict):")
    for name, m in eval_on_dev(dict_forms, tags_by_uid).items():
        print(f"  {name:10s} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")
    if args.eval_only:
        return

    held_out = excluded_uids()
    n_sent = n_pos = n_span = 0
    used = {"vietjobs": 0, "topcv": 0}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for p in posts:
            if p["job_uid"] in held_out:
                continue
            used[p["source"]] += 1
            forms = dict_forms + p["tags"]
            index, max_len = build_index(forms)
            for col, sec in SECTIONS.items():
                for i, sent in enumerate(split_sentences(p["texts"][col])):
                    tokens = TOKEN_RE.findall(mask_pii(sent))
                    tags = tag(tokens, index, max_len)
                    k = tags.count("B-SKILL")
                    n_sent += 1
                    n_pos += k > 0
                    n_span += k
                    rec = {"id": f"{p['job_uid'][:12]}-{sec}{i:02d}", "job_uid": p["job_uid"], "source": p["source"]}
                    f.write(json.dumps({**rec, "tokens": tokens, "tags": tags}, ensure_ascii=False) + "\n")
    print(
        f"{VERSION}: {used} tin (đã loại {len(held_out)} tin dev/test) → {n_sent} câu, "
        f"{n_pos} câu có kỹ năng, {n_span} span → {args.out}"
    )


if __name__ == "__main__":
    main()
