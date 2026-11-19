from absa.lexicon import ASPECTS, is_advice, is_missing, match_aspects, match_polarity, predict
from absa.weak_labels import weak_label


def test_khia_canh_dung_bo_6_cua_contract():
    """6 khía cạnh phải đúng khoá của silver.review_aspects (hợp đồng ở repo joblens)."""
    assert ASPECTS == (
        "salary_benefits",
        "training_learning",
        "management_care",
        "culture_fun",
        "office_workspace",
        "work_life_balance",
    )


def test_match_aspect_ca_tieng_viet_va_tieng_anh():
    assert match_aspects("Mức lương phù hợp với thị trường") == ["salary_benefits"]
    assert match_aspects("Salary and bonuses are competitive") == ["salary_benefits"]
    assert match_aspects("Văn phòng rộng rãi, thiết bị mới") == ["office_workspace"]


def test_cum_dai_duoc_uu_tien():
    """'work life balance' phải khớp cả cụm, không bị cắt thành từ lẻ."""
    assert match_aspects("Good work life balance here") == ["work_life_balance"]


def test_khop_theo_bien_tu():
    """'ot' không được khớp trong 'một', 'hot'."""
    assert "work_life_balance" not in match_aspects("Chỉ có một việc cần làm")


def test_phu_dinh_dao_dau_cuc_tinh():
    assert match_polarity("Văn phòng rất tốt") == "positive"
    assert match_polarity("Văn phòng không tốt") == "negative"
    assert match_polarity("The pay is not competitive") == "negative"


def test_predict_tra_ve_cap_khia_canh_cuc_tinh():
    out = predict("Đồng nghiệp thân thiện nhưng lương thấp")
    assert {d["aspect"] for d in out} == {"culture_fun", "salary_benefits"}
    assert all(d["polarity"] in ("positive", "negative", "neutral") for d in out)


def test_nhan_yeu_lay_cuc_tinh_tu_sao_truoc():
    sent = {
        "text": "Mức lương chưa theo kịp thị trường",
        "section": "liked",  # phần 'liked' nói tích cực, nhưng sao 2 phải thắng
        "aspect_ratings": {"salary_benefits": 2.0},
        "rating_overall": 4.0,
    }
    (lb,) = weak_label(sent)
    assert lb == {"aspect": "salary_benefits", "polarity": "negative", "source": "star"}


def test_nhan_yeu_khong_co_sao_thi_theo_phan():
    """ITviec không cho sao cho work_life_balance → chỉ còn tín hiệu phần của review."""
    sent = {
        "text": "OT khá nhiều vào cuối sprint",
        "section": "improvement",
        "aspect_ratings": {},
        "rating_overall": 4.0,
    }
    (lb,) = weak_label(sent)
    assert lb["aspect"] == "work_life_balance"
    assert lb == {"aspect": "work_life_balance", "polarity": "negative", "source": "section"}


def test_nhan_yeu_rong_khi_tu_dien_khong_nhan_ra():
    sent = {"text": "Mình đã làm ở đây khoảng hai năm", "section": "liked", "aspect_ratings": {}, "rating_overall": 4.0}
    assert weak_label(sent) == []


def test_luat_de_nghi_la_chê():
    """12/25 lỗi cực tính trên dev là câu chê bằng cách đề nghị, không có từ cảm xúc xấu nào."""
    for s in (
        "Cần chú ý thêm về chế độ thưởng cho OT",
        "Công ty nên mua thêm nhiều MacOS",
        "Cải thiện cơ sở vật chất, làm hybrid",
        "Rất mong công ty sẽ tăng lương thôi và thêm phụ cấp!!",
        "Career paths should be more transparent.",
    ):
        assert is_advice(s), s
        assert match_polarity(s) == "negative", s


def test_de_nghi_bi_phu_dinh_thi_khong_tinh():
    """ "Không có gì cần cải thiện cả. Phúc lợi khá tốt." là khen, không phải đề nghị (guideline mục 3)."""
    s = "Không có gì cần cải thiện cả. Phúc lợi khá tốt."
    assert not is_advice(s)
    assert match_polarity(s) == "positive"


def test_advice_false_tai_lap_duoc_co_ban():
    s = "Cải thiện cơ sở vật chất"
    assert match_polarity(s, advice=True) == "negative"
    assert match_polarity(s, advice=False) == "neutral"


def test_moi_truong_ra_culture_fun():
    """Guideline 0.2.2 mục 2c: "môi trường + từ đánh giá chung" → `culture_fun`."""
    assert match_aspects("Môi trường làm việc tốt") == ["culture_fun"]
    assert match_aspects("Good environment") == ["culture_fun"]
    assert "culture_fun" in match_aspects("Đồng nghiệp thân thiện, môi trường thoải mái")


def test_moi_truong_co_bo_ngu_hoc_hoi_ra_training_learning():
    """Cụm dài khớp trước nên "môi trường học hỏi" không bị đọc thành `culture_fun`."""
    assert match_aspects("Môi trường học hỏi tốt") == ["training_learning"]
    assert match_aspects("Good learning environment for Junior") == ["training_learning"]


def test_thuat_ngu_bang_2c():
    assert match_aspects("Không có company trip") == ["culture_fun"]
    assert match_aspects("Có cả máy pha cafe.") == ["office_workspace"]
    assert match_aspects("mong công ty có thêm hỗ trợ gym") == ["salary_benefits"]
    assert match_aspects("nhà xe hơi chật, bàn ghế ngồi hơi chật") == ["office_workspace"]
    assert match_aspects("thời gian tương đối flexiable") == ["work_life_balance"]


def test_luat_khong_co_la_che():
    """ "Không có <khía cạnh>" là chê dù trong câu không có từ cảm xúc nào."""
    assert is_missing("Không có company trip")
    assert match_polarity("Không có company trip") == "negative"
    assert match_polarity("Không có lương OT") == "negative"
    assert match_polarity("Không có company trip", missing=False) == "neutral"


def test_khong_co_gi_de_che_van_la_khen():
    """Lookahead chặn "không có **gì**": đó là khen, không phải thiếu thứ gì."""
    s = "Không có gì cần cải thiện cả. Phúc lợi khá tốt."
    assert not is_missing(s)
    assert match_polarity(s) == "positive"


def test_luat_khong_co_can_co_khia_canh():
    """Câu "không có" mà không nói tới khía cạnh nào thì không áp luật."""
    assert not is_missing("Không có nhận xét")


def test_luat_hoa_lay_negative():
    """Câu khen một ý chê một ý: `neutral` dành cho câu KHÔNG đánh giá gì (guideline 2d)."""
    s = "Great environment, but unfair performance review"
    assert match_polarity(s, tie=False) == "neutral"
    assert match_polarity(s, tie=True) == "negative"


def test_luat_hoa_khong_cham_cau_khong_co_tu_cam_xuc():
    """Không có từ cảm xúc nào thì vẫn là `neutral`, luật hòa không được biến nó thành chê."""
    assert match_polarity("Công ty có 200 nhân viên", tie=True) == "neutral"


def test_cai_thien_trong_cau_khen_khong_phai_de_nghi():
    """ "được/luôn/cố gắng + cải thiện" là kể việc tốt, không phải lời đề nghị."""
    assert not is_advice("Luôn được học hỏi và cải thiện kỹ năng")
    assert not is_advice("Công ty luôn cố gắng cải thiện để đáp ứng nhu cầu nhân viên")
    assert is_advice("Cần cải thiện cơ sở vật chất")


def test_need_to_mot_minh_khong_con_la_de_nghi():
    """ "Rarely need to do OT" là khen; chỉ "need to be/needs to be" mới tính là đề nghị."""
    assert not is_advice("Rarely need to do OT.")
    assert is_advice("The process needs to be more transparent")


def test_tat_ca_ba_luat_tai_lap_co_ban():
    """Tắt cả ba luật thì về đúng baseline từ điển cơ bản (chỉ đếm từ cảm xúc)."""
    off = dict(advice=False, missing=False, tie=False)
    assert match_polarity("Cải thiện cơ sở vật chất", **off) == "neutral"
    assert match_polarity("Không có company trip", **off) == "neutral"
    assert match_polarity("Lương thấp", **off) == "negative"
    assert match_polarity("Đồng nghiệp thân thiện", **off) == "positive"
