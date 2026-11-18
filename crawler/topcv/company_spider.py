"""Spider trang công ty TopCV: trang công ty → tin của chính công ty đó → job_posting.v1.

Chạy (chỉ khi Hoang Le cho phép crawl thật):
    uv run python -m crawler.topcv.run_companies --companies data/crawl/topcv/shared_companies.txt --max-jobs 50

Khác `TopcvSpider` ở chỗ **không lọc slug IT**: đã biết công ty này có mặt trên ITviec nên lấy hết tin
của họ, kể cả tin có tiêu đề không chứa từ khóa IT (tin trùng giữa hai trang hay viết tiêu đề khác nhau).
Bước xác nhận bằng "Danh mục nghề" trên trang tin vẫn giữ (`it_only`).

Giữ nguyên mọi giới hạn lịch sự của `POLITE_SETTINGS`: robots.txt, 3 giây/request, không cookie,
gặp 403/429 là dừng cả lần chạy. Giới hạn thật của TopCV đo được 2026-11-15: **chặn sau 65 request**,
nên `--max-jobs` nên để 40-60 mỗi ngày.
"""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

import scrapy

from crawler.common import mask_pii, parse_error_message, schema_errors
from crawler.topcv.company import job_links, page_url
from crawler.topcv.parser import PARSER_VERSION, ParseError, parse_job_page
from crawler.topcv.sitemap import job_id
from crawler.topcv.spider import POLITE_SETTINGS, ROOT, TopcvSpider, check_not_blocked


class TopcvCompanySpider(scrapy.Spider):
    name = "topcv-company"
    allowed_domains = ["www.topcv.vn"]
    custom_settings = POLITE_SETTINGS

    def __init__(
        self,
        companies: list[str] | None = None,
        max_jobs: int = 50,
        max_pages: int = 3,
        it_only: bool = True,
        out_dir: str | None = None,
        state_dir: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.companies = list(companies or [])
        self.max_jobs = int(max_jobs)
        self.max_pages = int(max_pages)
        self.it_only = str(it_only).lower() not in {"0", "false", "no"}
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        self.out_dir = Path(out_dir) if out_dir else ROOT / "data" / "crawl" / "topcv" / day
        self.html_dir = ROOT / "data" / "raw-html" / "topcv" / day
        self.state_dir = Path(state_dir) if state_dir else ROOT / "data" / "crawl" / "topcv"
        # dùng chung seen_ids.txt với TopcvSpider để không tải lại tin đã có
        self.seen = TopcvSpider._load_seen(self)
        self.requested = 0
        self.stats_local = {"jobs_ok": 0, "skipped_not_it": 0, "skipped_seen": 0, "parse_errors": 0}
        self._jobs_f = self._err_f = self._seen_f = None

    def _open_files(self):
        if self._jobs_f is None:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            self._jobs_f = (self.out_dir / "jobs.jsonl").open("a", encoding="utf-8")
            self._err_f = (self.out_dir / "parse_errors.jsonl").open("a", encoding="utf-8")
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self._seen_f = (self.state_dir / "seen_ids.txt").open("a", encoding="utf-8")

    def closed(self, reason):
        for f in (self._jobs_f, self._err_f, self._seen_f):
            if f:
                f.close()
        self.logger.info("Ket thuc (%s): %s", reason, self.stats_local)

    # ---- trang công ty -----------------------------------------------------------------------------
    async def start(self):
        for url in self.companies:
            yield scrapy.Request(url, callback=self.parse_company, cb_kwargs={"base": url, "page": 1})

    def parse_company(self, response, base: str, page: int):
        check_not_blocked(response)
        new = 0
        for url in job_links(response.text):
            if self.requested >= self.max_jobs:
                return
            sid = job_id(url)
            if not sid:
                continue
            if sid in self.seen:
                self.stats_local["skipped_seen"] += 1
                continue
            self.requested += 1
            new += 1
            yield scrapy.Request(url, callback=self.parse_job)
        # còn tin mới ở trang này thì xem trang sau; hết tin mới thì dừng để khỏi tốn request
        if new and page < self.max_pages and self.requested < self.max_jobs:
            yield scrapy.Request(
                page_url(base, page + 1), callback=self.parse_company, cb_kwargs={"base": base, "page": page + 1}
            )

    # ---- trang tin ---------------------------------------------------------------------------------
    def parse_job(self, response):
        check_not_blocked(response)
        self._open_files()
        sid = job_id(response.url)
        if sid and sid not in self.seen:
            self.seen.add(sid)
            self._seen_f.write(sid + "\n")
            self._seen_f.flush()
        try:
            parsed = parse_job_page(response.text, response.url)
        except ParseError as exc:
            self._error(response.url, exc.error_type, str(exc))
            return
        if self.it_only and not parsed.is_it:
            self.stats_local["skipped_not_it"] += 1
            return
        errors = schema_errors(parsed.message)
        if errors:
            self._error(response.url, "schema_violation", "; ".join(errors))
            return
        self.html_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(self.html_dir / f"{sid}.html.gz", "wt", encoding="utf-8") as f:
            f.write(mask_pii(response.text))
        self._jobs_f.write(json.dumps(parsed.message, ensure_ascii=False) + "\n")
        self._jobs_f.flush()
        self.stats_local["jobs_ok"] += 1
        yield parsed.message

    def _error(self, url, error_type, message):
        self.stats_local["parse_errors"] += 1
        rec = parse_error_message(
            "topcv", error_type, message, url=url, source_record_id=job_id(url), component_version=PARSER_VERSION
        )
        self._err_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._err_f.flush()
