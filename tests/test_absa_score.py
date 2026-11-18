from absa.score import as_dict, macro_f1, prf, report, slots


def test_as_dict():
    assert as_dict([{"aspect": "salary_benefits", "polarity": "negative"}]) == {"salary_benefits": "negative"}


def test_prf_tinh_tay():
    gold = [{"a", "b"}, {"c"}]
    pred = [{"a"}, {"c", "d"}]
    r = prf(gold, pred)
    assert r["tp"] == 2 and r["n_pred"] == 3 and r["n_gold"] == 3
    assert r["p"] == 2 / 3 and r["r"] == 2 / 3 and r["f1"] == 2 / 3


def test_prf_khong_du_doan_gi():
    r = prf([{"a"}], [set()])
    assert r["p"] == 0.0 and r["r"] == 0.0 and r["f1"] == 0.0


def test_slots_de_trong_thanh_none():
    """Khía cạnh không có trong dict phải thành `none`, KHÔNG thành `neutral` (guideline mục 2)."""
    y_true, y_pred = slots([{"salary_benefits": "positive"}], [{}])
    assert len(y_true) == 6 and y_true.count("none") == 5
    assert set(y_pred) == {"none"}


def test_macro_f1_khong_bo_qua_lop_vang_mat():
    """Đoán toàn `positive` không được điểm cao: hai lớp kia F1 = 0 vẫn vào trung bình."""
    macro, per = macro_f1(["positive"] * 4, ["positive"] * 4)
    assert per["positive"]["f1"] == 1.0
    assert macro == 1 / 3


def test_report_hoan_hao():
    gold = [{"salary_benefits": "negative"}, {}]
    rep = report(gold, gold)
    assert rep["aspect"]["f1"] == 1.0
    assert rep["polarity_on_matched"]["n"] == 1
    assert rep["slot"]["per_class"]["negative"]["f1"] == 1.0
