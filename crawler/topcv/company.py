"""WM1 – trang công ty TopCV: tìm thêm tin của một công ty đã biết.

Vì sao cần: quét sitemap cho ra tin rải khắp các công ty, nên TopCV và ITviec gần như không chung công ty
(đo 2026-11-15: 331 tin TopCV + 536 tin ITviec chỉ có 9 công ty chung). Không có công ty chung thì không
thể có tin trùng giữa hai trang. Cách nhắm đúng đích: lấy các công ty **đã biết có mặt ở cả hai trang**,
vào trang công ty của họ trên TopCV và lấy hết tin ở đó.

Mỗi trang tin TopCV đều trỏ về trang công ty: `https://www.topcv.vn/cong-ty/<slug>/<id>.html`.
Nhờ vậy lập được bảng "công ty → trang công ty" từ **HTML đã lưu trên máy, không gửi request nào**
(2026-11-15: đủ cho 247/247 công ty TopCV đã crawl).

**Lấy link tin theo mẫu URL, không theo class CSS.** Class trên TopCV đổi thường xuyên; mẫu URL
`/viec-lam/<slug>/<id>.html` thì ổn định và đã có regex kiểm tra ở `crawler/topcv/sitemap.py`.
"""

from __future__ import annotations

import gzip
import re
from collections import Counter
from pathlib import Path

from crawler.topcv.sitemap import JOB_URL_RE, is_allowed

ROOT = Path(__file__).resolve().parents[2]
COMPANY_URL_RE = re.compile(r"https://www\.topcv\.vn/cong-ty/([a-z0-9][a-z0-9-]*)/(\d+)")
JOB_HREF_RE = re.compile(r"https://www\.topcv\.vn/viec-lam/[a-z0-9][a-z0-9-]*/\d+\.html")
PAGE_PARAM = "?page={n}"


def company_url(slug: str, company_id: str) -> str:
    return f"https://www.topcv.vn/cong-ty/{slug}/{company_id}.html"


def company_url_in(page_html: str) -> str | None:
    """Trang công ty mà trang tin này trỏ tới. Lấy link xuất hiện nhiều nhất: trang tin cũng
    chứa link tới công ty khác ở mục 'việc làm liên quan', link của chính công ty lặp nhiều hơn."""
    hits = COMPANY_URL_RE.findall(page_html)
    if not hits:
        return None
    (slug, cid), _ = Counter(hits).most_common(1)[0]
    return company_url(slug, cid)


def job_links(page_html: str) -> list[str]:
    """Các URL tin tuyển dụng trên trang công ty, bỏ trùng, giữ thứ tự xuất hiện."""
    out, seen = [], set()
    for url in JOB_HREF_RE.findall(page_html):
        if url in seen or not JOB_URL_RE.match(url) or not is_allowed(url):
            continue
        seen.add(url)
        out.append(url)
    return out


def page_url(url: str, page: int) -> str:
    """Trang thứ `page` của danh sách tin (page 1 = chính URL đó)."""
    return url if page <= 1 else url + PAGE_PARAM.format(n=page)


def index_from_saved_html(html_dir: Path | None = None) -> dict[str, str]:
    """{source_job_id: trang công ty} đọc từ HTML đã lưu – không gửi request nào."""
    html_dir = html_dir or ROOT / "data" / "raw-html" / "topcv"
    out = {}
    for f in sorted(html_dir.glob("*/*.html.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            url = company_url_in(fh.read())
        if url:
            out[f.name.split(".")[0]] = url
    return out
