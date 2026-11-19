"""WM2: so sánh PhoBERT với baseline từ điển trên cùng tập bằng bootstrap ghép cặp.

Mặc định lấy lại **theo tin** (`--by posting`): 1.000 câu đến từ 125 tin, câu cùng tin không độc lập
nên lấy lại theo câu cho khoảng tin cậy hẹp giả. `--by sentence` giữ cách cũ để so.

Lệnh: uv run python -m experiments.paired_wm2 --bio data/annotation/skill_test1.bio.jsonl
In ΔF1 (span strict) và khoảng tin cậy 95%; lưu dự đoán vào data/eval/ (không commit) để phân tích lỗi.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from annotation.preannotate_dict import load_aliases
from experiments.bootstrap import cluster_indices, sentence_indices
from ie.baseline_dict import build_index, spans, tag
from ie.phobert import MODELS, hybrid, predict, prepare, read_bio


def counts(rows: list[dict], pred: list[list[str]]) -> np.ndarray:
    """Mỗi câu: (số span đúng, số span đoán, số span vàng)."""
    out = []
    for r, p in zip(rows, pred, strict=True):
        g = {(a, b) for a, b, _ in spans(r["tokens"], r["tags"])}
        q = {(a, b) for a, b, _ in spans(r["tokens"], p)}
        out.append((len(g & q), len(q), len(g)))
    return np.array(out)


def f1(c: np.ndarray) -> float:
    tp, p, g = c.sum(0)
    return float(2 * tp / (p + g)) if p + g else 0.0


def main() -> None:
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    ap = argparse.ArgumentParser()
    ap.add_argument("--bio", type=Path, required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--b", type=int, default=1000)
    ap.add_argument("--by", choices=["posting", "sentence"], default="posting")
    ap.add_argument("--prefix", default="wm2-phobert", help="tên thư mục model trước -s<seed>, vd wm2-phobert-v2")
    ap.add_argument("--out", type=Path, default=Path("data/eval/skill_test1_preds.json"))
    ap.add_argument(
        "--against",
        type=Path,
        help="file dự đoán đã lưu của hệ khác (vd skill_test1_preds_v3.json): so thêm ΔF1 với `phobert_s<seed>` cùng seed",
    )
    args = ap.parse_args()
    other = json.loads(args.against.read_text("utf-8")) if args.against else None

    rows = prepare(read_bio(args.bio), MODELS / "seg_cache.jsonl")
    index, max_n = build_index(load_aliases())
    dct = [tag(r["tokens"], index, max_n) for r in rows]
    cd = counts(rows, dct)
    if args.by == "posting":
        boot = list(cluster_indices([r["job_uid"] for r in rows], args.b))
    else:
        boot = list(sentence_indices(len(rows), args.b))
    print(f"dict F1={f1(cd):.3f}")
    save: dict = {"ids": [r["id"] for r in rows], "dict": dct}
    for s in args.seeds:
        path = MODELS / f"{args.prefix}-s{s}"
        tok = AutoTokenizer.from_pretrained(path)
        model = AutoModelForTokenClassification.from_pretrained(path)
        pred = predict(model, tok, rows, 256, torch.device("cpu"))
        hyb = [hybrid(p, d) for p, d in zip(pred, dct, strict=True)]
        save[f"phobert_s{s}"], save[f"hybrid_s{s}"] = pred, hyb
        for name, pr in (("phobert", pred), ("phobert+dict", hyb)):
            c = counts(rows, pr)
            diffs = np.array([f1(c[ix]) - f1(cd[ix]) for ix in boot])
            lo, hi = np.percentile(diffs, [2.5, 97.5])
            print(
                f"s{s} {name:13s} F1={f1(c):.3f} ΔF1={f1(c) - f1(cd):+.3f} "
                f"CI95=[{lo:+.3f}; {hi:+.3f}] p(Δ≤0)={np.mean(diffs <= 0):.3f}"
            )
        if other is not None:
            assert other["ids"] == save["ids"], "hai file dự đoán phải cùng thứ tự câu"
            co = counts(rows, other[f"phobert_s{s}"])
            c = counts(rows, pred)
            diffs = np.array([f1(c[ix]) - f1(co[ix]) for ix in boot])
            lo, hi = np.percentile(diffs, [2.5, 97.5])
            print(
                f"s{s} so với {args.against.name}: F1 {f1(co):.3f} → {f1(c):.3f} ΔF1={f1(c) - f1(co):+.3f} "
                f"CI95=[{lo:+.3f}; {hi:+.3f}] p(Δ≤0)={np.mean(diffs <= 0):.3f}"
            )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(save, ensure_ascii=False), encoding="utf-8")
    print(f"đã lưu {args.out}")


if __name__ == "__main__":
    main()
