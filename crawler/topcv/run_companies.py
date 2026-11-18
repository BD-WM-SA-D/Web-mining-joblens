"""Chạy spider trang công ty TopCV. CHỈ chạy khi Hoang Le đã cho phép crawl thật.

    uv run python -m crawler.topcv.run_companies --companies data/crawl/topcv/shared_companies.txt --max-jobs 50
    uv run python -m crawler.topcv.run_companies --companies ... --dry-run   # in kế hoạch, không gửi request

TopCV chặn sau khoảng 65 request (đo 2026-11-15) → để `--max-jobs` ở 40-60 mỗi ngày.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scrapy.crawler import CrawlerProcess

from crawler.topcv.company_spider import TopcvCompanySpider

HARD_MAX_JOBS = 200  # trang nguồn chặn sau ~65 request: chặn gõ nhầm số lớn trong một lần chạy


def read_companies(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", type=Path, required=True, help="file mỗi dòng một URL trang công ty")
    ap.add_argument("--max-jobs", type=int, default=50)
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--all-categories", action="store_true", help="lấy cả tin không phải IT")
    ap.add_argument("--dry-run", action="store_true", help="in kế hoạch, không gửi request")
    args = ap.parse_args()
    if args.max_jobs > HARD_MAX_JOBS:
        raise SystemExit(f"--max-jobs toi da {HARD_MAX_JOBS} moi lan chay")

    companies = read_companies(args.companies)
    lo, hi = len(companies), len(companies) * args.max_pages
    print(f"{len(companies)} trang cong ty, toi da {args.max_jobs} tin, {args.max_pages} trang/cong ty")
    print(f"uoc luong request: {lo}-{hi} (danh sach) + toi da {args.max_jobs} (tin)")
    for u in companies:
        print("  ", u)
    if args.dry_run:
        print("--dry-run: khong gui request nao")
        return

    process = CrawlerProcess()
    process.crawl(
        TopcvCompanySpider,
        companies=companies,
        max_jobs=args.max_jobs,
        max_pages=args.max_pages,
        it_only=not args.all_categories,
    )
    process.start()


if __name__ == "__main__":
    main()
