"""WM3 – chẩn đoán trên TEST cho các hệ **đã chấm**, không thêm hệ mới, không chọn tham số.

    uv run python -m experiments.diag_wm3

1. Tách số theo ngôn ngữ (vi / en): TEST có câu tiếng Anh, mô hình lai dùng TF-IDF trộn hai ngôn ngữ.
2. Câu có **hai cực khác nhau** trong nhãn vàng, và **trần** của mọi hệ chỉ cho một cực mỗi câu: lấy
   đúng khía cạnh vàng và cực xuất hiện nhiều nhất trong câu, đó là điểm cao nhất kiểu hệ này đạt được.
"""

from __future__ import annotations

import collections

from absa.eval_dev import GOLD, SENTS
from absa.lexicon import predict as dict_predict
from absa.score import as_dict, report
from absa.supervised import MODELS_FN, TEST_GOLD, section_rule, sentence_polarity, splits


def macro2(gold: list[dict], pred: list[dict]) -> float:
    return report(gold, pred)["slot"]["macro_f1_2"]


def main() -> None:
    drows, _, trows, _ = splits(GOLD, TEST_GOLD, SENTS)
    systems = {
        "từ điển absa-dict": [as_dict(dict_predict(r["text"])) for r in trows],
        "luật section": section_rule(trows),
        "mô hình lai (seed 1)": MODELS_FN["hybrid"](drows, trows, seed=1),
    }
    gold = [r["gold"] for r in trows]

    langs = sorted({r["lang"] for r in trows})
    cnt = collections.Counter(r["lang"] for r in trows)
    print(f"TEST {len(trows)} câu: " + ", ".join(f"{lg} {cnt[lg]}" for lg in langs))
    print("\n| Hệ | tất cả | " + " | ".join(langs) + " |")
    print("|---|---|" + "---|" * len(langs))
    for name, pred in systems.items():
        cells = []
        for lg in langs:
            ix = [i for i, r in enumerate(trows) if r["lang"] == lg]
            cells.append(f"{macro2([gold[i] for i in ix], [pred[i] for i in ix]):.3f}")
        print(f"| {name} | {macro2(gold, pred):.3f} | " + " | ".join(cells) + " |")

    multi = [g for g in gold if len(g) > 1]
    mixed = [g for g in gold if len(set(g.values())) > 1]
    print(f"\nCâu nhiều khía cạnh: {len(multi)}/{len(gold)}; trong đó hai cực khác nhau: {len(mixed)}")
    oracle = [dict.fromkeys(r["gold"], sentence_polarity(r)) if r["gold"] else {} for r in trows]
    print(
        f"Trần của hệ một cực/câu (khía cạnh vàng + cực phổ biến nhất của câu): macro pos/neg {macro2(gold, oracle):.3f}"
    )


if __name__ == "__main__":
    main()
