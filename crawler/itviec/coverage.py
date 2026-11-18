"""Đo độ phủ và thiên lệch của review ITviec công khai, từ HTML đã lưu (không gửi request mới).

    uv run python -m crawler.itviec.coverage --html-dir data/raw-html/itviec

Vì sao đo được thiên lệch: trang che **văn bản** của các review cũ nhưng vẫn hiện **điểm sao** của chúng.
So điểm sao của review công khai với điểm sao của các review bị che cho biết mẫu ta lấy được
có tích cực hơn phần còn lại hay không – con số này phải ghi vào phần hạn chế của báo cáo WM3.

In ra: số công ty có / không có review công khai, số câu mỗi review, điểm sao công khai so với bị che.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import statistics
from pathlib import Path

from lxml import html as lxml_html

from crawler.itviec.parser import SELECTORS, _rating, _text, parse_month, split_blocks

ROOT = Path(__file__).resolve().parents[2]
SENT_SPLIT_RE = re.compile(r"[.!?;\n]+")
TOTAL_RE = re.compile(r"<title>\s*(\d+)\s*[Rr]eview")


def sentences(text: str | None) -> list[str]:
    return [s.strip() for s in SENT_SPLIT_RE.split(text or "") if len(s.strip()) > 1]


def analyse_page(page_html: str) -> dict:
    """Thống kê một trang review đã lưu."""
    total = TOTAL_RE.search(page_html)
    public, blurred = [], []
    for chunk in split_blocks(page_html):
        node = lxml_html.fromstring(f"<div>{chunk}</div>")
        overall = _rating(_text(node.xpath(SELECTORS["rating_overall"])))
        month = parse_month(_text(node.xpath(SELECTORS["month"])))
        liked = _text(node.xpath(SELECTORS["liked"]))
        improvement = _text(node.xpath(SELECTORS["improvement"]))
        rec = _text(node.xpath(SELECTORS["recommend"])) or ""
        item = {"stars": overall, "month": month, "recommend": not rec.lower().startswith("không") if rec else None}
        if liked or improvement:
            item["n_sentences"] = len(sentences(liked)) + len(sentences(improvement))
            public.append(item)
        else:
            blurred.append(item)
    return {
        "total_reviews_on_site": int(total.group(1)) if total else None,
        "public": public,
        "blurred": blurred,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-dir", type=Path, default=ROOT / "data" / "raw-html" / "itviec")
    ap.add_argument("--out", type=Path, help="ghi thống kê từng trang ra JSON")
    args = ap.parse_args()

    files = sorted(args.html_dir.rglob("*.html.gz"))
    if not files:
        raise SystemExit(f"Không có HTML nào trong {args.html_dir}")

    rows = []
    for f in files:
        page = gzip.open(f, "rt", encoding="utf-8").read()
        r = analyse_page(page)
        r["file"] = f.name
        rows.append(r)

    with_public = [r for r in rows if r["public"]]
    pub_stars = [i["stars"] for r in rows for i in r["public"] if i["stars"]]
    blur_stars = [i["stars"] for r in rows for i in r["blurred"] if i["stars"]]
    sent = [i["n_sentences"] for r in rows for i in r["public"]]
    # chỉ so trong các công ty có cả hai loại, để không lẫn hiệu ứng khác công ty
    pairs = [
        (
            statistics.mean([i["stars"] for i in r["public"] if i["stars"]]),
            statistics.mean([i["stars"] for i in r["blurred"] if i["stars"]]),
        )
        for r in rows
        if [i for i in r["public"] if i["stars"]] and [i for i in r["blurred"] if i["stars"]]
    ]

    print(f"{len(files)} trang đã lưu, {len(with_public)} trang có review công khai")
    print(f"review công khai: {len(pub_stars)} | review bị che (chỉ có sao): {len(blur_stars)}")
    if sent:
        print(f"số câu mỗi review công khai: trung bình {statistics.mean(sent):.1f}, tổng {sum(sent)}")
    if pub_stars and blur_stars:
        print(f"sao công khai  : trung bình {statistics.mean(pub_stars):.2f} (n={len(pub_stars)})")
        print(f"sao bị che     : trung bình {statistics.mean(blur_stars):.2f} (n={len(blur_stars)})")
    if pairs:
        diffs = [a - b for a, b in pairs]
        print(
            f"chênh lệch trong cùng công ty: trung bình {statistics.mean(diffs):+.2f} sao "
            f"(n={len(diffs)} công ty, âm = review công khai khắt khe hơn)"
        )
    months = [i["month"] for r in rows for i in r["public"] if i["month"]]
    if months:
        print(f"tháng của review công khai: {min(months)} … {max(months)}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"→ {args.out}")


if __name__ == "__main__":
    main()
