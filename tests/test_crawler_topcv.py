"""Kiểm tra crawler TopCV trên HTML tự soạn – không gửi request nào."""

from pathlib import Path

import pytest
from scrapy.http import HtmlResponse, Request

from crawler.common import html_to_text, mask_pii, schema_errors
from crawler.topcv.parser import ParseError, parse_job_page
from crawler.topcv.sitemap import is_allowed, job_id, looks_it, parse_sitemap
from crawler.topcv.spider import TopcvSpider

FIX = Path(__file__).parent / "fixtures" / "topcv"
URL_IT = "https://www.topcv.vn/viec-lam/lap-trinh-vien-python-data/900001.html"
URL_SALES = "https://www.topcv.vn/viec-lam/nhan-vien-kinh-doanh/900002.html"

SITEMAP_INDEX = b"""<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://www.topcv.vn/sitemap/jobs_0.xml</loc></sitemap>
<sitemap><loc>https://www.topcv.vn/sitemap/jobs_1.xml</loc></sitemap></sitemapindex>"""
URLSET = b"""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://www.topcv.vn/viec-lam/lap-trinh-vien-python-data/900001.html</loc><lastmod>2026-10-01T00:00:00+00:00</lastmod></url>
<url><loc>https://www.topcv.vn/viec-lam/nhan-vien-kinh-doanh/900002.html</loc><lastmod>2026-10-02T00:00:00+00:00</lastmod></url>
<url><loc>https://www.topcv.vn/viec-lam/tester-phan-mem/900003.html</loc><lastmod>2026-09-01T00:00:00+00:00</lastmod></url>
<url><loc>https://www.topcv.vn/xem-cv/abc</loc></url></urlset>"""


def read(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_sitemap_parsing():
    kind, children = parse_sitemap(SITEMAP_INDEX)
    assert kind == "index" and [c.loc[-10:] for c in children] == ["jobs_0.xml", "jobs_1.xml"]
    kind, urls = parse_sitemap(URLSET)
    assert kind == "urlset" and len(urls) == 4 and urls[0].lastmod.startswith("2026-10-01")


def test_url_rules():
    assert job_id(URL_IT) == "900001"
    assert job_id("https://www.topcv.vn/xem-cv/abc") is None
    assert not is_allowed("https://www.topcv.vn/xem-cv/abc") and not is_allowed("https://www.topcv.vn/cv-ung-vien/1")
    assert looks_it(URL_IT) and not looks_it(URL_SALES)
    base = "https://www.topcv.vn/viec-lam/{}/1.html"
    for slug in [
        "nhan-vien-ke-toan-tai-chinh",
        "giao-vien-tieng-trung",
        "bep-truong-he-thong-khach-san",
        "nhan-vien-qc-nha-may",
        "chuyen-vien-ads-mang-giao-duc",
    ]:
        assert not looks_it(base.format(slug)), slug
    for slug in ["ky-su-ai", "nhan-vien-kiem-thu-phan-mem", "senior-java-developer", "chuyen-vien-an-ninh-mang"]:
        assert looks_it(base.format(slug)), slug


def test_parse_it_job():
    r = parse_job_page(
        read("job_it.html"), URL_IT, lastmod="2026-10-01T00:00:00+00:00", crawl_ts="2026-10-12T00:00:00Z"
    )
    p = r.message["payload"]
    assert r.is_it and r.category_path[0] == "Công nghệ Thông tin"
    assert r.message["source_job_id"] == "900001"
    assert p["title"] == "Lập trình viên Python (Data)" and p["company_id"] == "900001"
    assert p["locations"] == ["Hà Nội", "Hồ Chí Minh"]
    assert p["salary_text"] == "15000000 - 25000000 VND"
    assert p["skill_tags"] == ["Python", "SQL", "Apache Spark"]  # không lẫn "1 năm kinh nghiệm", "Nam", "Data Engineer"
    assert p["deadline"] == "2026-10-31" and p["date_posted"] == "2026-09-20"
    assert p["experience_text"] == "12 tháng"
    assert p["requirements"].startswith("- Thành thạo Python, SQL.")
    assert "Lương tháng 13" in p["benefits"]
    assert schema_errors(r.message) == []


def test_pii_is_masked():
    p = parse_job_page(read("job_it.html"), URL_IT).message["payload"]
    assert "example.invalid" not in p["description"] and "0912" not in p["description"]
    assert "<EMAIL>" in p["description"] and "<PHONE>" in p["description"]


def test_parse_non_it_and_negotiable_salary():
    r = parse_job_page(read("job_sales.html"), URL_SALES)
    p = r.message["payload"]
    assert not r.is_it
    assert p["salary_text"] == "Thoả thuận" and p["skill_tags"] == [] and p["description"] == "Tìm kiếm khách hàng mới."
    assert p["requirements"] is None and p["company_id"] is None
    assert schema_errors(r.message) == []


def test_content_hash_changes_with_content():
    a = parse_job_page(read("job_it.html"), URL_IT).message["content_hash"]
    b = parse_job_page(read("job_it.html").replace("Bảo hiểm đầy đủ", "Bảo hiểm cơ bản"), URL_IT).message[
        "content_hash"
    ]
    assert a != b


def test_parse_errors():
    with pytest.raises(ParseError) as e:
        parse_job_page(read("job_broken.html"), URL_IT)
    assert e.value.error_type == "missing_jsonld"
    with pytest.raises(ParseError):
        parse_job_page(read("job_it.html"), "https://www.topcv.vn/cong-ty/abc.html")


def test_split_skills_and_primary_category():
    from crawler.topcv.parser import split_skills

    assert split_skills("Luật bảo vệ dữ liệu (ví dụ: GDPR, CCPA), Python ,Python") == [
        "Luật bảo vệ dữ liệu (ví dụ: GDPR, CCPA)",
        "Python",
    ]
    sales_it = read("job_it.html").replace(
        '<a href="#">Công nghệ Thông tin</a>', '<a href="#">Kinh doanh/Bán hàng</a><a href="#">Công nghệ Thông tin</a>'
    )
    assert not parse_job_page(sales_it, URL_IT).is_it  # "Sales IT phần mềm": danh mục chính là kinh doanh


def test_helpers():
    assert html_to_text("<ul><li>A</li><li>B</li></ul>") == "- A\n- B"
    assert html_to_text("  ") is None
    assert mask_pii("gọi 0987.654.321") == "gọi <PHONE>"


def _resp(url, body, **cb):
    req = Request(url, cb_kwargs=cb)
    return HtmlResponse(
        url=url, body=body.encode("utf-8") if isinstance(body, str) else body, encoding="utf-8", request=req
    )


def test_spider_flow_offline(tmp_path, monkeypatch):
    spider = TopcvSpider(max_jobs=5, out_dir=str(tmp_path / "day"), state_dir=str(tmp_path))
    monkeypatch.setattr(spider, "html_dir", tmp_path / "html")
    reqs = list(spider.parse_index(_resp("https://www.topcv.vn/sitemap/jobs.xml", SITEMAP_INDEX)))
    assert len(reqs) == 1  # max_sitemaps=1
    reqs = list(spider.parse_urlset(_resp("https://www.topcv.vn/sitemap/jobs_0.xml", URLSET)))
    assert [r.url for r in reqs] == [URL_IT, "https://www.topcv.vn/viec-lam/tester-phan-mem/900003.html"]

    spider.since = "2026-09-15"
    assert [r.url for r in spider.parse_urlset(_resp("https://www.topcv.vn/sitemap/jobs_0.xml", URLSET))] == [URL_IT]

    items = list(spider.parse_job(_resp(URL_IT, read("job_it.html")), lastmod="2026-10-01T00:00:00+00:00"))
    assert len(items) == 1 and items[0]["source"] == "topcv"
    assert list(spider.parse_job(_resp(URL_SALES, read("job_sales.html")))) == []
    assert list(spider.parse_job(_resp(URL_IT, read("job_broken.html")))) == []
    spider.closed("test")
    assert spider.stats_local == {"jobs_ok": 1, "skipped_not_it": 1, "parse_errors": 1}
    assert (tmp_path / "day" / "jobs.jsonl").read_text(encoding="utf-8").count("\n") == 1
    assert "missing_jsonld" in (tmp_path / "day" / "parse_errors.jsonl").read_text(encoding="utf-8")

    # Chạy lại (crawl tiếp): tin đã tải không được xếp hàng lại
    again = TopcvSpider(max_jobs=5, out_dir=str(tmp_path / "day2"), state_dir=str(tmp_path))
    assert {"900001", "900002"} <= again.seen
    urls = [r.url for r in again.parse_urlset(_resp("https://www.topcv.vn/sitemap/jobs_0.xml", URLSET))]
    assert urls == ["https://www.topcv.vn/viec-lam/tester-phan-mem/900003.html"]
    assert (tmp_path / "html" / "900001.html.gz").exists()
