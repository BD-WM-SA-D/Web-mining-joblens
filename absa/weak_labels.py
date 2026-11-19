"""WM3 – nhãn yếu cho câu review (dùng để pre-train / tiền gán, KHÔNG dùng làm tập test).

    uv run python -m absa.weak_labels --out data/absa/weak_stars.jsonl

Quy tắc (AGENTS.md: nhãn yếu không được làm tập test):

| Thành phần | Nguồn nhãn yếu |
|---|---|
| Khía cạnh | từ điển `absa/resources/aspect_lexicon.csv` khớp cụm từ trong câu |
| Cực tính | **điểm sao theo khía cạnh** của review (ITviec cho 5/6 khía cạnh), ≥4 → tích cực, ≤2 → tiêu cực |
| Cực tính (dự phòng) | sao = 3 hoặc khía cạnh không có sao (`work_life_balance`) → theo **phần** của review: `liked` → tích cực, `improvement` → tiêu cực, `title` → theo `rating_overall` |

Cực tính **không** lấy từ từ điển cảm xúc, để nhãn yếu độc lập với baseline – nếu dùng chung từ điển thì
mô hình học từ nhãn yếu chỉ học lại baseline và so sánh mất ý nghĩa.

Ba nguồn nhiễu đã biết, ghi ra để phân tích lỗi:
1. Sao theo khía cạnh là của **cả review**, nên câu nói riêng một ý trái chiều sẽ bị gán sai.
2. Phần `liked` vẫn có câu tiêu cực ("OT nhiều lúc gần deadline") và ngược lại.
3. `work_life_balance` không có sao → chỉ còn tín hiệu phần, yếu nhất trong 6 khía cạnh.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from absa.lexicon import ASPECTS, match_aspects

ROOT = Path(__file__).resolve().parents[1]
VERSION = "aspect-dict+stars"
STAR_POS, STAR_NEG = 4.0, 2.0
SECTION_POLARITY = {"liked": "positive", "improvement": "negative"}
# khía cạnh ITviec KHÔNG cho điểm sao → nhãn yếu chỉ dựa vào phần của review
NO_STAR_ASPECTS = frozenset({"work_life_balance"})


def polarity_from_star(star: float | None) -> str | None:
    if star is None:
        return None
    if star >= STAR_POS:
        return "positive"
    if star <= STAR_NEG:
        return "negative"
    return None  # 3 sao: không kết luận, để tín hiệu phần quyết định


def polarity_from_section(section: str, rating_overall: float | None) -> str:
    if section in SECTION_POLARITY:
        return SECTION_POLARITY[section]
    return polarity_from_star(rating_overall) or "neutral"


def weak_label(sent: dict) -> list[dict]:
    """Câu → [{aspect, polarity, source}] theo nhãn yếu; rỗng nếu từ điển không nhận ra khía cạnh."""
    out = []
    for aspect in match_aspects(sent["text"]):
        star = None if aspect in NO_STAR_ASPECTS else (sent.get("aspect_ratings") or {}).get(aspect)
        pol = polarity_from_star(star)
        source = "star"
        if pol is None:
            pol = polarity_from_section(sent["section"], sent.get("rating_overall"))
            source = "section"
        out.append({"aspect": aspect, "polarity": pol, "source": source})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sentences", type=Path, default=ROOT / "data" / "absa" / "sentences.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "absa" / "weak_stars.jsonl")
    args = ap.parse_args()

    sents = [json.loads(ln) for ln in args.sentences.read_text(encoding="utf-8").splitlines() if ln.strip()]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    n_cov = 0
    by_aspect: collections.Counter = collections.Counter()
    by_pol: collections.Counter = collections.Counter()
    by_src: collections.Counter = collections.Counter()
    with args.out.open("w", encoding="utf-8") as f:
        for s in sents:
            labels = weak_label(s)
            n_cov += bool(labels)
            for lb in labels:
                by_aspect[lb["aspect"]] += 1
                by_pol[lb["polarity"]] += 1
                by_src[lb["source"]] += 1
            f.write(
                json.dumps(
                    {
                        "sentence_id": s["sentence_id"],
                        "text": s["text"],
                        "lang": s["lang"],
                        "section": s["section"],
                        "weak_version": VERSION,
                        "labels": labels,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"{len(sents)} câu, {n_cov} câu có ít nhất 1 khía cạnh ({n_cov / len(sents):.1%})")
    print(f"  theo khía cạnh: {dict(sorted(by_aspect.items(), key=lambda x: -x[1]))}")
    print(f"  theo cực tính:  {dict(by_pol)}")
    print(f"  nguồn cực tính: {dict(by_src)}")
    print(f"  khía cạnh thiếu nhãn yếu: {[a for a in ASPECTS if not by_aspect[a]]}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
