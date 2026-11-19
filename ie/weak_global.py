"""Nhãn yếu kho tag chung cho WM2: thêm từ điển gom từ kho tag toàn cục (mọi tin VietJobs + TopCV) vào nhãn self-training.

    uv run python -m ie.weak_global --eval-only    # chỉ đo độ nhiễu trên dev
    uv run python -m ie.weak_global                # sinh data/weak/wm2_weak_globaltag.bio.jsonl

Cấu hình theo mục đăng ký trước "Cải thiện nhãn yếu WM2" trong `experiments/results.md` – không đổi sau khi xem số.

- Ở các bộ nhãn trước, mỗi tin chỉ được dò bằng tag của chính nó; tên công cụ hiếm mà tin không gắn tag thì bị bỏ sót.
- Từ điển chung: `technical_skills` của toàn bộ VietJobs (mọi ngành) + `skill_tags` TopCV, lọc bằng `clean_tags`,
  giữ tag có ở ≥ MIN_JOBS tin khác nhau. Tin thuộc dev/test không được đếm.
- Bộ này = nhãn self-training + span dò bằng từ điển chung ở chỗ còn trống (không đè span cũ), rồi qua luật 0.4 (`refine`).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from seqeval.metrics import f1_score, precision_score, recall_score
from seqeval.scheme import IOB2

from annotation.preannotate_dict import load_aliases
from ie.baseline_dict import build_index, spans, tag
from ie.vietjobs import DEFAULT_CSV, load
from ie.weak_labels import DEV_BIO, WEAK_DIR, _list, clean_tags, excluded_uids, label_tokens, postings
from ie.weak_rules import refine

ROOT = Path(__file__).resolve().parents[1]
TOPCV = ROOT / "data" / "crawl" / "topcv" / "topcv_20261118.parquet"
MIN_JOBS = 3


def global_vocab(csv: Path = DEFAULT_CSV, min_jobs: int = MIN_JOBS) -> tuple[list[str], set[str]]:
    """Trả (danh sách dạng viết của tag giữ lại, từ vựng kỹ năng mềm)."""
    vj = load(csv)
    soft = {s.lower() for v in vj["soft_skills"] for s in _list(v)}
    held = excluded_uids()
    jobs: list[list[str]] = [
        list(r) for u, r in zip(vj["job_uid"], vj["technical_skills"], strict=True) if u not in held
    ]
    if TOPCV.exists():
        tv = pd.read_parquet(TOPCV, columns=["job_uid", "skill_tags"])
        jobs += [_list(r) for u, r in zip(tv["job_uid"], tv["skill_tags"], strict=True) if u not in held]
    n_jobs: Counter[str] = Counter()
    forms: dict[str, Counter[str]] = defaultdict(Counter)
    for tags in jobs:
        keep = clean_tags(tags, soft)
        for t in keep:
            forms[t.lower()][t] += 1
        n_jobs.update({t.lower() for t in keep})
    vocab = [forms[k].most_common(1)[0][0] for k, n in n_jobs.items() if n >= min_jobs]
    print(f"kho tag: {len(jobs)} tin, {len(n_jobs)} tag khác nhau; giữ {len(vocab)} tag có ở ≥ {min_jobs} tin")
    return vocab, soft


def add_spans(tokens: list[str], base: list[str], extra: list[str]) -> list[str]:
    """Thêm span của `extra` vào chỗ `base` còn trống, không đè span cũ; rồi qua luật 0.4."""
    out = list(base)
    for a, b, _ in spans(tokens, extra):
        if all(t == "O" for t in out[a:b]) and (b >= len(out) or out[b] != "I-SKILL"):
            out[a] = "B-SKILL"
            out[a + 1 : b] = ["I-SKILL"] * (b - a - 1)
    return refine(tokens, out)


def eval_dev(vocab: list[str], soft: set[str]) -> None:
    rows = [json.loads(x) for x in DEV_BIO.read_text(encoding="utf-8").splitlines() if x]
    tags_by_uid = {p["job_uid"]: p["tags"] for p in postings(soft)}
    dict_forms = load_aliases()
    g_index, g_max = build_index(vocab)
    gold = [r["tags"] for r in rows]
    rules = [label_tokens(r["tokens"], dict_forms + tags_by_uid.get(r["job_uid"], []), "rules") for r in rows]
    glob = [add_spans(r["tokens"], p, tag(r["tokens"], g_index, g_max)) for r, p in zip(rows, rules, strict=True)]
    kw = {"mode": "strict", "scheme": IOB2}
    print(f"Nhãn yếu trên dev {DEV_BIO.name} (so với nhãn tay, seqeval strict):")
    for name, pred in (("tag+dict+luật", rules), ("tag+dict+luật + kho chung", glob)):
        p, r, f = (fn(gold, pred, **kw) for fn in (precision_score, recall_score, f1_score))
        print(f"  {name:16s} P={p:.3f} R={r:.3f} F1={f:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-only", action="store_true")
    ap.add_argument("--src", type=Path, default=WEAK_DIR / "wm2_weak_selftrain.bio.jsonl")
    ap.add_argument("--out", type=Path, default=WEAK_DIR / "wm2_weak_globaltag.bio.jsonl")
    args = ap.parse_args()

    vocab, soft = global_vocab()
    eval_dev(vocab, soft)
    if args.eval_only:
        return
    g_index, g_max = build_index(vocab)
    added: Counter[str] = Counter()
    n_sent = n_pos = n_span = 0
    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for line in args.src.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            before = {(a, b) for a, b, _ in spans(r["tokens"], r["tags"])}
            tags = add_spans(r["tokens"], r["tags"], tag(r["tokens"], g_index, g_max))
            added.update(s for a, b, s in spans(r["tokens"], tags) if (a, b) not in before)
            k = tags.count("B-SKILL")
            n_sent += 1
            n_pos += k > 0
            n_span += k
            f.write(json.dumps({**r, "tags": tags}, ensure_ascii=False) + "\n")
    print(
        f"kho tag chung: {n_sent} câu, {n_pos} câu có kỹ năng, {n_span} span (thêm {sum(added.values())}) → {args.out}"
    )
    print("Span thêm nhiều nhất:", added.most_common(40))


if __name__ == "__main__":
    main()
