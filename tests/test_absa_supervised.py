"""Mô hình lai WM3: khía cạnh lấy từ từ điển, cực tính học từ nhãn tay."""

from __future__ import annotations

import pytest

from absa.lexicon import match_aspects, sentiment_counts
from absa.supervised import (
    fit_predict_hybrid,
    rule_feats,
    section_rule,
    sentence_polarity,
    targets,
    to_pred,
)


def row(text: str, gold: dict | None = None, section: str = "liked", lang: str = "vi") -> dict:
    return {"text": text, "gold": gold or {}, "section": section, "lang": lang, "sentence_id": text[:8]}


def test_dem_tu_cam_xuc_co_dao_dau_khi_phu_dinh():
    assert sentiment_counts("Phúc lợi tốt, đồng nghiệp thân thiện") == (2, 0)
    # "hấp dẫn" là từ khen, bị "chưa" đảo thành một lượt chê – đây là chỗ hai số này khác
    # `match_polarity`: nó chỉ trả về nhãn, còn mô hình cực tính cần biết đếm được bao nhiêu lượt.
    assert sentiment_counts("Lương chưa hấp dẫn") == (0, 1)
    assert sentiment_counts("Công ty có 200 người") == (0, 0)


def test_cau_hai_chieu_dem_duoc_ca_hai_phia():
    n_pos, n_neg = sentiment_counts("Great environment, but unfair performance review")
    assert n_pos >= 1 and n_neg >= 1


def test_cuc_cua_cau_lay_cuc_hay_gap_nhat():
    assert sentence_polarity(row("x", {"salary_benefits": "negative"})) == "negative"
    assert sentence_polarity(row("x", {"a": "positive", "b": "positive", "c": "negative"})) == "positive"
    assert sentence_polarity(row("x")) is None


def test_dac_trung_luat_co_du_cot_va_bat_duoc_luat_de_nghi():
    feats = rule_feats([row("Mong công ty xem lại chế độ OT"), row("Lương cao")])
    assert feats.shape == (2, 11)
    assert feats[0][5] == 1.0  # is_advice
    assert feats[1][5] == 0.0


def test_khia_canh_cua_mo_hinh_lai_dung_bang_tu_dien():
    from absa.lexicon import match_aspects

    train = [
        row("Lương thấp quá", {"salary_benefits": "negative"}, section="improvement"),
        row("Lương cao và phúc lợi tốt", {"salary_benefits": "positive"}),
        row("OT nhiều, mệt mỏi", {"work_life_balance": "negative"}, section="improvement"),
        row("Đồng nghiệp thân thiện", {"culture_fun": "positive"}),
    ]
    test = [row("Văn phòng đẹp, đồng nghiệp vui vẻ"), row("Không có lương OT", section="improvement")]
    pred = fit_predict_hybrid(train, test, seed=0, tfidf=False)
    assert len(pred) == 2
    for r, p in zip(test, pred, strict=True):
        assert set(p) == set(match_aspects(r["text"])), r["text"]
        assert len(set(p.values())) <= 1  # baseline và mô hình lai đều cho một cực cho cả câu


def test_to_pred_bo_o_none():
    y = targets([row("x", {"salary_benefits": "negative"})])[0]
    assert to_pred(y) == {"salary_benefits": "negative"}


def test_mo_hinh_lai_can_it_nhat_mot_cau_co_nhan():
    with pytest.raises(ValueError):
        fit_predict_hybrid([row("Lương cao")], [row("Lương thấp")], seed=0, tfidf=False)


def test_luat_phan_review_la_moc_bat_buoc():
    """Mốc tầm thường: phần "Đề nghị cải thiện" → chê, phần còn lại → khen."""
    rows = [
        {"text": "Lương tốt, phúc lợi đầy đủ", "section": "liked"},
        {"text": "Lương nên tăng thêm", "section": "improvement"},
    ]
    out = section_rule(rows)
    assert set(out[0]) == set(match_aspects(rows[0]["text"]))
    assert set(out[0].values()) <= {"positive"}
    assert set(out[1].values()) <= {"negative"}


def test_cv_chia_fold_theo_review_khong_theo_cau():
    """Câu của cùng một review phải nằm cùng một fold – không thì CV rò rỉ giữa train và fold giữ lại."""
    from absa.supervised import folds

    groups = ["r1", "r1", "r1", "r2", "r2", "r3", "r4", "r4", "r5", "r6"]
    parts = folds(groups, 3, seed=1)
    assert sorted(i for p in parts for i in p) == list(range(len(groups)))
    for p in parts:
        for g in {groups[i] for i in p}:
            assert all(groups[j] != g for q in parts if q is not p for j in q)
