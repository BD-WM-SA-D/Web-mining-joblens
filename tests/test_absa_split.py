from absa.split import detect_lang, sentences_of, split_text

REVIEW = {
    "source_review_id": "r1",
    "company_id": "abc-software",
    "payload": {
        "company_name": "ABC Software",
        "review_month": "2026-10",
        "rating_overall": 4.0,
        "aspect_ratings": {"salary_benefits": 2.0, "culture_fun": 5.0},
        "recommend": True,
        "title": "Chỗ tốt để học nhưng lương thấp",
        "liked_text": "- Đồng nghiệp thân thiện, luôn sẵn sàng giúp đỡ. - Nhiều khóa học nội bộ.",
        "improvement_text": "Lương nên điều chỉnh theo thị trường. OT nhiều lúc gần deadline.",
    },
}


def test_detect_lang():
    assert detect_lang("Đồng nghiệp thân thiện, môi trường thoải mái") == "vi"
    assert detect_lang("Friendly teammates and a clear process") == "en"
    # vài tên riêng có dấu không được nhận nhầm là câu tiếng Việt
    assert detect_lang("Great office in Ha Noi") == "en"


def test_tach_gach_dau_dong():
    """sent_tokenize không cắt ở dấu '-', phải cắt gạch đầu dòng trước."""
    out = split_text("- Đồng nghiệp thân thiện. - Lương thì thấp hơn thị trường.", "vi")
    assert len(out) == 2
    assert out[0].startswith("Đồng nghiệp")
    assert out[1].startswith("Lương")


def test_bo_cau_qua_ngan_va_khong_co_chu():
    assert split_text("- :)) - N/A - 123", "vi") == []


def test_sentences_of_du_bo_cuc_va_boi_canh():
    sents = sentences_of(REVIEW)
    assert {s["section"] for s in sents} == {"title", "liked", "improvement"}
    assert all(s["lang"] == "vi" for s in sents)
    assert all(s["company_id"] == "abc-software" for s in sents)
    # bối cảnh cho nhãn yếu phải đi kèm từng câu
    assert all(s["aspect_ratings"]["salary_benefits"] == 2.0 for s in sents)


def test_sentence_id_on_dinh_va_khong_trung():
    ids = [s["sentence_id"] for s in sentences_of(REVIEW)]
    assert len(ids) == len(set(ids))
    assert ids == [s["sentence_id"] for s in sentences_of(REVIEW)]


def test_br_la_ranh_gioi_cau():
    """ITviec dùng <br> làm ranh giới ý (57,6% khối review). Parser giữ nó thành "\n"."""
    text = "Cơ sở vật chất tốt, có bàn nâng hạ đỡ mỏi lưng\nBản thân tôi chưa bao giờ phải OT"
    out = split_text(text, "vi")
    assert len(out) == 2
    assert out[0].startswith("Cơ sở vật chất")
    assert out[1].startswith("Bản thân tôi")


def test_sentence_id_on_dinh_khi_doi_thu_tu():
    """id băm theo nội dung, không theo chỉ số câu: chèn câu mới ở đầu không làm đổi id câu sau."""
    base = {
        "source_review_id": "r1",
        "company_id": "c1",
        "payload": {"liked_text": "Văn phòng rất đẹp và rộng rãi.", "company_name": "X"},
    }
    added = {
        "source_review_id": "r1",
        "company_id": "c1",
        "payload": {
            "liked_text": "Đồng nghiệp hỗ trợ nhau tốt.\nVăn phòng rất đẹp và rộng rãi.",
            "company_name": "X",
        },
    }
    id_truoc = sentences_of(base)[0]["sentence_id"]
    sau = {s["text"]: s["sentence_id"] for s in sentences_of(added)}
    assert sau["Văn phòng rất đẹp và rộng rãi."] == id_truoc


def test_cau_trung_y_nguyen_van_co_id_khac_nhau():
    rv = {
        "source_review_id": "r2",
        "company_id": "c1",
        "payload": {"liked_text": "Lương thưởng khá ổn.\nLương thưởng khá ổn.", "company_name": "X"},
    }
    ids = [s["sentence_id"] for s in sentences_of(rv)]
    assert len(ids) == 2 and ids[0] != ids[1]
