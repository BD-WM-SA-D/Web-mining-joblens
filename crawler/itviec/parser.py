"""Parser trang review công ty ITviec → message review.v1.

Cấu trúc ghi nhận ngày 2026-11-12 trên trang thật `/nha-tuyen-dung/<slug>/danh-gia`:

    div.content-of-review                     ← mỗi review một khối
      span.ifs-14.text-dark-grey              ← "Tháng Ba 2026" (tháng bằng chữ tiếng Việt)
      h3.text-it-black                        ← tiêu đề review
      p.ims-3.ime-1                           ← sao tổng (1–5)
      ul.detail-rating-tooltip > li           ← mỗi khía cạnh: p.w-50 (tên) + p.ims-2 (sao)
      div.recommend-icon-wrapper              ← "Khuyến khích" / "Không khuyến khích"
      h4 "Điều tôi thích:"  + p.normal-text   ← phần khen
      h4 "Đề nghị cải thiện:" + div.panel-paragraph ← phần góp ý

**Review bị che (quan trọng):** ngoài review công khai, trang còn các khối `div.details-review.blur`
chứa VĂN BẢN GIẢ giống hệt nhau ở mọi công ty ("The salary is really good, the manager always tries…"),
dùng để che review thật và mời đăng nhập. Parser phải loại chúng, nếu không tập dữ liệu sẽ toàn câu giả.
Dấu hiệu phân biệt: review thật dùng `<h4>Điều tôi thích:</h4>`, khối bị che dùng `<p>Điều tôi thích</p>`
bên trong `div.what-you-liked` và cha có class `blur`.
Đo ngày 2026-11-12 trên `ntt-data-vietnam` (43 review): **1 review thật / 9 khối bị che mỗi trang**.

Trang KHÔNG có id review → `source_review_id` = 16 ký tự đầu của content_hash (theo review.v1).
Chỉ lấy review công khai (hiện khi chưa đăng nhập); phần còn lại đòi đăng nhập – không đụng tới.
Không lấy tên, chức danh người review; văn bản đi qua mask_pii (ADR 0001 D1).
ITviec đổi giao diện thì sửa SELECTORS ở đây.
"""

from __future__ import annotations

import re
import unicodedata

from lxml import html as lxml_html

from crawler.common import content_hash, mask_pii, review_message, utc_now

PARSER_VERSION = "itviec-review-parser:0.2.0"

# Mỗi review (thật hay bị che) bắt đầu bằng div.py-4.border-bottom-dashed; HTML của trang có thẻ <p>
# lồng <p> nên cây DOM dựng ra bị lồng sai → cắt HTML theo mốc này rồi parse từng mảnh.
BLOCK_START = "<div class='py-4 border-bottom-dashed'>"

SELECTORS = {
    "month": './/span[contains(@class, "text-dark-grey")]',
    "title": './/h3[contains(@class, "text-it-black")]',
    "rating_overall": './/p[contains(@class, "ims-3")]',
    "aspect_row": './/ul[contains(@class, "detail-rating-tooltip")]/li',
    "aspect_name": './/p[contains(@class, "w-50")]',
    "aspect_value": './/p[contains(@class, "ims-2")]',
    "recommend": './/div[contains(@class, "recommend-icon-wrapper")]',
    # chỉ h4 = review thật; khối bị che dùng <p> nên không khớp.
    # Lấy cả div CHA rồi cắt bỏ tiêu đề: HTML có <p> lồng <p> nên nội dung bị đẩy ra khỏi following-sibling[1].
    # bản EN của trang (/companies/<slug>/review) dùng tiêu đề tiếng Anh, cùng một review
    "liked": './/h4[starts-with(normalize-space(.), "Điều tôi thích") or starts-with(normalize-space(.), "What I liked")]/..',
    "improvement": (
        './/h4[starts-with(normalize-space(.), "Đề nghị cải thiện")'
        ' or starts-with(normalize-space(.), "Suggestions for improvement")]/..'
    ),
    "blurred": './/div[contains(@class, "blur")]',
}

# Tên khía cạnh trên trang (đã bỏ dấu, chữ thường) → khóa trong review.v1 aspect_ratings
ASPECT_KEYS = {
    "luong thuong & phuc loi": "salary_benefits",
    "salary & benefits": "salary_benefits",
    "dao tao & hoc hoi": "training_learning",
    "training & learning": "training_learning",
    "su quan tam den nhan vien": "management_care",
    "management cares about me": "management_care",
    "van hoa cong ty": "culture_fun",
    "culture & fun": "culture_fun",
    "van phong lam viec": "office_workspace",
    "office & workspace": "office_workspace",
}

VN_MONTHS = {
    "mot": 1, "hai": 2, "ba": 3, "tu": 4, "nam": 5, "sau": 6,
    "bay": 7, "tam": 8, "chin": 9, "muoi": 10, "muoi mot": 11, "muoi hai": 12,
}  # fmt: skip

MONTH_VN_RE = re.compile(r"thang\s+([a-z ]+?)\s+(\d{4})")
MONTH_NUM_RE = re.compile(r"(0?[1-9]|1[0-2])[/-](\d{4})")
COMPANY_SLUG_RE = re.compile(r"/(?:nha-tuyen-dung|companies)/([^/?#]+)")
TITLE_SKIP = {"danh gia chung"}  # h3 của khối tổng quan, không phải tiêu đề review


class ParseError(Exception):
    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type


def fold(s: str) -> str:
    """Bỏ dấu + chữ thường + gộp khoảng trắng, để so tên khía cạnh và tên tháng."""
    no_mark = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))
    return " ".join(no_mark.replace("đ", "d").split())


NL = "\n"


def _node_text(node) -> str:
    """Văn bản của một node, giữ `<br>` thành dấu xuống dòng.

    ITviec dùng `<br>` làm ranh giới ý: 57,6% khối liked/improvement có `<br>`, và người viết gõ mỗi ý
    một dòng mà không có dấu câu. `itertext()` nối bằng dấu cách nên hai ý rời bị dán thành một câu
    ("...có chỗ ngủ trưa Bản thân tôi chưa bao giờ phải OT..."), làm hỏng cả tách câu lẫn gán nhãn.
    """
    parts: list[str] = []

    def walk(el) -> None:
        if el.text:
            parts.append(el.text)
        for ch in el:
            if isinstance(ch.tag, str) and ch.tag.lower() == "br":
                parts.append(NL)
            else:
                walk(ch)
            if ch.tail:
                parts.append(ch.tail)

    walk(node)
    lines = (" ".join(ln.split()) for ln in "".join(parts).split(NL))
    return NL.join(ln for ln in lines if ln)


def _text(nodes) -> str | None:
    return (_node_text(nodes[0]) if len(nodes) else None) or None


def _rating(raw: str | None) -> float | None:
    m = re.search(r"\d+(?:[.,]\d+)?", raw or "")
    if not m:
        return None
    v = float(m.group(0).replace(",", "."))
    return v if 1 <= v <= 5 else None


def parse_month(raw: str | None) -> str | None:
    """'Tháng Ba 2026' hoặc '03/2026' → '2026-03'."""
    f = fold(raw or "")
    m = MONTH_VN_RE.search(f)
    if m and (num := VN_MONTHS.get(m.group(1).strip())):
        return f"{m.group(2)}-{num:02d}"
    m = MONTH_NUM_RE.search(raw or "")
    return f"{m.group(2)}-{int(m.group(1)):02d}" if m else None


def company_slug(url: str) -> str:
    m = COMPANY_SLUG_RE.search(url)
    if not m:
        raise ParseError("bad_url", f"URL không có slug công ty: {url}")
    return m.group(1)


def _section_text(block, key: str, headings: tuple[str, ...]) -> str | None:
    """Văn bản một phần (thích / góp ý), đã bỏ dòng tiêu đề đứng đầu (VN hoặc EN)."""
    txt = _text(block.xpath(SELECTORS[key]))
    if not txt:
        return None
    for h in headings:
        txt = re.sub(rf"^{re.escape(h)}\s*:?\s*", "", txt).strip()
    return txt or None


def _block_ratings(block) -> dict:
    """Phần điểm số của một khối – LUÔN đọc được, kể cả khối bị che."""
    aspects: dict[str, float | None] = {}
    for row in block.xpath(SELECTORS["aspect_row"]):
        key = ASPECT_KEYS.get(fold(_text(row.xpath(SELECTORS["aspect_name"])) or ""))
        if key:
            aspects[key] = _rating(_text(row.xpath(SELECTORS["aspect_value"])))
    rec_txt = fold(_text(block.xpath(SELECTORS["recommend"])) or "")
    return {
        "review_month": parse_month(_text(block.xpath(SELECTORS["month"]))),
        "rating_overall": _rating(_text(block.xpath(SELECTORS["rating_overall"]))),
        "aspect_ratings": aspects,
        "recommend": None if not rec_txt else not rec_txt.startswith("khong"),
    }


def _block_to_payload(block, company_name: str) -> dict | None:
    """Một khối → payload review.v1, hoặc None nếu là khối bị che / không có phần văn bản."""
    liked = mask_pii(_section_text(block, "liked", ("Điều tôi thích", "What I liked")))
    improvement = mask_pii(_section_text(block, "improvement", ("Đề nghị cải thiện", "Suggestions for improvement")))
    if not liked and not improvement:
        return None

    title = _text(block.xpath(SELECTORS["title"]))
    if title and fold(title) in TITLE_SKIP:
        title = None

    return {
        **_block_ratings(block),
        "company_name": company_name,
        "title": mask_pii(title),
        "liked_text": liked,
        "improvement_text": improvement,
    }


def split_blocks(page_html: str) -> list[str]:
    """Cắt HTML thành từng khối review theo BLOCK_START (chịu được HTML lồng sai)."""
    marks = [m.start() for m in re.finditer(re.escape(BLOCK_START), page_html)]
    if not marks:
        return []
    ends = marks[1:] + [len(page_html)]
    return [page_html[a:b] for a, b in zip(marks, ends, strict=True)]


def parse_ratings(page_html: str, url: str, crawl_ts: str | None = None) -> list[dict]:
    """Điểm số của MỌI review trên trang, kể cả review bị che (chỉ che văn bản, không che điểm).

    Dùng cho: nhãn yếu WM3, đo thiên lệch của mẫu công khai, kiểm chứng mô hình bằng tương quan sao.
    Không theo schema review.v1 (schema đó bắt buộc có nội dung) – đây là file cục bộ của môn WM.
    `has_text=True` nghĩa là review này cũng lấy được văn bản qua `parse_review_page`.
    """
    doc = lxml_html.fromstring(page_html)
    slug = company_slug(url)
    company_name = _text(doc.xpath("//h1")[:1])
    ts = crawl_ts or utc_now()
    out = []
    for i, chunk in enumerate(split_blocks(page_html)):
        node = lxml_html.fromstring(f"<div>{chunk}</div>")
        r = _block_ratings(node)
        if r["rating_overall"] is None and not r["aspect_ratings"]:
            continue  # khối không phải review
        has_text = bool(node.xpath(SELECTORS["liked"])) or bool(node.xpath(SELECTORS["improvement"]))
        out.append(
            {
                "source": "itviec",
                "company_id": slug,
                "company_name": company_name,
                "url": url,
                "crawl_ts": ts,
                "position": i,
                "has_text": has_text,
                **r,
            }
        )
    return out


def parse_review_page(page_html: str, url: str, crawl_ts: str | None = None) -> list[dict]:
    """Một trang review công ty → danh sách message review.v1 (CHỈ review công khai thật)."""
    doc = lxml_html.fromstring(page_html)
    slug = company_slug(url)
    company_name = _text(doc.xpath("//h1")[:1])
    if not company_name:
        raise ParseError("missing_company_name", "Không thấy <h1> tên công ty")

    blocks = split_blocks(page_html)
    out = []
    for chunk in blocks:
        node = lxml_html.fromstring(f"<div>{chunk}</div>")
        payload = _block_to_payload(node, company_name)
        if payload is None:
            continue
        out.append(review_message("itviec", content_hash(payload)[:16], slug, url, payload, crawl_ts))
    if not out:
        raise ParseError(
            "no_public_reviews",
            f"Không có review công khai ({len(blocks)} khối, đều bị che hoặc rỗng)",
        )
    return out
