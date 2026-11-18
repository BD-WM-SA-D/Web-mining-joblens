from pathlib import Path

import pytest
from lxml import html as lx

from crawler.common import schema_errors
from crawler.itviec.parser import (
    ParseError,
    _node_text,
    company_slug,
    parse_month,
    parse_review_page,
    split_blocks,
)

FIXTURE = Path(__file__).parent / "fixtures" / "itviec" / "review_page.html"
URL = "https://itviec.com/nha-tuyen-dung/abc-software/danh-gia"


@pytest.fixture(scope="module")
def html():
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def reviews(html):
    return parse_review_page(html, URL, crawl_ts="2026-11-12T10:00:00Z")


def test_company_slug_ca_hai_dang_url():
    assert company_slug(URL) == "abc-software"
    assert company_slug("https://itviec.com/companies/abc-corp/review") == "abc-corp"
    with pytest.raises(ParseError):
        company_slug("https://itviec.com/it-jobs/abc")


def test_parse_month_tieng_viet_va_so():
    assert parse_month("Tháng Mười 2026") == "2026-10"
    assert parse_month("Tháng Ba 2026") == "2026-03"
    assert parse_month("Tháng Mười Hai 2025") == "2025-12"
    assert parse_month("01/2025") == "2025-01"
    assert parse_month("không có tháng") is None
    assert parse_month(None) is None


def test_split_blocks_dem_dung_so_khoi(html):
    assert len(split_blocks(html)) == 3


def test_chi_lay_review_cong_khai_that(reviews):
    """Khối bị che (details-review blur) và khối không có văn bản phải bị loại."""
    assert len(reviews) == 1
    for msg in reviews:
        assert schema_errors(msg, "review.v1") == []


def test_khong_lay_van_ban_gia_cua_khoi_bi_che(reviews):
    text = " ".join(str(reviews[0]["payload"].get(k) or "") for k in ("liked_text", "improvement_text"))
    assert "The salary is really good" not in text
    assert "Boss is like a friend" not in text


def test_truong_cua_review_that(reviews):
    m = reviews[0]
    assert m["source"] == "itviec" and m["company_id"] == "abc-software"
    assert len(m["source_review_id"]) == 16  # trang không có id → hash nội dung
    p = m["payload"]
    assert p["company_name"] == "ABC Software"
    assert p["review_month"] == "2026-10"
    assert p["rating_overall"] == 4.0
    assert p["recommend"] is True
    assert p["title"] == "Môi trường tốt cho junior"
    assert p["aspect_ratings"] == {
        "salary_benefits": 3.0,
        "training_learning": 5.0,
        "management_care": 4.0,
        "culture_fun": 4.0,
        "office_workspace": 4.0,
    }
    assert p["liked_text"].startswith("Mentor nhiệt tình")
    assert "Điều tôi thích" not in p["liked_text"]  # đã cắt tiêu đề
    assert p["improvement_text"].startswith("Nên xem lại")


def test_loc_pii(reviews):
    p = reviews[0]["payload"]
    assert "0912345678" not in p["liked_text"] and "<PHONE>" in p["liked_text"]
    assert "hr@abc.vn" not in p["improvement_text"] and "<EMAIL>" in p["improvement_text"]


def test_trang_khong_co_review_cong_khai_thi_bao_loi():
    with pytest.raises(ParseError) as e:
        parse_review_page("<html><h1>X</h1><body>Đăng nhập để xem</body></html>", URL)
    assert e.value.error_type == "no_public_reviews"


def test_review_url_phan_trang():
    from crawler.itviec.spider import review_url

    assert review_url("abc") == "https://itviec.com/nha-tuyen-dung/abc/danh-gia"
    assert review_url("abc", 1) == "https://itviec.com/nha-tuyen-dung/abc/danh-gia"
    assert review_url("abc", 3) == "https://itviec.com/nha-tuyen-dung/abc/danh-gia?page=3"


def test_spider_dung_khi_bi_chan():
    from scrapy.exceptions import CloseSpider

    from crawler.topcv.spider import check_not_blocked

    class FakeResponse:
        def __init__(self, status):
            self.status = status

    for code in (429, 403):
        with pytest.raises(CloseSpider):
            check_not_blocked(FakeResponse(code))
    check_not_blocked(FakeResponse(200))  # không ném


def test_sitemap_lay_slug_va_bo_trung():
    from crawler.itviec.sitemap import slugs_from_xml

    xml = """<urlset>
      <url><loc>https://itviec.com/nha-tuyen-dung/abc-corp/danh-gia</loc></url>
      <url><loc>https://itviec.com/nha-tuyen-dung/abc-corp/danh-gia</loc></url>
      <url><loc>https://itviec.com/nha-tuyen-dung/x-y-z/danh-gia</loc></url>
      <url><loc>https://itviec.com/it-jobs/khong-phai-review</loc></url>
    </urlset>"""
    assert slugs_from_xml(xml) == ["abc-corp", "x-y-z"]


def test_parse_ratings_lay_ca_review_bi_che(html):
    from crawler.itviec.parser import parse_ratings

    rows = parse_ratings(html, URL, crawl_ts="2026-11-12T10:00:00Z")
    # fixture: 1 review thật + 1 khối bị che + 1 khối chỉ có sao → cả 3 đều có điểm
    assert len(rows) == 3
    assert [r["has_text"] for r in rows] == [True, False, False]
    assert all(r["company_id"] == "abc-software" for r in rows)
    assert rows[0]["rating_overall"] == 4.0 and rows[0]["review_month"] == "2026-10"
    assert rows[1]["rating_overall"] == 2.0 and rows[1]["recommend"] is False
    assert rows[1]["aspect_ratings"] == {"salary_benefits": 2.0}
    assert rows[2]["rating_overall"] == 5.0 and rows[2]["review_month"] == "2025-01"
    # không chứa văn bản nào
    assert all("liked_text" not in r for r in rows)


def test_hiring_companies_tach_slug_tu_url_viec_lam():
    from crawler.itviec.sitemap import hiring_companies

    jobs = """<urlset>
      <url><loc>https://itviec.com/viec-lam-it/senior-backend-java-fpt-is-4708</loc></url>
      <url><loc>https://itviec.com/viec-lam-it/ai-engineer-fpt-is-0856</loc></url>
      <url><loc>https://itviec.com/viec-lam-it/qc-engineer-mb-bank-2314</loc></url>
      <url><loc>https://itviec.com/viec-lam-it/khong-khop-cong-ty-nao-9999</loc></url>
    </urlset>"""
    # slug dài phải được khớp trước, để "fpt-is" không ăn vào "fpt-is-hanoi"
    got = hiring_companies(jobs, ["fpt-is", "fpt-is-hanoi", "mb-bank"])
    assert got == {"fpt-is": 2, "mb-bank": 1}


def test_node_text_giu_br_thanh_xuong_dong():
    """ITviec gõ mỗi ý một dòng, phân tách bằng <br>. Nối bằng dấu cách sẽ dán hai ý thành một câu."""
    node = lx.fromstring("<div><p>Văn phòng đẹp<br/>Không phải OT</p></div>")
    assert _node_text(node) == "Văn phòng đẹp\nKhông phải OT"


def test_node_text_gop_khoang_trang_trong_tung_dong():
    node = lx.fromstring("<div><p>  Lương   ổn  <br/>  <br/>  OT   ít  </p></div>")
    assert _node_text(node) == "Lương ổn\nOT ít"
