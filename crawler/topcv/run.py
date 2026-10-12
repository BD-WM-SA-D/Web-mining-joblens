"""Chạy spider TopCV. CHỈ chạy khi Hoang Le đã cho phép crawl thật (HUONG-DAN, mục 7).

    uv run python -m crawler.topcv.run --max-jobs 20                 # thử nhỏ
    uv run python -m crawler.topcv.run --max-jobs 500 --max-sitemaps 5 --since 2026-10-01

Kết quả: data/crawl/topcv/<ngày>/jobs.jsonl, parse_errors.jsonl; HTML đã che PII ở data/raw-html/topcv/<ngày>/.
"""

from __future__ import annotations

import argparse

from scrapy.crawler import CrawlerProcess

from crawler.topcv.spider import TopcvSpider

HARD_MAX_JOBS = 5000  # chặn gõ nhầm số quá lớn trong một lần chạy


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-jobs", type=int, default=20)
    ap.add_argument("--max-sitemaps", type=int, default=1)
    ap.add_argument("--since", help="chỉ lấy URL có lastmod >= giá trị này (ISO, ví dụ 2026-10-01)")
    ap.add_argument("--all-categories", action="store_true", help="lấy cả tin không phải IT")
    ap.add_argument("--no-slug-filter", action="store_true", help="không lọc thô theo slug (tốn request hơn)")
    args = ap.parse_args()
    if args.max_jobs > HARD_MAX_JOBS:
        raise SystemExit(f"--max-jobs tối đa {HARD_MAX_JOBS} mỗi lần chạy")

    process = CrawlerProcess()
    process.crawl(
        TopcvSpider,
        max_jobs=args.max_jobs,
        max_sitemaps=args.max_sitemaps,
        since=args.since,
        it_only=not args.all_categories,
        slug_filter=not args.no_slug_filter,
    )
    process.start()


if __name__ == "__main__":
    main()
