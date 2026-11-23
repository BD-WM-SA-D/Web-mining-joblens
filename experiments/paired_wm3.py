"""WM3: so mô hình lai với baseline từ điển trên cùng tập TEST bằng bootstrap ghép cặp theo câu.

    uv run python -m experiments.paired_wm3

Một điểm số đơn lẻ không nói được chênh lệch có thật hay do may: lấy lại mẫu có hoàn lại 1.000 lần,
mỗi lần tính lại cả hai hệ **trên cùng** mẫu đó, rồi xem phân phối của hiệu số. Ghép cặp (cùng mẫu cho
cả hai hệ) nên khử được phần nhiễu do câu dễ/khó.

Mặc định lấy lại **theo review** (`--by review`): 348 câu đến từ 99 review, câu cùng review chung điểm
sao, văn phong và ô `section`, nên lấy lại theo câu cho khoảng tin cậy hẹp giả.

`--baseline section` so với luật một dòng theo ô `section` – baseline chính của WM3 (xem results.md).

Khía cạnh không so ở đây: mô hình lai lấy khía cạnh từ chính từ điển nên Δ = 0 theo thiết kế.
"""

from __future__ import annotations

from common.io import read_jsonl

import argparse
from pathlib import Path

import numpy as np

from absa.eval_dev import GOLD, SENTS
from absa.lexicon import VERSION as DICT_VERSION
from absa.lexicon import predict as dict_predict
from absa.score import as_dict, report
from absa.supervised import MODELS_FN, TEST_GOLD, section_rule, splits
from experiments.bootstrap import cluster_indices, sentence_indices

METRICS = {
    "macro pos/neg theo ô": lambda rep: rep["slot"]["macro_f1_2"],
    "F1 negative theo ô": lambda rep: rep["slot"]["per_class"]["negative"]["f1"],
    "R negative theo ô": lambda rep: rep["slot"]["per_class"]["negative"]["r"],
    "macro 3 lớp theo ô": lambda rep: rep["slot"]["macro_f1_3"],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="hybrid")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--b", type=int, default=1000)
    ap.add_argument("--by", choices=["review", "sentence"], default="review")
    ap.add_argument("--baseline", choices=["dict", "section"], default="dict")
    ap.add_argument("--gold", type=Path, nargs="+", default=GOLD)
    ap.add_argument("--test-gold", type=Path, default=TEST_GOLD)
    ap.add_argument("--sentences", type=Path, default=SENTS)
    args = ap.parse_args()

    drows, _, trows, _ = splits(args.gold, args.test_gold, args.sentences)
    gold = [r["gold"] for r in trows]
    if args.baseline == "section":
        base, base_name = section_rule(trows), "luật section"
    else:
        base, base_name = [as_dict(dict_predict(r["text"])) for r in trows], DICT_VERSION
    new = MODELS_FN[args.model](drows, trows, seed=args.seed)
    assert len(read_jsonl(args.test_gold)) >= len(trows)

    if args.by == "review":
        boot = list(cluster_indices([r["review_id"] for r in trows], args.b))
    else:
        boot = list(sentence_indices(len(trows), args.b))
    print(
        f"TEST {len(trows)} câu / {len({r['review_id'] for r in trows})} review; {base_name} so với {args.model}"
        f" (train trên {len(drows)} câu dev), bootstrap theo {args.by}"
    )
    print(f"\n| Chỉ số | {base_name} | {args.model} | Δ | CI95 ghép cặp | p(Δ≤0) |")
    print("|---|---|---|---|---|---|")
    rep_b, rep_n = report(gold, base), report(gold, new)
    for name, f in METRICS.items():
        v_b, v_n = f(rep_b), f(rep_n)
        diffs = np.array(
            [
                f(report([gold[i] for i in ix], [new[i] for i in ix]))
                - f(report([gold[i] for i in ix], [base[i] for i in ix]))
                for ix in boot
            ]
        )
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        print(
            f"| {name} | {v_b:.3f} | {v_n:.3f} | {v_n - v_b:+.3f} |"
            f" [{lo:+.3f}; {hi:+.3f}] | {np.mean(diffs <= 0):.3f} |"
        )


if __name__ == "__main__":
    main()
