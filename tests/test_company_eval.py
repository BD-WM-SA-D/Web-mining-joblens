"""Kiểm phép đo WM3 theo điểm sao (absa/company_eval.py) và thống kê nhu cầu kỹ năng."""

from __future__ import annotations

import math

from absa.company_eval import auc_low_star, blurred_company_stars, cells, demeaned, paired, spearman
from experiments.skill_demand import cat_level2, log_odds_dirichlet, wilson


def _row(rid, cid, text="Lương ổn", section="liked", stars=None):
    return {
        "source_review_id": rid,
        "company_id": cid,
        "text": text,
        "section": section,
        "lang": "vi",
        "aspect_ratings": stars or {"salary_benefits": 4.0},
    }


def test_blurred_stars_bo_review_co_van_ban():
    """Đích của mức công ty chỉ được tính trên review BỊ CHE, nếu không là tự chấm chính mình."""
    ratings = [
        {"company_id": "a", "has_text": True, "aspect_ratings": {"salary_benefits": 5.0}},
        {"company_id": "a", "has_text": False, "aspect_ratings": {"salary_benefits": 3.0}},
        {"company_id": "a", "has_text": False, "aspect_ratings": {"salary_benefits": 1.0}},
    ]
    out = blurred_company_stars(ratings)
    assert out[("a", "salary_benefits")] == (2.0, 2)  # (3+1)/2, không có 5.0 của review có văn bản


def test_cells_gop_theo_don_vi_va_bo_khia_canh_khong_co_sao():
    rows = [
        _row("r1", "c1", stars={"salary_benefits": 4.0}),
        _row("r1", "c1", stars={"salary_benefits": 4.0}),
    ]
    pred = [{"salary_benefits": "positive"}, {"salary_benefits": "negative", "work_life_balance": "negative"}]
    cs = cells(rows, pred, {}, "review")
    assert len(cs) == 1  # một ô (review, khía cạnh); work_life_balance không có sao nên bị loại
    assert cs[0]["pred"] == 0.0 and cs[0]["n_sent"] == 2  # trung bình (+1, -1)
    assert cs[0]["star"] == 4.0


def test_cells_muc_cong_ty_dung_sao_bi_che():
    rows = [_row("r1", "c1")]
    stars = {("c1", "salary_benefits"): (2.5, 4)}
    cs = cells(rows, [{"salary_benefits": "positive"}], stars, "company")
    assert cs[0]["star"] == 2.5 and cs[0]["n_target"] == 4
    assert cells(rows, [{"salary_benefits": "positive"}], {}, "company") == []  # không có đích thì bỏ ô


def test_spearman_hang_so_tra_nan():
    assert math.isnan(spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]))
    assert spearman([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0


def test_demeaned_tru_trung_binh_theo_khia_canh():
    cs = [
        {"aspect": "a", "pred": 1.0, "star": 5.0},
        {"aspect": "a", "pred": -1.0, "star": 3.0},
        {"aspect": "b", "pred": 0.0, "star": 1.0},
    ]
    xs, ys = demeaned(cs)
    assert xs == [1.0, -1.0, 0.0]  # TB nhóm a = 0
    assert ys == [1.0, -1.0, 0.0]  # TB nhóm a = 4, nhóm b = 1


def test_auc_mot_lop_tra_nan():
    cs = [{"pred": 1.0, "star": 5.0}, {"pred": -1.0, "star": 4.0}]
    auc, n_low = auc_low_star(cs)
    assert math.isnan(auc) and n_low == 0


def test_paired_ghep_theo_o_va_dau_dung():
    """Hệ B đảo dấu hoàn toàn thì Δρ phải dương rõ rệt."""
    cs_a = [{"unit": f"u{i}", "aspect": "a", "pred": float(i % 3 - 1), "star": float(i % 3 + 2)} for i in range(30)]
    cs_b = [{**c, "pred": -c["pred"]} for c in cs_a]
    d = paired(cs_a, cs_b, b=200, seed=1)
    assert d["n_cells"] == 30
    assert d["delta"] > 1.0 and d["ci95"][0] > 0 and d["p_le_0"] == 0.0


def test_wilson():
    lo, hi = wilson(50, 100)
    assert lo < 0.5 < hi and 0.39 < lo < 0.41 and 0.59 < hi < 0.61
    assert all(math.isnan(x) for x in wilson(0, 0))
    assert wilson(0, 10)[0] == 0.0


def test_log_odds_uu_tien_ky_nang_dac_trung_khong_phai_pho_bien():
    from collections import Counter

    group = Counter({"Python": 40, "Unity": 20})
    rest = Counter({"Python": 400, "Unity": 5})
    prior = group + rest
    z = log_odds_dirichlet(group, rest, prior)
    assert z["Unity"] > z["Python"]  # Unity đặc trưng hơn dù ít tin hơn


def test_cat_level2():
    assert cat_level2("Công nghệ Thông tin > Thiết kế > Game Development") == "Thiết kế"
    assert cat_level2("Information Technology") == "Information Technology"
    assert cat_level2(None) == "?"
