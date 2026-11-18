"""Parse lại HTML review ITviec đã lưu, KHÔNG gửi request nào.

    uv run python -m crawler.itviec.reparse --out data/crawl/itviec/reparse-2026-11-15 \
        --compare data/crawl/itviec/2026-11-13/reviews.jsonl

Dùng khi sửa parser: HTML đã che PII nằm ở `data/raw-html/itviec/<ngày>/<slug>-p<trang>.html.gz`, nên
chạy lại parser trên đó là đủ, không cần crawl lại (quy tắc crawl lịch sự: không chạm trang nguồn khi
không cần).

Ghi ra `<out>/reviews.jsonl` cùng định dạng `review.v1` như spider. Lưu ý `source_review_id` là
`content_hash(payload)` nên sửa parser làm id đổi theo – đó là lý do `--compare` đối chiếu bằng
(công ty, tiêu đề) chứ không bằng id.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter
from pathlib import Path

from crawler.itviec.parser import ParseError, parse_review_page
from crawler.itviec.spider import review_url

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw-html" / "itviec"
NAME_RE = re.compile(r"^(?P<slug>.+)-p(?P<page>\d+)$")


def html_files(raw_dir: Path) -> list[Path]:
    return sorted(raw_dir.glob("*/*.html.gz")) + sorted(raw_dir.glob("*/*.html"))


def read_html(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()
    return path.read_text(encoding="utf-8")


def url_of(path: Path) -> str | None:
    """`msb-p1.html.gz` -> URL trang review gốc. None nếu tên file không theo mẫu."""
    m = NAME_RE.match(path.name.split(".")[0])
    return review_url(m["slug"], int(m["page"])) if m else None


def key_of(msg: dict) -> tuple:
    """Khóa đối chiếu không phụ thuộc nội dung văn bản: công ty + tiêu đề + tháng."""
    p = msg["payload"]
    return (msg["company_id"], p.get("title"), p.get("review_month"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=RAW_DIR)
    ap.add_argument("--out", type=Path, required=True, help="thư mục ghi reviews.jsonl")
    ap.add_argument("--compare", type=Path, help="reviews.jsonl cũ để đối chiếu")
    args = ap.parse_args()

    files = html_files(args.raw)
    if not files:
        raise SystemExit(f"Không có HTML nào trong {args.raw}")

    rows: dict[str, dict] = {}
    stat: Counter[str] = Counter()
    for f in files:
        stat["file"] += 1
        url = url_of(f)
        if not url:
            stat["bo_ten_file_la"] += 1
            continue
        try:
            for msg in parse_review_page(read_html(f), url):
                stat["review"] += 1
                rows[msg["source_review_id"]] = msg
        except ParseError as e:
            stat[f"parse_error:{e.args[0]}"] += 1

    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / "reviews.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows.values()), "utf-8")
    print(f"{stat['file']} file -> {stat['review']} review, {len(rows)} review khác nhau")
    print(f"ghi ra {out}")
    for k, v in sorted(stat.items()):
        if k.startswith(("parse_error", "bo_")):
            print(f"  {k}: {v}")

    if args.compare and args.compare.exists():
        old = {}
        for line in args.compare.read_text(encoding="utf-8").splitlines():
            if line.strip():
                m = json.loads(line)
                old[key_of(m)] = m
        new = {key_of(m): m for m in rows.values()}
        both = set(old) & set(new)
        changed = [
            k
            for k in both
            if (new[k]["payload"].get("liked_text"), new[k]["payload"].get("improvement_text"))
            != (old[k]["payload"].get("liked_text"), old[k]["payload"].get("improvement_text"))
        ]
        print(f"\nđối chiếu {args.compare}:")
        print(f"  {len(old)} review cũ, {len(new)} review mới, {len(both)} khớp (công ty + tiêu đề + tháng)")
        print(f"  {len(changed)} review đổi nội dung văn bản")
        for k in changed[:3]:
            print(f"    - {k[0]} / {k[1]}")
            print(f"      cũ : {(old[k]['payload'].get('liked_text') or '')[:110]!r}")
            print(f"      mới: {(new[k]['payload'].get('liked_text') or '')[:110]!r}")


if __name__ == "__main__":
    main()
