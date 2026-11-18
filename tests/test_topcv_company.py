from pathlib import Path

import pandas as pd

from crawler.topcv.company import company_url, company_url_in, job_links, page_url
from crawler.topcv.run_companies import read_companies
from crawler.topcv.shared_companies import shared

FIXTURE = Path(__file__).parent / "fixtures" / "topcv" / "company_page.html"
HTML = FIXTURE.read_text(encoding="utf-8")


def test_company_url_in_lay_link_cua_chinh_cong_ty():
    """Trang công ty cũng trỏ tới công ty khác ở mục 'việc làm liên quan' – phải lấy link lặp nhiều nhất."""
    assert company_url_in(HTML) == company_url("cong-ty-tnhh-vi-du", "123456")


def test_company_url_in_khong_co_link_thi_None():
    assert company_url_in("<html><body>trang khác</body></html>") is None


def test_job_links_bo_trung_giu_thu_tu():
    links = job_links(HTML)
    assert links[:3] == [
        "https://www.topcv.vn/viec-lam/senior-backend-engineer-java/1000001.html",
        "https://www.topcv.vn/viec-lam/chuyen-vien-phan-tich-nghiep-vu/1000002.html",
        "https://www.topcv.vn/viec-lam/ke-toan-tong-hop/1000003.html",
    ]
    assert len(links) == len(set(links))


def test_job_links_khong_cham_duong_dan_cv():
    assert all("/xem-cv/" not in u for u in job_links(HTML))


def test_job_links_khong_lay_trang_danh_muc():
    assert all("/tim-viec-lam" not in u for u in job_links(HTML))


def test_page_url():
    base = "https://www.topcv.vn/cong-ty/x/1.html"
    assert page_url(base, 1) == base
    assert page_url(base, 2) == base + "?page=2"


def test_read_companies_bo_dong_trong(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text("https://a\n\n  https://b  \n", encoding="utf-8")
    assert read_companies(f) == ["https://a", "https://b"]


def test_shared_khop_ten_cong_ty_khac_cach_viet():
    """TopCV ghi tên pháp lý, ITviec ghi tên thương hiệu → phải khớp được sau chuẩn hóa."""
    topcv = pd.DataFrame(
        [
            {"source_job_id": "1", "company_name": "Công ty TNHH LG CNS Việt Nam"},
            {"source_job_id": "2", "company_name": "Công ty TNHH LG CNS Việt Nam"},
            {"source_job_id": "3", "company_name": "Công ty Cổ phần Chỉ Có Ở TopCV"},
        ]
    )
    itviec = pd.DataFrame([{"company_name": "LG CNS Việt Nam"}, {"company_name": "LG CNS Việt Nam"}])
    df = shared(topcv, itviec, {"1": company_url("cong-ty-tnhh-lg-cns-viet-nam", "139535")})
    assert len(df) == 1
    row = df.iloc[0]
    assert row["company"] == "lg cns việt nam"
    assert row["n_topcv"] == 2 and row["n_itviec"] == 2
    assert row["company_url"].endswith("/139535.html")


def test_shared_cong_ty_chua_biet_trang_thi_de_trong():
    topcv = pd.DataFrame([{"source_job_id": "9", "company_name": "ABC Software"}])
    itviec = pd.DataFrame([{"company_name": "ABC Software"}])
    df = shared(topcv, itviec, {})
    assert df.iloc[0]["company_url"] is None
