"""Spider ITviec: trang review công ty → review.v1 (JSONL trong data/, đã gitignore).

Chạy (chỉ khi Hoang Le cho phép crawl thật):
    uv run python -m crawler.itviec.run --companies <slug> --max-pages 1   # thử 1 công ty

Giới hạn cứng, giống spider TopCV: tuân thủ robots.txt, tối thiểu 3 giây/request, không cookie,
KHÔNG đăng nhập (chỉ lấy review công khai), không lách chống bot.
Gặp HTTP 429 hoặc 403 thì DỪNG NGAY cả lần chạy, không thử lại (sự cố TopCV 2026-10-12).

robots.txt ITviec (xem 2026-11-12): chỉ cấm /subscriptions/new, không cấm trang review,
không có Crawl-delay → vẫn tự đặt 3 giây/request.
Danh sách công ty lấy từ sitemap chính thức (crawler/itviec/sitemap.py): 12.422 trang review.
"""

from __future__ import annotations

import gzip
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import scrapy

from crawler.common import mask_pii, parse_error_message, schema_errors
from crawler.itviec.parser import PARSER_VERSION, ParseError, company_slug, parse_ratings, parse_review_page
from crawler.topcv.spider import POLITE_SETTINGS, check_not_blocked

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://itviec.com"
DEFAULT_UA = "JobLensStudentProject/0.1 (HUST course project, non-commercial; contact in repo README)"


def review_url(slug: str, page: int = 1) -> str:
    """URL trang review tiếng Việt (dạng trong sitemap twinnings_companies_review_vn.xml)."""
    base = f"{BASE}/nha-tuyen-dung/{slug}/danh-gia"
    return base if page <= 1 else f"{base}?page={page}"


class ItviecReviewSpider(scrapy.Spider):
    name = "itviec-review"
    allowed_domains = ["itviec.com"]
    custom_settings = {**POLITE_SETTINGS, "USER_AGENT": os.environ.get("JOBLENS_CRAWL_USER_AGENT", DEFAULT_UA)}

    def __init__(
        self,
        companies: list[str] | str,
        max_pages: int = 1,
        out_dir: str | None = None,
        state_dir: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.companies = companies.split(",") if isinstance(companies, str) else list(companies)
        self.max_pages = int(max_pages)
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        self.out_dir = Path(out_dir) if out_dir else ROOT / "data" / "crawl" / "itviec" / day
        self.html_dir = ROOT / "data" / "raw-html" / "itviec" / day
        self.state_dir = Path(state_dir) if state_dir else ROOT / "data" / "crawl" / "itviec"
        self.seen = self._load_seen()
        self.stats_local = {"reviews_ok": 0, "ratings_ok": 0, "pages": 0, "parse_errors": 0, "companies_empty": 0}
        self._rev_f = self._err_f = self._seen_f = self._rate_f = None

    # ---- vòng đời -----------------------------------------------------------------
    def _open_files(self):
        if self._rev_f is None:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            self._rev_f = (self.out_dir / "reviews.jsonl").open("a", encoding="utf-8")
            self._rate_f = (self.out_dir / "review_ratings.jsonl").open("a", encoding="utf-8")
            self._err_f = (self.out_dir / "parse_errors.jsonl").open("a", encoding="utf-8")
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self._seen_f = (self.state_dir / "seen_reviews.txt").open("a", encoding="utf-8")

    def _load_seen(self) -> set[str]:
        """'<slug>:<review_id>' đã lấy, để chạy tiếp không ghi trùng."""
        seen: set[str] = set()
        f = self.state_dir / "seen_reviews.txt"
        if f.exists():
            seen |= {ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()}
        for rf in self.state_dir.glob("*/reviews.jsonl"):
            for ln in rf.read_text(encoding="utf-8").splitlines():
                try:
                    m = json.loads(ln)
                    seen.add(f"{m['company_id']}:{m['source_review_id']}")
                except (json.JSONDecodeError, KeyError):
                    continue
        return seen

    def closed(self, reason):
        for f in (self._rev_f, self._err_f, self._seen_f, self._rate_f):
            if f:
                f.close()
        self.logger.info("Kết thúc (%s): %s", reason, self.stats_local)

    # ---- trang review -------------------------------------------------------------
    async def start(self):
        for slug in self.companies:
            yield scrapy.Request(review_url(slug.strip()), callback=self.parse_reviews, cb_kwargs={"page": 1})

    def parse_reviews(self, response, page: int = 1):
        check_not_blocked(response)
        self._open_files()
        self.stats_local["pages"] += 1
        slug = company_slug(response.url)
        # lưu HTML TRƯỚC khi parse: lúc parse lỗi mới là lúc cần HTML nhất để sửa selector
        self._save_html(response, f"{slug}-p{page}")
        # Điểm sao của MỌI review (kể cả review bị che) – ghi trước, độc lập với việc parse văn bản có lỗi hay không.
        # Dữ liệu này mất là mất hẳn: review mới sẽ đẩy review hiện tại vào vùng bị che.
        n_rate = 0
        for r in parse_ratings(response.text, response.url):
            self._rate_f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n_rate += 1
        self._rate_f.flush()
        self.stats_local["ratings_ok"] += n_rate
        try:
            messages = parse_review_page(response.text, response.url)
        except ParseError as exc:
            if exc.error_type == "no_reviews":
                self.stats_local["companies_empty"] += 1
            self._error(response.url, exc.error_type, str(exc), slug)
            return
        new = 0
        for msg in messages:
            key = f"{msg['company_id']}:{msg['source_review_id']}"
            if key in self.seen:
                continue
            errors = schema_errors(msg, "review.v1")
            if errors:
                self._error(response.url, "schema_violation", "; ".join(errors), slug)
                continue
            self.seen.add(key)
            self._seen_f.write(key + "\n")
            self._rev_f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            new += 1
            self.stats_local["reviews_ok"] += 1
            yield msg
        for f in (self._rev_f, self._seen_f):
            f.flush()
        self.logger.info(
            "%s trang %d: %d review công khai (%d mới), %d điểm sao", slug, page, len(messages), new, n_rate
        )
        # Lật trang khi trang này CÓ review công khai, kể cả review đã lấy lần trước (new == 0):
        # dựa vào `new` sẽ không bao giờ sang được trang 2 khi chạy lại cùng một công ty.
        if messages and page < self.max_pages:
            yield scrapy.Request(review_url(slug, page + 1), callback=self.parse_reviews, cb_kwargs={"page": page + 1})

    def _save_html(self, response, name: str):
        """HTML thô đã che email/SĐT, nén gzip (ADR 0001 D1)."""
        self.html_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(self.html_dir / f"{name}.html.gz", "wt", encoding="utf-8") as f:
            f.write(mask_pii(response.text))

    def _error(self, url, error_type, message, slug=None):
        self.stats_local["parse_errors"] += 1
        rec = parse_error_message(
            "itviec", error_type, message, url=url, source_record_id=slug, component_version=PARSER_VERSION
        )
        self._err_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._err_f.flush()
