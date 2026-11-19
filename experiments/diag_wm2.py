"""WM2 – chẩn đoán trên dự đoán TEST đã lưu, trả lời các câu phản biện mà không chấm thêm mô hình nào.

    uv run python -m experiments.diag_wm2

Đọc `data/eval/skill_test1_preds.json` (dự đoán của đúng lần chấm TEST chính thức 2026-11-12, do
`experiments/paired_wm2.py` lưu) nên **không** chọn hay chạy mô hình mới. In ra:

1. Khoảng tin cậy ΔF1 khi bootstrap **theo tin** thay vì theo câu (1.000 câu từ 125 tin).
2. F1 partial (chồng lấn token) bên cạnh F1 strict – lỗi là "không nhận ra" hay "cắt sai mép".
3. Recall tách theo kỹ năng **đã thấy** trong nhãn yếu từ tag và **chưa thấy** – mô hình có vượt ra ngoài
   từ điển/tag hay chỉ nội suy.
4. Tỷ lệ câu có kỹ năng mà hệ đoán **rỗng hoàn toàn**, và recall mức câu (tìm đúng ≥ 1 span).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from experiments.bootstrap import ci, cluster_indices, sentence_indices
from ie.baseline_dict import spans

ROOT = Path(__file__).resolve().parents[1]
BIO = ROOT / "data" / "annotation" / "skill_test1.bio.jsonl"
PREDS = ROOT / "data" / "eval" / "skill_test1_preds.json"
WEAK = ROOT / "data" / "weak" / "wm2_weak_tag.bio.jsonl"


def span_set(tokens: list[str], tags: list[str]) -> set[tuple[int, int]]:
    return {(a, b) for a, b, _ in spans(tokens, tags)}


def counts(rows: list[dict], pred: list[list[str]]) -> np.ndarray:
    out = []
    for r, p in zip(rows, pred, strict=True):
        g, q = span_set(r["tokens"], r["tags"]), span_set(r["tokens"], p)
        out.append((len(g & q), len(q), len(g)))
    return np.array(out)


def f1(c: np.ndarray) -> float:
    tp, p, g = c.sum(0)
    return float(2 * tp / (p + g)) if p + g else 0.0


def partial_prf(rows: list[dict], pred: list[list[str]]) -> tuple[float, float, float]:
    """Khớp một-một tham lam theo chồng lấn token: span đoán khớp span vàng nếu chung ≥ 1 token."""
    m_pred = m_gold = n_pred = n_gold = 0
    for r, p in zip(rows, pred, strict=True):
        g = sorted(span_set(r["tokens"], r["tags"]))
        q = sorted(span_set(r["tokens"], p))
        n_pred += len(q)
        n_gold += len(g)
        used: set[int] = set()
        for a, b in q:
            for k, (c, d) in enumerate(g):
                if k not in used and a < d and c < b:
                    used.add(k)
                    m_pred += 1
                    break
        m_gold += len(used)
    prec = m_pred / n_pred if n_pred else 0.0
    rec = m_gold / n_gold if n_gold else 0.0
    return prec, rec, (2 * prec * rec / (prec + rec) if prec + rec else 0.0)


def norm(tokens: list[str], a: int, b: int) -> str:
    return " ".join(tokens[a:b]).lower()


def weak_vocab(path: Path) -> set[str]:
    vocab: set[str] = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            vocab |= {norm(r["tokens"], a, b) for a, b, _ in spans(r["tokens"], r["tags"])}
    return vocab


def recall_by_seen(rows: list[dict], pred: list[list[str]], vocab: set[str]) -> dict[str, tuple[int, int]]:
    """{'đã thấy': (đúng, tổng vàng), 'chưa thấy': (...)} – recall strict theo nhóm span vàng."""
    out = {"đã thấy": [0, 0], "chưa thấy": [0, 0]}
    for r, p in zip(rows, pred, strict=True):
        q = span_set(r["tokens"], p)
        for a, b in span_set(r["tokens"], r["tags"]):
            k = "đã thấy" if norm(r["tokens"], a, b) in vocab else "chưa thấy"
            out[k][1] += 1
            out[k][0] += (a, b) in q
    return {k: (v[0], v[1]) for k, v in out.items()}


def sentence_level(rows: list[dict], pred: list[list[str]]) -> tuple[float, float]:
    """(tỷ lệ câu có kỹ năng mà đoán rỗng, tỷ lệ câu có kỹ năng mà tìm đúng ≥ 1 span)."""
    has = [(r, p) for r, p in zip(rows, pred, strict=True) if span_set(r["tokens"], r["tags"])]
    empty = sum(1 for r, p in has if not span_set(r["tokens"], p))
    hit = sum(1 for r, p in has if span_set(r["tokens"], r["tags"]) & span_set(r["tokens"], p))
    return empty / len(has), hit / len(has)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bio", type=Path, default=BIO)
    ap.add_argument("--preds", type=Path, default=PREDS)
    ap.add_argument("--weak", type=Path, default=WEAK)
    ap.add_argument("--b", type=int, default=1000)
    args = ap.parse_args()

    rows = [json.loads(x) for x in args.bio.read_text(encoding="utf-8").splitlines() if x.strip()]
    saved = json.loads(args.preds.read_text(encoding="utf-8"))
    if [r["id"] for r in rows] != saved["ids"]:
        raise SystemExit("thứ tự câu trong file dự đoán không khớp file nhãn – dừng")
    systems = {"từ điển": saved["dict"]} | {f"PhoBERT s{s}": saved[f"phobert_s{s}"] for s in (1, 2, 3)}
    groups = [r["job_uid"] for r in rows]
    print(f"{len(rows)} câu, {len(set(groups))} tin")

    # 1. khoảng tin cậy: theo câu so với theo tin
    cd = counts(rows, saved["dict"])
    print("\n| Hệ | F1 strict | ΔF1 | CI95 theo câu | CI95 theo tin | p(Δ≤0) theo tin |")
    print("|---|---|---|---|---|---|")
    for name, pred in systems.items():
        c = counts(rows, pred)
        if name == "từ điển":
            lo_s, hi_s, _ = ci([f1(c[ix]) for ix in sentence_indices(len(rows), args.b)])
            lo_c, hi_c, _ = ci([f1(c[ix]) for ix in cluster_indices(groups, args.b)])
            print(f"| {name} | {f1(c):.3f} | – | [{lo_s:.3f}; {hi_s:.3f}] | [{lo_c:.3f}; {hi_c:.3f}] | – |")
            continue
        d_s = [f1(c[ix]) - f1(cd[ix]) for ix in sentence_indices(len(rows), args.b)]
        d_c = [f1(c[ix]) - f1(cd[ix]) for ix in cluster_indices(groups, args.b)]
        lo_s, hi_s, _ = ci(d_s)
        lo_c, hi_c, p_c = ci(d_c)
        print(
            f"| {name} | {f1(c):.3f} | {f1(c) - f1(cd):+.3f} | [{lo_s:+.3f}; {hi_s:+.3f}] |"
            f" [{lo_c:+.3f}; {hi_c:+.3f}] | {p_c:.3f} |"
        )

    # 2–4. chẩn đoán
    vocab = weak_vocab(args.weak)
    print("\n| Hệ | P/R/F1 strict | P/R/F1 partial | R đã thấy | R chưa thấy | câu đoán rỗng | câu tìm ≥1 |")
    print("|---|---|---|---|---|---|---|")
    for name, pred in systems.items():
        c = counts(rows, pred)
        tp, n_p, n_g = c.sum(0)
        pp, pr, pf = partial_prf(rows, pred)
        seen = recall_by_seen(rows, pred, vocab)
        empty, hit = sentence_level(rows, pred)
        (hs, ns), (hu, nu) = seen["đã thấy"], seen["chưa thấy"]
        print(
            f"| {name} | {tp / n_p:.3f} / {tp / n_g:.3f} / {f1(c):.3f} | {pp:.3f} / {pr:.3f} / {pf:.3f} |"
            f" {hs / ns:.3f} ({ns}) | {hu / nu:.3f} ({nu}) | {empty:.3f} | {hit:.3f} |"
        )


if __name__ == "__main__":
    main()
