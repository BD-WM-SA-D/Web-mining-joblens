"""Spider tin tuyển dụng ITviec: sitemap việc làm → trang tin → job_posting.v1 (JSONL trong data/).

Chạy (chỉ khi Hoang Le cho phép crawl thật):
    uv run python -m crawler.itviec.run_jobs --max-jobs 50

Nguồn URL: `twinnings_jobs_desc_vn.xml` (615 tin IT đang mở, 2026-11-13) – tải bằng
`crawler.itviec.sitemap`, không phải crawl nội dung.

Giới hạn cứng giống spider TopCV: robots.txt, ≥3 giây/request, không cookie, KHÔNG đăng nhập.
Gặp HTTP 429/403 thì DỪNG NGAY cả lần chạy, không thử lại.
Lương bị ẩn với khách chưa đăng nhập → `salary_text` thường rỗng, đó là hành vi đúng (xem job_parser).
"""

from __future__ import annotations

import gzip
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import scrapy

from crawler.common import mask_pii, parse_error_message, schema_errors
from crawler.itviec.job_parser import PARSER_VERSION, ParseError, job_id, parse_job_page
from crawler.itviec.sitemap import DEFAULT_JOBS_XML, LOC_RE
from crawler.topcv.spider import POLITE_SETTINGS, check_not_blocked

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UA = "JobLensStudentProject/0.1 (HUST course project, non-commercial; contact in repo README)"


class ItviecJobSpider(scrapy.Spider):
    name = "itviec-job"
    allowed_domains = ["itviec.com"]
    custom_settings = {**POLITE_SETTINGS, "USER_AGENT": os.environ.get("JOBLENS_CRAWL_USER_AGENT", DEFAULT_UA)}

    def __init__(
        self,
        max_jobs: int = 50,
        jobs_xml: str | None = None,
        out_dir: str | None = None,
        state_dir: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_jobs = int(max_jobs)
        self.jobs_xml = Path(jobs_xml) if jobs_xml else DEFAULT_JOBS_XML
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        self.out_dir = Path(out_dir) if out_dir else ROOT / "data" / "crawl" / "itviec-jobs" / day
        self.html_dir = ROOT / "data" / "raw-html" / "itviec-jobs" / day
        self.state_dir = Path(state_dir) if state_dir else ROOT / "data" / "crawl" / "itviec-jobs"
        self.seen = self._load_seen()
        self.stats_local = {"jobs_ok": 0, "parse_errors": 0, "skipped_seen": 0}
        self._jobs_f = self._err_f = self._seen_f = None

    # ---- vòng đời -----------------------------------------------------------------
    def _open_files(self):
        if self._jobs_f is None:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            self._jobs_f = (self.out_dir / "jobs.jsonl").open("a", encoding="utf-8")
            self._err_f = (self.out_dir / "parse_errors.jsonl").open("a", encoding="utf-8")
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self._seen_f = (self.state_dir / "seen_ids.txt").open("a", encoding="utf-8")

    def _load_seen(self) -> set[str]:
        seen: set[str] = set()
        f = self.state_dir / "seen_ids.txt"
        if f.exists():
            seen |= {ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()}
        for jf in self.state_dir.glob("*/jobs.jsonl"):
            for ln in jf.read_text(encoding="utf-8").splitlines():
                try:
                    seen.add(json.loads(ln)["source_job_id"])
                except (json.JSONDecodeError, KeyError):
                    continue
        return seen

    def closed(self, reason):
        for f in (self._jobs_f, self._err_f, self._seen_f):
            if f:
                f.close()
        self.logger.info("Kết thúc (%s): %s", reason, self.stats_local)

    # ---- duyệt sitemap ------------------------------------------------------------
    async def start(self):
        if not self.jobs_xml.exists():
            raise FileNotFoundError(f"Chưa có {self.jobs_xml} – chạy `python -m crawler.itviec.sitemap --fetch` trước")
        n = 0
        for loc in LOC_RE.findall(self.jobs_xml.read_text(encoding="utf-8")):
            sid = job_id(loc)
            if not sid:
                continue
            if sid in self.seen:
                self.stats_local["skipped_seen"] += 1
                continue
            if n >= self.max_jobs:
                break
            n += 1
            yield scrapy.Request(loc, callback=self.parse_job)

    # ---- trang tin ----------------------------------------------------------------
    def parse_job(self, response):
        check_not_blocked(response)
        self._open_files()
        sid = job_id(response.url)
        self._save_html(response, sid)
        if sid and sid not in self.seen:
            self.seen.add(sid)
            self._seen_f.write(sid + "\n")
            self._seen_f.flush()
        try:
            message = parse_job_page(response.text, response.url)
        except ParseError as exc:
            self._error(response.url, exc.error_type, str(exc), sid)
            return
        errors = schema_errors(message)
        if errors:
            self._error(response.url, "schema_violation", "; ".join(errors), sid)
            return
        self._jobs_f.write(json.dumps(message, ensure_ascii=False) + "\n")
        self._jobs_f.flush()
        self.stats_local["jobs_ok"] += 1
        yield message

    def _save_html(self, response, name: str | None):
        """HTML thô đã che email/SĐT, nén gzip (ADR 0001 D1). Lưu TRƯỚC khi parse."""
        self.html_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(self.html_dir / f"{name or 'unknown'}.html.gz", "wt", encoding="utf-8") as f:
            f.write(mask_pii(response.text))

    def _error(self, url, error_type, message, sid=None):
        self.stats_local["parse_errors"] += 1
        rec = parse_error_message(
            "itviec", error_type, message, url=url, source_record_id=sid, component_version=PARSER_VERSION
        )
        self._err_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._err_f.flush()
