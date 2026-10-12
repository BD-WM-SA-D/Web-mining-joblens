"""Spider TopCV: sitemap tin → trang tin IT → job_posting.v1 (JSONL trong data/, đã gitignore).

Chạy (chỉ khi Hoang Le cho phép crawl thật):
    uv run python -m crawler.topcv.run --max-jobs 20

Giới hạn cứng: tuân thủ robots.txt, 1 request/giây/domain, không cookie, không đăng nhập, không chạm đường dẫn CV.
"""

from __future__ import annotations

import gzip
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import scrapy

from crawler.common import mask_pii, parse_error_message, schema_errors
from crawler.topcv.parser import PARSER_VERSION, ParseError, parse_job_page
from crawler.topcv.sitemap import JOBS_SITEMAP, is_allowed, job_id, looks_it, parse_sitemap

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UA = "JobLensStudentProject/0.1 (HUST course project, non-commercial; contact in repo README)"

POLITE_SETTINGS = {
    "ROBOTSTXT_OBEY": True,
    "USER_AGENT": os.environ.get("JOBLENS_CRAWL_USER_AGENT", DEFAULT_UA),
    "DOWNLOAD_DELAY": 1.0,
    "RANDOMIZE_DOWNLOAD_DELAY": True,
    "CONCURRENT_REQUESTS": 1,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_START_DELAY": 1.0,
    "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
    "COOKIES_ENABLED": False,
    "RETRY_TIMES": 2,
    "TELNETCONSOLE_ENABLED": False,
    "LOG_LEVEL": "INFO",
}


class TopcvSpider(scrapy.Spider):
    name = "topcv"
    allowed_domains = ["www.topcv.vn"]
    custom_settings = POLITE_SETTINGS

    def __init__(
        self,
        max_jobs: int = 20,
        max_sitemaps: int = 1,
        since: str | None = None,
        it_only: bool = True,
        slug_filter: bool = True,
        out_dir: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_jobs = int(max_jobs)
        self.max_sitemaps = int(max_sitemaps)
        self.since = since  # chỉ lấy URL có lastmod >= since (ISO), cho crawl tăng dần
        self.it_only = str(it_only).lower() not in {"0", "false", "no"}
        self.slug_filter = str(slug_filter).lower() not in {"0", "false", "no"}
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        self.out_dir = Path(out_dir) if out_dir else ROOT / "data" / "crawl" / "topcv" / day
        self.html_dir = ROOT / "data" / "raw-html" / "topcv" / day
        self.requested = 0
        self.stats_local = {"jobs_ok": 0, "skipped_not_it": 0, "parse_errors": 0}
        self._jobs_f = self._err_f = None

    # ---- vòng đời -----------------------------------------------------------------
    def _open_files(self):
        if self._jobs_f is None:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            self._jobs_f = (self.out_dir / "jobs.jsonl").open("a", encoding="utf-8")
            self._err_f = (self.out_dir / "parse_errors.jsonl").open("a", encoding="utf-8")

    def closed(self, reason):
        for f in (self._jobs_f, self._err_f):
            if f:
                f.close()
        self.logger.info("Kết thúc (%s): %s", reason, self.stats_local)

    # ---- sitemap ------------------------------------------------------------------
    async def start(self):
        yield scrapy.Request(JOBS_SITEMAP, callback=self.parse_index)

    def parse_index(self, response):
        _, children = parse_sitemap(response.body)
        for child in children[: self.max_sitemaps]:
            yield scrapy.Request(child.loc, callback=self.parse_urlset)

    def parse_urlset(self, response):
        _, entries = parse_sitemap(response.body)
        for e in entries:
            if self.requested >= self.max_jobs:
                return
            if not job_id(e.loc) or not is_allowed(e.loc):
                continue
            if self.slug_filter and not looks_it(e.loc):
                continue
            if self.since and e.lastmod and e.lastmod < self.since:
                continue
            self.requested += 1
            yield scrapy.Request(e.loc, callback=self.parse_job, cb_kwargs={"lastmod": e.lastmod})

    # ---- trang tin ----------------------------------------------------------------
    def parse_job(self, response, lastmod: str | None = None):
        self._open_files()
        try:
            parsed = parse_job_page(response.text, response.url, lastmod=lastmod)
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
        self._save_html(response)
        self._jobs_f.write(json.dumps(parsed.message, ensure_ascii=False) + "\n")
        self.stats_local["jobs_ok"] += 1
        yield parsed.message

    def _save_html(self, response):
        """HTML thô đã che email/SĐT, nén gzip – bản cục bộ của s3://joblens/raw-html/ (ADR 0001 D1)."""
        self.html_dir.mkdir(parents=True, exist_ok=True)
        path = self.html_dir / f"{job_id(response.url)}.html.gz"
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(mask_pii(response.text))

    def _error(self, url, error_type, message):
        self.stats_local["parse_errors"] += 1
        rec = parse_error_message(
            "topcv", error_type, message, url=url, source_record_id=job_id(url), component_version=PARSER_VERSION
        )
        self._err_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
