"""Chạy spider tin tuyển dụng ITviec. CHỈ chạy khi Hoang Le đã cho phép crawl thật (HUONG-DAN, mục 7).

    uv run python -m crawler.itviec.sitemap --fetch            # lấy sitemap việc làm (1 request)
    uv run python -m crawler.itviec.run_jobs --max-jobs 20     # thử nhỏ
    uv run python -m crawler.itviec.run_jobs --max-jobs 615    # cả sitemap, ~1 giờ

Kết quả: data/crawl/itviec-jobs/<ngày>/jobs.jsonl, parse_errors.jsonl;
HTML đã che PII ở data/raw-html/itviec-jobs/<ngày>/. Chạy lại thì bỏ qua tin đã lấy (seen_ids.txt).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scrapy.crawler import CrawlerProcess

from crawler.itviec.job_spider import ItviecJobSpider

HARD_MAX_JOBS = 700  # sitemap hiện có 615 tin; chặn gõ nhầm số lớn


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-jobs", type=int, default=20)
    ap.add_argument("--jobs-xml", type=Path, help="mặc định data/crawl/itviec/sitemap_jobs_vn.xml")
    args = ap.parse_args()
    if args.max_jobs > HARD_MAX_JOBS:
        raise SystemExit(f"--max-jobs tối đa {HARD_MAX_JOBS} mỗi lần chạy")

    print(f"tối đa {args.max_jobs} tin, ≥3 giây/request")
    process = CrawlerProcess()
    process.crawl(ItviecJobSpider, max_jobs=args.max_jobs, jobs_xml=str(args.jobs_xml) if args.jobs_xml else None)
    process.start()


if __name__ == "__main__":
    main()
