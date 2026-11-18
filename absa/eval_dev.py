"""Chấm các phiên bản baseline WM3 trên tập dev đã gán nhãn.

    uv run python -m absa.eval_dev

Tập dev = các câu trong `data/annotation/absa_trial.absa.jsonl` **còn tồn tại** trong
`data/absa/sentences.jsonl` (khớp theo văn bản). Câu bị bộ tách câu cắt nhỏ hơn thì loại, vì đơn vị
gán nhãn đã khác – giữ lại sẽ chấm mô hình trên đơn vị không còn dùng nữa.

In một bảng để dán vào `experiments/results.md`. Không ghi file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from absa.lexicon import VERSION as DICT_VERSION
from absa.lexicon import aspect_terms, predict, sentiment_terms
from absa.score import as_dict, fmt, report
from absa.weak_labels import VERSION as WEAK_VERSION
from absa.weak_labels import weak_label

ROOT = Path(__file__).resolve().parents[1]
GOLD = [
    ROOT / "data" / "annotation" / "absa_trial.absa.jsonl",  # lô thử 60 câu (project 6)
    ROOT / "data" / "annotation" / "absa_dev2.absa.jsonl",  # mở rộng 150 câu (project 8)
]
SENTS = ROOT / "data" / "absa" / "sentences.jsonl"
UNUSABLE = "không gán được"

# Các cấu hình luật cực tính của `absa.lexicon.match_polarity`, bật dần.
CONFIGS = [
    ("từ điển v1 (chỉ đếm từ cảm xúc)", dict(advice=False, missing=False, tie=False)),
    ("+ luật đề nghị", dict(advice=True, missing=False, tie=False)),
    ('+ luật "không có"', dict(advice=True, missing=True, tie=False)),
    ("+ luật hòa → negative", dict(advice=True, missing=False, tie=True)),
    ("từ điển v3 (cả ba luật)", dict(advice=True, missing=True, tie=True)),
]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def dev_set(gold_paths: list[Path], sents_path: Path) -> tuple[list[dict], list[dict], int]:
    """(nhãn vàng, câu tương ứng, số câu bị loại). Khớp theo văn bản nên id đổi vẫn tìm được.

    Nhiều file nhãn thì ghép lại (dev nằm ở hai project Label Studio); câu trùng văn bản chỉ lấy một lần.
    """
    rows, seen = [], set()
    for path in gold_paths:
        for r in load_jsonl(path):
            # Gộp theo `sentence_id`, KHÔNG theo văn bản: hai review khác nhau có thể có câu giống hệt
            # ("Lương thấp"), đó là hai mẫu thật, gộp lại là làm hụt tập đánh giá.
            if (r["flag"] or "").startswith(UNUSABLE) or r["sentence_id"] in seen:
                continue
            seen.add(r["sentence_id"])
            rows.append(r)
    by_text = {}
    for s in load_jsonl(sents_path):
        by_text.setdefault(s["text"], s)
    keep = [(r, by_text[r["text"]]) for r in rows if r["text"] in by_text]
    return [r for r, _ in keep], [s for _, s in keep], len(rows) - len(keep)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", type=Path, nargs="+", default=GOLD)
    ap.add_argument("--sentences", type=Path, default=SENTS)
    args = ap.parse_args()

    rows, sents, dropped = dev_set(args.gold, args.sentences)
    gold = [r["gold"] for r in rows]
    n_pairs = sum(len(g) for g in gold)
    print(
        f"{', '.join(p.name for p in args.gold)}: {len(rows)} câu, {n_pairs} cặp (khía cạnh, cực);"
        f" loại {dropped} câu đã bị tách nhỏ hơn"
    )

    # Bật dần từng luật cực tính để báo cáo được đóng góp của riêng nó, không chỉ tổng.
    print(f"từ điển {DICT_VERSION}, {len(aspect_terms())} cụm khía cạnh, {len(sentiment_terms())} cụm cảm xúc")
    runs = [(name, [as_dict(predict(r["text"], **o)) for r in rows]) for name, o in CONFIGS]
    runs.append((f"nhãn yếu {WEAK_VERSION}", [as_dict(weak_label(s)) for s in sents]))
    for name, pred in runs:
        print("\n" + fmt(name, report(gold, pred)))

    print("\n| Hệ | Khía cạnh F1 | Theo ô, 3 lớp | Theo ô, chỉ pos/neg | R negative | P negative |")
    print("|---|---|---|---|---|---|")
    for name, pred in runs:
        rep = report(gold, pred)
        s = rep["slot"]
        neg = s["per_class"]["negative"]
        print(
            f"| {name} | {rep['aspect']['f1']:.3f} | {s['macro_f1_3']:.3f} | {s['macro_f1_2']:.3f} |"
            f" {neg['r']:.3f} | {neg['p']:.3f} |"
        )


if __name__ == "__main__":
    main()
