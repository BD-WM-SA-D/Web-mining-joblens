"""Đọc sitemap TopCV: https://www.topcv.vn/sitemap.xml → sitemap/jobs.xml → sitemap/jobs_N.xml → /viec-lam/<slug>/<id>.html.

Sitemap không ghi nhóm nghề, nên lọc tin IT làm hai bước: lọc thô theo slug (giảm số request) rồi xác nhận bằng
"Danh mục nghề" trên trang tin (parser.is_it_job).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lxml import etree

SITEMAP_ROOT = "https://www.topcv.vn/sitemap.xml"
JOBS_SITEMAP = "https://www.topcv.vn/sitemap/jobs.xml"
JOB_URL_RE = re.compile(r"^https://www\.topcv\.vn/viec-lam/([^/]+)/(\d+)\.html$")
# Theo robots.txt (2026-10-12) và quy tắc nhóm: không bao giờ chạm đường dẫn CV / riêng tư
FORBIDDEN_PATHS = (
    "/cv/get-private-url/",
    "/private/",
    "/xem-cv/",
    "/xem-cv-draft/",
    "/sua-cv/",
    "/viet-cv/",
    "/edit/cv/",
    "/cv-ung-vien/",
    "/cv-ung-tuyen/",
    "/p/",
)
# Lọc thô theo slug – chỉ để bớt request; trang tin mới là căn cứ cuối cùng.
# So khớp theo TỪ nguyên vẹn của slug (tách bằng "-"), không theo chuỗi con: "ai" không được khớp "tai", "giai".
IT_SLUG_TOKENS = frozenset(
    "developer dev engineer backend frontend fullstack java python php dotnet net nodejs react reactjs angular vue "
    "golang android ios flutter mobile tester devops data ai ml it sql oracle sap odoo erp cloud aws azure "
    "security pentest network sysadmin embedded game unity ux ui blockchain bigdata".split()
)
IT_SLUG_PHRASES = (
    "lap-trinh",
    "kiem-thu",
    "phan-mem",
    "du-lieu",
    "cong-nghe-thong-tin",
    "ky-su-cau-noi",
    "an-ninh-mang",
    "quan-tri-mang",
    "quan-tri-he-thong",
    "bao-mat",
    "business-analyst",
    "machine-learning",
    "tri-tue-nhan-tao",
    "back-end",
    "front-end",
    "full-stack",
    "it-helpdesk",
    "ho-tro-ky-thuat-it",
)
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@dataclass(frozen=True)
class SitemapEntry:
    loc: str
    lastmod: str | None


def parse_sitemap(xml: bytes) -> tuple[str, list[SitemapEntry]]:
    """Trả ('index', các sitemap con) hoặc ('urlset', các URL), kèm lastmod nếu có."""
    root = etree.fromstring(xml.strip())
    kind = etree.QName(root).localname
    tag = "sm:sitemap" if kind == "sitemapindex" else "sm:url"
    entries = [
        SitemapEntry(el.findtext("sm:loc", namespaces=NS).strip(), (el.findtext("sm:lastmod", namespaces=NS) or None))
        for el in root.findall(tag, NS)
    ]
    return ("index" if kind == "sitemapindex" else "urlset"), entries


def job_id(url: str) -> str | None:
    m = JOB_URL_RE.match(url)
    return m.group(2) if m else None


def is_allowed(url: str) -> bool:
    return not any(p in url for p in FORBIDDEN_PATHS)


def looks_it(url: str) -> bool:
    m = JOB_URL_RE.match(url)
    if not m:
        return False
    slug = m.group(1)
    tokens = set(slug.split("-"))
    return bool(tokens & IT_SLUG_TOKENS) or any(f"-{ph}-" in f"-{slug}-" for ph in IT_SLUG_PHRASES)
