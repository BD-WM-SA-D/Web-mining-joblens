"""WM3 – tách review ITviec thành câu để gán nhãn khía cạnh + cảm xúc.

    uv run python -m absa.split --out data/absa/sentences.jsonl

Mỗi review ITviec có ba phần văn bản (`title`, `liked_text`, `improvement_text`) và 5 điểm sao theo
khía cạnh. ABSA làm ở **mức câu**, nên phải tách trước.

Hai điều phải xử lý riêng:

1. **Gạch đầu dòng.** Người viết review ITviec hay liệt kê "- Đồng nghiệp thân thiện. - Lương thấp."
   `sent_tokenize` không cắt ở dấu "-", nên cắt theo gạch đầu dòng trước rồi mới tách câu.
2. **Hai ngôn ngữ.** 116/144 review tiếng Việt, 28 tiếng Anh (đo 2026-11-15). `underthesea.sent_tokenize`
   dùng cho tiếng Việt; câu tiếng Anh tách bằng regex dấu kết câu. Trường `lang` giữ lại để
   báo cáo kết quả riêng từng ngôn ngữ (PhoBERT chỉ hiểu tiếng Việt).

Câu quá ngắn (< MIN_CHARS ký tự) hoặc không có chữ cái thì bỏ: "- ", "N/A", ":))" không gán được nhãn.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_CHARS = 15
SECTIONS = ("title", "liked", "improvement")
# dấu tiếng Việt – dùng để đoán ngôn ngữ, ngưỡng 5 ký tự để khỏi nhận nhầm tên riêng ("Hà Nội")
VI_CHARS_RE = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]")
VI_MIN_DIACRITICS = 5
# gạch đầu dòng: "- ", "• ", "+ ", "1. " ở đầu dòng hoặc sau khoảng trắng
BULLET_RE = re.compile(r"(?:(?<=^)|(?<=\s))[-–•*+]\s+|(?:(?<=^)|(?<=\s))\d{1,2}[.)]\s+")
EN_SENT_RE = re.compile(r"(?<=[.!?])\s+")
HAS_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
WS_RE = re.compile(r"\s+")


def detect_lang(text: str) -> str:
    """'vi' hay 'en' – đủ cho việc chọn bộ tách câu và báo cáo riêng từng ngôn ngữ."""
    return "vi" if len(VI_CHARS_RE.findall(text)) >= VI_MIN_DIACRITICS else "en"


def _sent_split(chunk: str, lang: str) -> list[str]:
    if lang == "vi":
        from underthesea import sent_tokenize

        return list(sent_tokenize(chunk))
    return EN_SENT_RE.split(chunk)


def split_text(text: str | None, lang: str) -> list[str]:
    """Một đoạn → danh sách câu: cắt gạch đầu dòng trước, rồi tách câu trong từng gạch."""
    if not text:
        return []
    out = []
    # Dấu xuống dòng (từ `<br>` trong HTML) là ranh giới ý cứng: cắt trước khi gộp khoảng trắng.
    for line in text.split("\n"):
        for chunk in BULLET_RE.split(WS_RE.sub(" ", line).strip()):
            chunk = chunk.strip()
            if not chunk:
                continue
            for s in _sent_split(chunk, lang):
                s = s.strip(" \t-–•*")
                if len(s) >= MIN_CHARS and HAS_LETTER_RE.search(s):
                    out.append(s)
    return out


def sentences_of(review: dict) -> list[dict]:
    """Một message review.v1 → các câu kèm bối cảnh review (điểm sao, phần, ngôn ngữ)."""
    p = review["payload"]
    whole = " ".join(filter(None, (p.get("title"), p.get("liked_text"), p.get("improvement_text"))))
    lang = detect_lang(whole)
    out = []
    for section, field in (("title", "title"), ("liked", "liked_text"), ("improvement", "improvement_text")):
        seen: dict[str, int] = {}
        for i, text in enumerate(split_text(p.get(field), lang)):
            # id băm theo NỘI DUNG, không theo thứ tự câu: sửa bộ tách câu thì câu nào không đổi vẫn
            # giữ nguyên id nên nhãn đã gán không mất. `rep` chỉ để phân biệt hai câu trùng y nguyên.
            rep = seen[text] = seen.get(text, -1) + 1
            out.append(
                {
                    "sentence_id": hashlib.sha256(
                        f"{review['source_review_id']}|{section}|{text}|{rep}".encode()
                    ).hexdigest()[:16],
                    "source_review_id": review["source_review_id"],
                    "company_id": review["company_id"],
                    "company_name": p.get("company_name"),
                    "review_month": p.get("review_month"),
                    "section": section,
                    "sent_idx": i,
                    "lang": lang,
                    "text": text,
                    # bối cảnh dùng cho NHÃN YẾU, không được đưa vào tập test
                    "rating_overall": p.get("rating_overall"),
                    "aspect_ratings": p.get("aspect_ratings") or {},
                    "recommend": p.get("recommend"),
                }
            )
    return out


def load_reviews(patterns: list[str]) -> list[dict]:
    """Đọc các file reviews.jsonl khớp `patterns`, bỏ review trùng theo `source_review_id`.

    Chặn trộn dữ liệu đã parse lại với dữ liệu cũ: `source_review_id` là `content_hash(payload)` nên
    cùng một review parse bằng hai bản parser sẽ có hai id khác nhau và lọt qua bước bỏ trùng, cho ra
    corpus gấp đôi với hai cách tách câu lẫn nhau.
    """
    files = sorted(f for pattern in patterns for f in glob.glob(pattern))
    reparsed = [f for f in files if "reparse-" in f]
    if reparsed and len(reparsed) != len(files):
        raise SystemExit(
            "Có cả thư mục reparse-* và thư mục crawl gốc trong cùng một lần chạy:\n  "
            + "\n  ".join(files)
            + "\nChọn một bộ: --reviews 'data/crawl/itviec/reparse-*/reviews.jsonl'"
        )

    rows, seen = [], set()
    for pattern in patterns:
        for f in sorted(glob.glob(pattern)):
            for ln in Path(f).read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                r = json.loads(ln)
                if r["source_review_id"] in seen:
                    continue
                seen.add(r["source_review_id"])
                rows.append(r)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews", nargs="+", default=["data/crawl/itviec/*/reviews.jsonl"])
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "absa" / "sentences.jsonl")
    args = ap.parse_args()

    reviews = load_reviews(args.reviews)
    sents = [s for r in reviews for s in sentences_of(r)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for s in sents:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    by_lang = {lg: sum(1 for s in sents if s["lang"] == lg) for lg in ("vi", "en")}
    by_sec = {sec: sum(1 for s in sents if s["section"] == sec) for sec in SECTIONS}
    print(f"{len(reviews)} review → {len(sents)} câu")
    print(f"  ngôn ngữ: {by_lang}")
    print(f"  theo phần: {by_sec}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
