"""Chạy spider review ITviec. CHỈ chạy khi Hoang Le đã cho phép crawl thật (HUONG-DAN, mục 7).

    uv run python -m crawler.itviec.run --companies ntt-data-vietnam --max-pages 1      # thử 1 công ty
    uv run python -m crawler.itviec.run --companies-file data/crawl/itviec/companies.txt --max-pages 2

Kết quả: data/crawl/itviec/<ngày>/reviews.jsonl, parse_errors.jsonl; HTML đã che PII ở data/raw-html/itviec/<ngày>/.
Mỗi công ty × mỗi trang = 1 request, cách nhau ≥ 3 giây. HARD_MAX_REQUESTS chặn gõ nhầm số lớn.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scrapy.crawler import CrawlerProcess

from crawler.itviec.spider import ItviecReviewSpider

HARD_MAX_REQUESTS = 400  # mỗi lần chạy, theo quy tắc "vài trăm request/ngày"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", help="danh sách slug, phân tách bằng dấu phẩy")
    ap.add_argument("--companies-file", type=Path, help="file mỗi dòng một slug")
    ap.add_argument("--max-pages", type=int, default=1, help="số trang review tối đa mỗi công ty")
    args = ap.parse_args()

    slugs: list[str] = []
    if args.companies:
        slugs += [s.strip() for s in args.companies.split(",") if s.strip()]
    if args.companies_file:
        slugs += [ln.strip() for ln in args.companies_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    slugs = list(dict.fromkeys(slugs))
    if not slugs:
        raise SystemExit("Cần --companies hoặc --companies-file")
    if len(slugs) * args.max_pages > HARD_MAX_REQUESTS:
        raise SystemExit(f"{len(slugs)} công ty × {args.max_pages} trang vượt {HARD_MAX_REQUESTS} request mỗi lần chạy")

    print(
        f"{len(slugs)} công ty × tối đa {args.max_pages} trang ≈ {len(slugs) * args.max_pages} request, ≥3 giây/request"
    )
    process = CrawlerProcess()
    process.crawl(ItviecReviewSpider, companies=slugs, max_pages=args.max_pages)
    process.start()


if __name__ == "__main__":
    main()
