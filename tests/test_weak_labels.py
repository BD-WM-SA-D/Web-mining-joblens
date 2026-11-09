"""Kiểm tra lọc tag và gán nhãn yếu (không cần dữ liệu)."""

from ie.weak_labels import clean_tags, label_tokens


def test_clean_tags_drops_soft_short_and_long():
    soft = {"giao tiếp"}
    tags = ["Python", "Giao tiếp", "C", "Ai", "Có khả năng làm việc dưới áp lực cao", "Spring Boot"]
    assert clean_tags(tags, soft) == ["Python", "Spring Boot"]


def test_label_tokens_uses_posting_tags():
    toks = ["Kinh", "nghiệm", "Digiwin", "T100", "và", "SQL"]
    assert label_tokens(toks, ["SQL", "Digiwin T100"]) == ["O", "O", "B-SKILL", "I-SKILL", "O", "B-SKILL"]
