import pandas as pd

from crawler.dedup import baseline_key, baseline_pairs, candidates, minhash_pairs, norm, shingles

DESC = (
    "Tham gia phát triển hệ thống backend bằng Java Spring Boot, thiết kế API, "
    "tối ưu truy vấn cơ sở dữ liệu PostgreSQL và triển khai trên AWS cùng đội ngũ."
)


def df_from(rows):
    return pd.DataFrame(
        [
            {
                "job_uid": r[0],
                "source": r[1],
                "title": r[2],
                "company_name": r[3],
                "description": r[4],
                "requirements_text": r[5] if len(r) > 5 else "",
            }
            for r in rows
        ]
    )


def test_norm_va_baseline_key():
    assert norm("  Lập Trình Viên, Java!! ") == "lập trình viên java"
    # cùng khóa dù khác hoa thường, dấu câu và đuôi quảng cáo
    k1 = baseline_key("Java Developer (Tuyển gấp)", "FPT Software")
    k2 = baseline_key("java developer", "fpt   software")
    assert k1 == k2
    assert baseline_key("Java Developer - lương upto 2000$", "FPT") == baseline_key("Java Developer", "FPT")


def test_baseline_pairs_cung_tieu_de_cong_ty():
    df = df_from(
        [
            ("a1", "topcv", "Java Developer", "FPT", DESC),
            ("a2", "itviec", "Java Developer (Tuyển gấp)", "FPT", DESC),
            ("b1", "topcv", "Tester", "FPT", "Kiểm thử phần mềm."),
        ]
    )
    assert baseline_pairs(df) == {("a1", "a2")}


def test_minhash_bat_tin_giong_noi_dung_khac_tieu_de():
    # tiêu đề khác hẳn nhưng nội dung gần giống → baseline trượt, minhash phải bắt
    df = df_from(
        [
            ("a1", "topcv", "Java Developer", "FPT", DESC),
            ("a2", "itviec", "Kỹ sư phần mềm Backend", "FPT", DESC + " Ưu tiên biết Docker."),
            ("c1", "topcv", "Designer", "VNG", "Thiết kế giao diện bằng Figma, vẽ minh họa, dựng video."),
        ]
    )
    mh = minhash_pairs(df, threshold=0.5)
    assert ("a1", "a2") in mh
    assert all("c1" not in pair for pair in mh)


def test_candidates_gop_hai_tang_va_danh_dau_khac_trang():
    df = df_from(
        [
            ("a1", "topcv", "Java Developer", "FPT", DESC),
            ("a2", "itviec", "Java Developer", "FPT", DESC),
        ]
    )
    cand = candidates(df, threshold=0.5)
    assert len(cand) == 1
    row = cand.iloc[0]
    assert bool(row["by_baseline"]) and row["jaccard_est"] > 0.5 and bool(row["cross_source"])


def test_shingles_cau_ngan():
    assert shingles("Java") == {"java"}
    assert shingles("") == set()


def test_sample_theo_tang_va_an_tang():
    """Rút cặp: chia đều 4 tầng, ưu tiên cặp khác nguồn, trộn thứ tự."""
    import random

    from annotation.sample_dedup_pairs import build_strata, pick

    df = df_from(
        [
            ("a1", "topcv", "Java Developer", "FPT", DESC),
            ("a2", "itviec", "Java Developer", "FPT", DESC),  # baseline + minhash
            ("a3", "topcv", "Tester", "FPT", "Kiểm thử phần mềm thủ công cho các dự án web."),
            ("c1", "topcv", "Designer", "VNG", "Thiết kế giao diện bằng Figma, vẽ minh họa."),
            ("c2", "itviec", "Product Manager", "VNG", "Quản lý lộ trình sản phẩm, làm việc với đội kỹ thuật."),
        ]
    )
    src = dict(zip(df["job_uid"], df["source"], strict=True))
    strata = build_strata(df)
    assert ("a1", "a2") in strata["baseline"]
    # cặp cùng công ty mà thuật toán không đề xuất → tầng same_company (dùng đo recall)
    assert ("a1", "a3") in strata["same_company"] or ("a3", "a1") in strata["same_company"]
    assert ("c1", "c2") in strata["same_company"]

    pairs = pick(strata, 4, random.Random(0), src)
    assert len(pairs) <= 4
    assert all(p["stratum"] in ("baseline", "minhash_high", "minhash_low", "same_company") for p in pairs)
    # không có cặp tự ghép với chính nó, không trùng cặp
    assert all(p["a"] != p["b"] for p in pairs)
    assert len({(p["a"], p["b"]) for p in pairs}) == len(pairs)


def test_task_gan_nhan_khong_lo_tang_lay_mau():
    """Người gán không được biết cặp đến từ tầng nào – `stratum` chỉ nằm trong manifest."""
    import json

    from annotation.sample_dedup_pairs import to_label_studio

    df = pd.DataFrame(
        [
            {
                "job_uid": "a" * 40,
                "source": "topcv",
                "title": "Backend Java",
                "company_name": "ACME",
                "description": "mô tả A",
            },
            {
                "job_uid": "b" * 40,
                "source": "itviec",
                "title": "Java Backend",
                "company_name": "ACME",
                "description": "mô tả B",
            },
        ]
    )
    tasks = to_label_studio([{"stratum": "minhash_high", "a": "a" * 40, "b": "b" * 40}], df)
    assert "stratum" not in tasks[0]["data"]
    assert "minhash_high" not in json.dumps(tasks, ensure_ascii=False)
    assert tasks[0]["data"]["index"] == 0  # khớp lại với manifest bằng index


def test_rut_cap_gioi_han_lap_tin_va_cong_ty():
    """Một công ty nhiều tin không được chiếm hết mẫu, một tin không lặp quá MAX_PER_JOB cặp."""
    import collections
    import random

    from annotation.sample_dedup_pairs import pick

    jobs = [f"m{i:02d}" for i in range(20)] + [f"o{i:02d}" for i in range(20)]
    src = {j: "topcv" for j in jobs}
    company = {j: ("mb" if j.startswith("m") else f"c{j}") for j in jobs}
    big = [(a, b) for i, a in enumerate(jobs[:20]) for b in jobs[i + 1 : 20]]  # 190 cặp cùng công ty
    small = [(jobs[20 + i], jobs[21 + i]) for i in range(0, 18, 2)]
    pairs = pick({"same_company": big + small}, 60, random.Random(0), src, company, max_per_job=3, max_per_company=15)
    per_job = collections.Counter(j for p in pairs for j in (p["a"], p["b"]))
    assert max(per_job.values()) <= 3
    assert sum(1 for p in pairs if company[p["a"]] == "mb") <= 15


def test_rut_lai_giu_cap_da_gan():
    import random

    from annotation.sample_dedup_pairs import pick

    src = {j: "topcv" for j in "abcdef"}
    strata = {"same_company": [("a", "b"), ("c", "d"), ("e", "f")], "minhash_low": [("a", "c")]}
    keep = [{"stratum": "minhash_low", "a": "a", "b": "c"}]
    pairs = pick(strata, 3, random.Random(1), src, keep=keep)
    assert {"stratum": "minhash_low", "a": "a", "b": "c"} in pairs
    assert len({(p["a"], p["b"]) for p in pairs}) == len(pairs)


def test_khong_gioi_han_tang_co_cap_trung():
    """Cặp baseline / minhash_high là nơi có tin trùng – không được bị giới hạn lặp cắt mất."""
    import random

    from annotation.sample_dedup_pairs import pick

    src = {j: "topcv" for j in "abcdef"}
    company = dict.fromkeys("abcdef", "mb")
    high = [("a", "b"), ("a", "c"), ("a", "d"), ("a", "e")]  # "a" lặp 4 lần
    pairs = pick({"minhash_high": high}, 4, random.Random(0), src, company, max_per_job=1, max_per_company=1)
    assert len(pairs) == 4


def test_tieu_de_mem_bo_hinh_thuc_va_dia_diem_giu_cap_bac():
    from crawler.dedup import soft_title_key

    assert soft_title_key("Data Science Intern On-site", "FINPROS") == soft_title_key("Data Science Intern", "FINPROS")
    assert soft_title_key("Java Developer (Remote, Vietnam)", "A") == soft_title_key("Java Developer", "A")
    assert soft_title_key("Tester tại Hà Nội", "A") == soft_title_key("Tester", "A")
    assert soft_title_key("Junior Java Developer", "A") != soft_title_key("Senior Java Developer", "A")
    # không cắt nhầm giữa từ: "hn" chỉ khớp nguyên từ
    assert "john" in soft_title_key("John Engineer", "A")


def test_cat_khung_cong_ty_tach_hai_vi_tri_chung_mo_ta():
    from crawler.dedup import shingle_sets

    intro = "ANDPAD là công ty SaaS hàng đầu Nhật Bản với phúc lợi bảo hiểm du lịch hằng năm và lương tháng 13. "
    rows = [
        (
            "j1",
            "itviec",
            "Android Engineer",
            "ANDPAD",
            intro + "Phát triển ứng dụng Android bằng Kotlin và Jetpack Compose.",
        ),
        (
            "j2",
            "itviec",
            "iOS Engineer",
            "ANDPAD",
            intro + "Phát triển ứng dụng iOS bằng Swift và SwiftUI cho khách hàng.",
        ),
        ("j3", "itviec", "QA Engineer", "ANDPAD", intro + "Kiểm thử tự động bằng Playwright cho sản phẩm web."),
    ]
    df = df_from(rows)
    full, cut = shingle_sets(df), shingle_sets(df, strip=True)

    def jac(s, a, b):
        return len(s[a] & s[b]) / len(s[a] | s[b])

    assert jac(full, "j1", "j2") > 0.4
    assert jac(cut, "j1", "j2") < 0.2
    assert all(cut[u] for u in cut)  # không tin nào bị cắt rỗng


def test_cat_khung_bo_qua_cong_ty_it_tin():
    from crawler.dedup import shingle_sets

    df = df_from([("a", "topcv", "Java", "X", DESC), ("b", "topcv", "Java", "X", DESC)])
    assert shingle_sets(df, strip=True) == shingle_sets(df)


def test_lo_kappa_lay_moi_cap_trung_va_kho():
    from annotation.kappa_dedup import select

    rows = [{"index": i, "dup": i < 3, "hard": i == 5} for i in range(40)]
    strata = {i: ("same_company" if i % 2 else "minhash_low") for i in range(40)}
    out = select(rows, strata, 10, 0)
    idx = {r["index"] for r in out}
    assert {0, 1, 2, 5} <= idx
    assert len(out) == 10 and len(idx) == 10
