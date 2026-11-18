"""Parser trang tin tuyển dụng ITviec → message job_posting.v1 (WM1: nguồn thứ hai để tìm tin trùng).

Cấu trúc ghi nhận 2026-11-13 trên `/viec-lam-it/<chuc-danh>-<slug-cong-ty>-<id>`:

- Khối JSON-LD `schema.org/JobPosting` (giống TopCV, ổn định hơn class CSS) cho: title, datePosted,
  validThrough, skills (chuỗi ngăn bằng dấu phẩy), hiringOrganization.name, jobLocation, employmentType,
  experienceRequirements.monthsOfExperience, description (HTML), jobBenefits (HTML).
- HTML cho phần **Yêu cầu công việc**: `<h2>Yêu cầu công việc</h2>` + khối ngay sau (JSON-LD gộp
  mô tả và yêu cầu vào `description` nên phải tách lại từ HTML).

**Lương:** ITviec ẩn lương với khách chưa đăng nhập – `baseSalary.value.value` thường là câu mời
("You'll love it", "Đăng nhập để xem mức lương"). Parser chỉ giữ chuỗi lương khi nó có chữ số,
còn lại để `None`; không suy đoán. Việc chuẩn hoá lương là của Big Data (ADR 0001 D2).
"""

from __future__ import annotations

import json
import re

from lxml import html as lxml_html

from crawler.common import html_to_text, job_message, mask_pii

PARSER_VERSION = "itviec-job-parser:0.1.0"
JOB_ID_RE = re.compile(r"-(\d+)$")
# câu mời đăng nhập thay cho lương
LOGIN_HINT_RE = re.compile(r"đăng nhập|sign ?in|you'?ll love it|login", re.IGNORECASE)
REQ_HEADINGS = ("yêu cầu công việc", "your skills and experience", "kỹ năng & chuyên môn")


def _obj(value) -> dict:
    """JSON-LD của ITviec không nhất quán: cùng một trường có khi là object, có khi là chuỗi
    (`experienceRequirements` = "No requirements"). Trả về {} cho mọi thứ không phải dict."""
    return value if isinstance(value, dict) else {}


class ParseError(Exception):
    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type


def job_id(url: str) -> str | None:
    """`/viec-lam-it/data-ops-senior-...-momo-3554` → `3554` (id tin trên ITviec)."""
    m = JOB_ID_RE.search(url.split("?")[0].rstrip("/").rsplit("/", 1)[-1])
    return m.group(1) if m else None


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


def _salary_text(ld: dict) -> str | None:
    """Chỉ giữ lương nếu có chữ số; câu mời đăng nhập → None."""
    salary = _obj(ld.get("baseSalary"))
    value = _obj(salary.get("value"))
    raw = value.get("value")
    if not isinstance(raw, str) or not re.search(r"\d", raw) or LOGIN_HINT_RE.search(raw):
        return None
    currency = salary.get("currency") or ""
    unit = value.get("unitText", "")
    return " ".join(x for x in (raw, currency, unit) if x).strip()


def _locations(ld: dict) -> list[str]:
    out = []
    places = ld.get("jobLocation") or []
    for p in places if isinstance(places, list) else [places]:
        addr = _obj(_obj(p).get("address"))
        city = addr.get("addressLocality") or addr.get("addressRegion")
        if city and city not in out:
            out.append(city)
    return out


def _requirements(doc) -> str | None:
    """Phần 'Yêu cầu công việc': lấy các phần tử sau <h2> cho tới <h2> kế tiếp."""
    for h2 in doc.xpath("//h2"):
        if " ".join("".join(h2.itertext()).split()).lower() not in REQ_HEADINGS:
            continue
        parts = []
        for el in h2.itersiblings():
            if el.tag == "h2":
                break
            parts.append(lxml_html.tostring(el, encoding="unicode"))
        # phần yêu cầu có thể nằm trong thẻ cha chứa h2 (khối imy-5 paragraph)
        if not parts and (parent := h2.getparent()) is not None:
            parts = [lxml_html.tostring(el, encoding="unicode") for el in parent if el is not h2]
        return html_to_text("".join(parts)) if parts else None
    return None


def _skills(ld: dict) -> list[str]:
    raw = ld.get("skills")
    if isinstance(raw, list):
        items = [str(x) for x in raw]
    elif isinstance(raw, str):
        items = raw.split(",")
    else:
        return []
    return [s.strip() for s in items if s.strip()]


def parse_job_page(page_html: str, url: str, lastmod: str | None = None, crawl_ts: str | None = None) -> dict:
    """Trang tin ITviec → message job_posting.v1."""
    sid = job_id(url)
    if not sid:
        raise ParseError("bad_url", f"URL không có id tin: {url}")
    doc = lxml_html.fromstring(page_html)
    ld = _job_posting_ld(doc)

    title = (ld.get("title") or "").strip()
    if not title:
        raise ParseError("missing_title", "JSON-LD không có title")

    exp = ld.get("experienceRequirements")
    months = _obj(exp).get("monthsOfExperience")
    experience_text = f"{months} months" if months else (exp.strip() if isinstance(exp, str) and exp.strip() else None)
    payload = {
        "title": mask_pii(title),
        "company_name": mask_pii(_obj(ld.get("hiringOrganization")).get("name")),
        "salary_text": _salary_text(ld),
        "locations": _locations(ld),
        "experience_text": experience_text,
        "employment_type": ld.get("employmentType"),
        "category": ld.get("industry"),
        "deadline": ld.get("validThrough"),
        "date_posted": ld.get("datePosted"),
        "skill_tags": _skills(ld),
        "description": mask_pii(html_to_text(ld.get("description"))),
        "requirements": mask_pii(_requirements(doc)),
        "benefits": mask_pii(html_to_text(ld.get("jobBenefits"))),
    }
    return job_message("itviec", sid, url, {k: v for k, v in payload.items() if v not in (None, [])}, lastmod, crawl_ts)
