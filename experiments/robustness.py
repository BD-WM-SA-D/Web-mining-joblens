"""Độ bền của dedup (WM1) và trích kỹ năng (WM2) khi văn bản tin bị nhiễu – theo mục đăng ký trước trong
`experiments/results.md` ("Độ bền với nhiễu"). Chỉ đo: không chỉnh hệ, ngưỡng, từ điển hay model.

    uv run python -m experiments.robustness wm1
    uv run python -m experiments.robustness wm2            # cần nhóm ml và model data/models/wm2-phobert-v3-s<N>

Nhiễu tất định: cùng seed + cùng job_uid (hoặc id câu) → cùng biến đổi. Nhãn giữ nguyên vì nhiễu không đổi
nghĩa tin. WM2 chỉ dùng biến đổi trong từng token nên số token và nhãn BIO không lệch.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path

SEED = 20261118
RATE_WM1 = 0.5
TYPO_FRAC = 0.1
TITLE_SUFFIXES = ("(Tuyển gấp)", "- Lương upto 2000$", "[Hà Nội]", "- Urgent")
KEEP_FRAC = 0.6
ROOT = Path(__file__).resolve().parents[1]


def rng_for(*key) -> random.Random:
    h = hashlib.sha256("|".join(map(str, (SEED, *key))).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def no_diacritics(text: str) -> str:
    s = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
    return unicodedata.normalize("NFC", "".join(c for c in s if not unicodedata.combining(c)))


def typo_word(word: str, rng: random.Random) -> str:
    if len(word) < 4:
        return word
    i = rng.randrange(1, len(word) - 2)
    return word[:i] + word[i + 1] + word[i] + word[i + 2 :]


def typos(text: str, rng: random.Random, frac: float = TYPO_FRAC) -> str:
    return re.sub(r"\w+", lambda m: typo_word(m.group(), rng) if rng.random() < frac else m.group(), text)


# ---------- WM1 ----------

WM1_NOISE = ("bo_dau", "go_sai", "tieu_de_them", "cat_mo_ta")
BODY = ("description", "requirements_text")


def perturb_job(row: dict, kind: str) -> dict:
    r = dict(row)
    rng = rng_for(kind, r["job_uid"])
    if rng.random() >= RATE_WM1:
        return r
    if kind == "bo_dau":
        for c in ("title", *BODY):
            r[c] = no_diacritics(r.get(c) or "")
    elif kind == "go_sai":
        for c in BODY:
            r[c] = typos(r.get(c) or "", rng)
    elif kind == "tieu_de_them":
        r["title"] = f"{r.get('title') or ''} {rng.choice(TITLE_SUFFIXES)}"
    elif kind == "cat_mo_ta":
        for c in BODY:
            s = r.get(c) or ""
            r[c] = s[: int(len(s) * KEEP_FRAC)]
    return r


def wm1(labels: Path) -> None:
    import pandas as pd

    from crawler.eval_dedup import THRESHOLD, load, prf, snapshot_df

    raw = [json.loads(x) for x in labels.read_text("utf-8").splitlines() if x.strip()]
    gold = [r["dup"] for r in raw]
    clean = snapshot_df()
    print(f"nhãn {labels.name}: {len(raw)} cặp, {sum(gold)} trùng; mỗi tin bị nhiễu với xác suất {RATE_WM1}")
    print("\n| Nhiễu | baseline P/R/F1 | v1 P/R/F1 | v2 P/R/F1 | cặp có ít nhất một bản nhiễu |")
    print("|---|---|---|---|---|")
    for kind in ("không", *WM1_NOISE):
        if kind == "không":
            df, touched = clean, set()
        else:
            recs = [perturb_job(r, kind) for r in clean.to_dict("records")]
            orig = clean.set_index("job_uid")
            touched = {
                r["job_uid"]
                for r in recs
                if any(r.get(c) != orig.at[r["job_uid"], c] for c in ("title", *BODY) if c in orig.columns)
            }
            df = pd.DataFrame(recs)
        rows, _, _ = load(copy.deepcopy(raw), df)
        systems = {
            "baseline": [r["baseline"] for r in rows],
            "v1": [r["baseline"] or r["jaccard"] >= THRESHOLD for r in rows],
            "v2": [r["baseline_soft"] or r["jaccard_cut"] >= THRESHOLD for r in rows],
        }
        cells = [" / ".join(f"{x:.3f}" for x in prf(gold, systems[s])) for s in ("baseline", "v1", "v2")]
        n_touch = sum(r["a"] in touched or r["b"] in touched for r in rows)
        print(f"| {kind} | {' | '.join(cells)} | {n_touch}/{len(rows)} |")


# ---------- WM2 ----------

WM2_NOISE = ("bo_dau", "chu_thuong", "go_sai")


def perturb_tokens(row: dict, kind: str) -> dict:
    rng = rng_for(kind, row["id"])
    if kind == "bo_dau":
        toks = [no_diacritics(t) for t in row["tokens"]]
    elif kind == "chu_thuong":
        toks = [t.lower() for t in row["tokens"]]
    else:
        toks = [typo_word(t, rng) if rng.random() < TYPO_FRAC else t for t in row["tokens"]]
    return {**row, "id": f"{row['id']}~{kind}", "tokens": toks}


def wm2(bio: Path, seeds: list[int], prefix: str) -> None:
    from seqeval.metrics import f1_score
    from seqeval.scheme import IOB2

    from annotation.preannotate_dict import load_aliases
    from ie.baseline_dict import build_index, tag

    rows = [json.loads(x) for x in bio.read_text("utf-8").splitlines() if x.strip()]
    gold = [r["tags"] for r in rows]
    kw = {"mode": "strict", "scheme": IOB2}
    index, max_len = build_index(load_aliases())
    variants = {"không": rows} | {k: [perturb_tokens(r, k) for r in rows] for k in WM2_NOISE}

    models = []
    try:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        for s in seeds:
            path = ROOT / "data" / "models" / f"{prefix}-s{s}"
            tok = AutoTokenizer.from_pretrained(path)
            models.append((s, tok, AutoModelForTokenClassification.from_pretrained(path).to(dev)))
    except ImportError:
        print("không có torch → chỉ chấm từ điển")

    from ie.phobert import predict, prepare

    print(f"\n{len(rows)} câu `{bio.stem}`; PhoBERT {prefix} seed {seeds}")
    print("\n| Nhiễu | từ điển F1 | PhoBERT F1 (từng seed) | PhoBERT TB |")
    print("|---|---|---|---|")
    for kind, rs in variants.items():
        f_dict = f1_score(gold, [tag(r["tokens"], index, max_len) for r in rs], **kw)
        fs = []
        if models:
            prepared = prepare(rs)  # không dùng cache: id đã đổi theo loại nhiễu
            for _, tok, model in models:
                fs.append(f1_score(gold, predict(model, tok, prepared, 256, dev), **kw))
        mean = sum(fs) / len(fs) if fs else float("nan")
        per = " / ".join(f"{f:.3f}" for f in fs)
        print(f"| {kind} | {f_dict:.3f} | {per} | {mean:.3f} |", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="task", required=True)
    a = sub.add_parser("wm1")
    a.add_argument("--labels", type=Path, default=ROOT / "data" / "annotation" / "dedup_batch1.labels_v02.jsonl")
    b = sub.add_parser("wm2")
    b.add_argument("--bio", type=Path, default=ROOT / "data" / "annotation" / "skill_test1.bio.jsonl")
    b.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    b.add_argument("--prefix", default="wm2-phobert-v3")
    args = ap.parse_args()
    if args.task == "wm1":
        wm1(args.labels)
    else:
        wm2(args.bio, args.seeds, args.prefix)


if __name__ == "__main__":
    main()
