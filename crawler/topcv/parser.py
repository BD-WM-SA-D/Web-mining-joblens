"""Parser trang tin TopCV → message job_posting.v1.

Nguồn chính là khối JSON-LD schema.org/JobPosting (ổn định hơn class CSS). HTML chỉ dùng cho
"Danh mục Nghề liên quan" (box-category) → xác định tin IT.
skill_tags lấy từ JSON-LD `skills` (= khối "Kỹ năng cần có"). Không lấy tag "Yêu cầu"/"Chuyên môn" trong job-tags:
đó là kinh nghiệm, bằng cấp, giới tính, vị trí, lĩnh vực – không phải kỹ năng.
Mô tả trong JSON-LD có 3 phần <h2>: Mô tả công việc / Yêu cầu ứng viên / Quyền lợi được hưởng.
Cấu trúc ghi nhận ngày 2026-10-12 trên 2 trang mẫu; TopCV đổi giao diện thì sửa ở đây.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from lxml import html as lxml_html

from crawler.common import html_to_text, job_message, mask_pii
from crawler.topcv.sitemap import job_id

PARSER_VERSION = "topcv-parser:0.1.0"
SECTION_KEYS = {
    "description": ("mô tả công việc",),
    "requirements": ("yêu cầu ứng viên", "yêu cầu công việc"),
    "benefits": ("quyền lợi",),
}
IT_CATEGORY = "công nghệ thông tin"


@dataclass
class ParsedJob:
    message: dict  # job_posting.v1
    is_it: bool
    category_path: list[str]


class ParseError(Exception):
    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type


def _job_posting_ld(doc) -> dict:
    for raw in doc.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    raise ParseError("missing_jsonld", "Không tìm thấy JSON-LD JobPosting")


def _split_sections(desc_html: str | None) -> dict[str, str | None]:
    """Tách mô tả thành 3 phần theo tiêu đề <h2>; không có tiêu đề thì cả khối là description."""
    out = dict.fromkeys(SECTION_KEYS)
    if not desc_html:
        return out
    parts = re.split(r"(?i)<h2[^>]*>(.*?)</h2>", desc_html)
    if len(parts) == 1:
        out["description"] = html_to_text(desc_html)
        return out
    for heading, body in zip(parts[1::2], parts[2::2], strict=True):
        h = html_to_text(heading) or ""
        for key, words in SECTION_KEYS.items():
            if any(w in h.lower() for w in words):
                out[key] = html_to_text(body)
    return out


def _salary_text(base: dict | None) -> str | None:
    value = (base or {}).get("value") or {}
    if isinstance(value.get("value"), str):
        return value["value"].strip()  # ví dụ "Thoả thuận"
    lo, hi = value.get("minValue"), value.get("maxValue")
    cur = (base or {}).get("currency") or ""
    if lo and hi:
        return f"{lo} - {hi} {cur}".strip()
    if lo:
        return f"Từ {lo} {cur}".strip()
    if hi:
        return f"Tới {hi} {cur}".strip()
    return None


def _locations(job_location) -> list[str]:
    places = job_location if isinstance(job_location, list) else [job_location] if job_location else []
    regions = []
    for p in places:
        region = ((p or {}).get("address") or {}).get("addressRegion")
        if region and region not in regions:
            regions.append(region)
    return regions


def category_path(doc) -> list[str]:
    """Các mục trong khối "Danh mục Nghề liên quan", ví dụ ['Công nghệ Thông tin', 'Software Testing', ...]."""
    for box in doc.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " box-category ")]'):
        text = " ".join(box.text_content().split())
        if text.startswith("Danh mục Nghề liên quan"):
            return [" ".join(a.text_content().split()) for a in box.xpath(".//a") if a.text_content().strip()]
    return []


def split_skills(raw) -> list[str]:
    """Tách chuỗi "A, B (ví dụ: C, D)" theo dấu phẩy nằm ngoài ngoặc; bỏ trùng."""
    out, buf, depth = [], "", 0
    for ch in str(raw or ""):
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if ch == "," and depth <= 0:
            out.append(buf)
            buf, depth = "", 0
        else:
            buf += ch
    out.append(buf)
    seen: list[str] = []
    for s in (" ".join(x.split()) for x in out):
        if s and s not in seen:
            seen.append(s)
    return seen


def is_it_job(doc, ld: dict) -> bool:
    """Tin IT khi danh mục CHÍNH (mục đầu tiên) là Công nghệ Thông tin; không có khối danh mục thì xét industry."""
    cats = category_path(doc)
    if cats:
        return IT_CATEGORY in cats[0].lower()
    return str(ld.get("industry", "")).lower().startswith("it")


def parse_job_page(html: str, url: str, lastmod: str | None = None, crawl_ts: str | None = None) -> ParsedJob:
    """Trả message job_posting.v1 kèm cờ IT. Ném ParseError nếu thiếu dữ liệu bắt buộc."""
    sid = job_id(url)
    if not sid:
        raise ParseError("bad_url", f"URL không đúng dạng tin TopCV: {url}")
    doc = lxml_html.fromstring(html)
    ld = _job_posting_ld(doc)
    title = (ld.get("title") or "").strip()
    if not title:
        raise ParseError("missing_title", "JSON-LD không có title")

    org = ld.get("hiringOrganization") or {}
    ident = ld.get("identifier") or {}
    months = (ld.get("experienceRequirements") or {}).get("monthsOfExperience")
    sections = _split_sections(ld.get("description"))
    skills = split_skills(ld.get("skills"))
    valid = ld.get("validThrough")
    cats = category_path(doc)

    payload = {
        "title": title,
        "company_name": org.get("name"),
        "company_id": str(ident["value"]) if ident.get("value") is not None else None,
        "salary_text": _salary_text(ld.get("baseSalary")),
        "locations": _locations(ld.get("jobLocation")),
        "experience_text": f"{months} tháng" if months is not None else None,
        "level": ld.get("occupationalCategory"),
        "employment_type": ld.get("employmentType"),
        "category": " > ".join(cats[:3]) if cats else ld.get("industry"),
        "deadline": valid[:10] if valid else None,
        "date_posted": (ld.get("datePosted") or "")[:10] or None,
        "skill_tags": skills,
        "description": mask_pii(sections["description"]),
        "requirements": mask_pii(sections["requirements"]),
        "benefits": mask_pii(sections["benefits"]),
    }
    msg = job_message("topcv", sid, url, payload, lastmod=lastmod, crawl_ts=crawl_ts)
    return ParsedJob(message=msg, is_it=is_it_job(doc, ld), category_path=cats)
