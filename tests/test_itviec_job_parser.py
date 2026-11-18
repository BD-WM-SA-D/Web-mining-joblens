from pathlib import Path

import pytest

from crawler.common import schema_errors
from crawler.itviec.job_parser import ParseError, job_id, parse_job_page

FIXTURE = Path(__file__).parent / "fixtures" / "itviec" / "job_page.html"
URL = "https://itviec.com/viec-lam-it/senior-backend-engineer-abc-software-3554"


@pytest.fixture(scope="module")
def message():
    return parse_job_page(FIXTURE.read_text(encoding="utf-8"), URL, crawl_ts="2026-11-13T10:00:00Z")


def test_job_id():
    assert job_id(URL) == "3554"
    assert job_id("https://itviec.com/viec-lam-it/abc-123?utm=x") == "123"
    assert job_id("https://itviec.com/viec-lam-it/khong-co-id") is None


def test_url_khong_co_id_thi_bao_loi():
    with pytest.raises(ParseError) as e:
        parse_job_page("<html></html>", "https://itviec.com/viec-lam-it/khong-co-id")
    assert e.value.error_type == "bad_url"


def test_khong_co_jsonld_thi_bao_loi():
    with pytest.raises(ParseError) as e:
        parse_job_page("<html><body>trang khác</body></html>", URL)
    assert e.value.error_type == "missing_jsonld"


def test_hop_schema_va_dung_nguon(message):
    assert schema_errors(message, "job_posting.v1") == []
    assert message["source"] == "itviec"
    assert message["source_job_id"] == "3554"


def test_cac_truong_tu_jsonld(message):
    p = message["payload"]
    assert p["title"] == "Senior Backend Engineer"
    assert p["company_name"] == "ABC Software"
    assert p["locations"] == ["Quận 7"]
    assert p["skill_tags"] == ["Java", "Spring Boot", "Kafka", "SQL"]
    assert p["date_posted"] == "2026-10-26"
    assert p["deadline"] == "2026-11-30"
    assert p["employment_type"] == "FULL_TIME"
    assert p["experience_text"] == "36 months"


def test_luong_bi_an_thi_de_trong(message):
    """ITviec ẩn lương với khách chưa đăng nhập – không được bịa, không được lấy câu mời."""
    assert "salary_text" not in message["payload"]


def test_tach_duoc_phan_yeu_cau(message):
    req = message["payload"]["requirements"]
    assert req and "3+ năm kinh nghiệm Java" in req
    # phần mô tả không được lẫn vào yêu cầu
    assert "Phát triển hệ thống backend" not in req


def test_loc_pii(message):
    req = message["payload"]["requirements"]
    assert "0912345678" not in req and "<PHONE>" in req


def test_jsonld_khong_nhat_quan_khong_lam_vo_parser():
    """ITviec trả `experienceRequirements` khi là object, khi là chuỗi ("No requirements").

    Lần crawl 2026-11-13 vỡ ở đây: 20 tin lỗi → spider tự dừng sau 157/615 tin.
    """
    import json

    html = FIXTURE.read_text(encoding="utf-8")
    ld_start = html.index("{", html.index("application/ld+json"))
    ld_end = html.index("</script>", ld_start)
    ld = json.loads(html[ld_start:ld_end])

    for value, expected in [
        ("No requirements", "No requirements"),
        ({"@type": "OccupationalExperienceRequirements", "monthsOfExperience": 24}, "24 months"),
        (None, None),
    ]:
        ld["experienceRequirements"] = value
        page = html[:ld_start] + json.dumps(ld, ensure_ascii=False) + html[ld_end:]
        p = parse_job_page(page, URL)["payload"]
        assert p.get("experience_text") == expected

    # các trường khác cũng có thể là chuỗi thay vì object
    for field in ("hiringOrganization", "baseSalary", "jobLocation"):
        ld["experienceRequirements"] = "No requirements"
        ld[field] = "không phải object"
        page = html[:ld_start] + json.dumps(ld, ensure_ascii=False) + html[ld_end:]
        parse_job_page(page, URL)  # không được ném lỗi
