"""WM2 self-training: thêm span mà các model PhoBERT đều đoán (nhãn yếu bỏ sót) vào nhãn yếu, rồi train lại.

    uv run python -m ie.self_train --src rules --dst selftrain --models wm2-phobert-rules-s1 wm2-phobert-rules-s2 wm2-phobert-rules-s3

- Chỉ chạy trên tập train nhãn yếu (đã loại tin dev/test); không chạm dev hay test.
- Span được thêm khi: TẤT CẢ model cùng đoán đúng span đó (đồng thuận = độ chắc), không chồng span nhãn yếu sẵn có,
  và không bị luật guideline loại (`ie.weak_rules.refine`).
- Không bỏ span nhãn yếu nào: self-training ở đây chỉ để giảm bỏ sót (recall).
"""

from __future__ import annotations

from common.io import read_jsonl

import argparse
import json
from collections import Counter
from pathlib import Path

from ie.baseline_dict import spans
from ie.phobert import MODELS, predict, prepare
from ie.weak_rules import refine

WEAK_DIR = Path(__file__).resolve().parents[1] / "data" / "weak"


def merge(tokens: list[str], weak: list[str], preds: list[list[str]]) -> tuple[list[str], list[str]]:
    """Trả về (nhãn mới, các span đã thêm)."""
    agreed = set.intersection(*[{(a, b) for a, b, _ in spans(tokens, p)} for p in preds])
    out = list(weak)
    added = []
    for a, b in sorted(agreed):
        if all(t == "O" for t in out[a:b]) and (b >= len(out) or out[b] != "I-SKILL"):
            out[a] = "B-SKILL"
            out[a + 1 : b] = ["I-SKILL"] * (b - a - 1)
            added.append((a, b))
    out = refine(tokens, out)
    kept = [" ".join(tokens[a:b]) for a, b in added if out[a] == "B-SKILL"]
    return out, kept


def main() -> None:
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="rules")
    ap.add_argument("--dst", default="selftrain")
    ap.add_argument("--models", nargs="+", required=True)
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rows = prepare(read_jsonl(WEAK_DIR / f"wm2_weak_{args.src}.bio.jsonl"), MODELS / "seg_cache.jsonl")
    preds = []
    for name in args.models:
        tok = AutoTokenizer.from_pretrained(MODELS / name)
        model = AutoModelForTokenClassification.from_pretrained(MODELS / name).to(device)
        preds.append(predict(model, tok, rows, 256, device))
        print(f"đã đoán bằng {name}")

    added = Counter()
    n_pos = n_span = 0
    out_path = WEAK_DIR / f"wm2_weak_{args.dst}.bio.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(rows):
            tags, kept = merge(r["tokens"], r["tags"], [p[i] for p in preds])
            added.update(kept)
            k = tags.count("B-SKILL")
            n_pos += k > 0
            n_span += k
            rec = {key: r[key] for key in ("id", "job_uid", "source", "tokens")}
            f.write(json.dumps({**rec, "tags": tags}, ensure_ascii=False) + "\n")
    print(
        f"self-train {args.src}→{args.dst}: {len(rows)} câu, {n_pos} câu có kỹ năng, {n_span} span "
        f"(thêm {sum(added.values())} span) → {out_path}"
    )
    print("Span thêm nhiều nhất:", added.most_common(40))


if __name__ == "__main__":
    main()
