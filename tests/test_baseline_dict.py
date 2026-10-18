"""Kiểm tra baseline từ điển trên token (không cần dữ liệu)."""

from ie.baseline_dict import build_index, spans, tag


def test_tag_longest_and_case():
    index, n = build_index(["React", "React Native", "Go", "SQL"])
    toks = ["Biết", "React", "Native", ",", "sql", "và", "SQL", ";", "go", "Go"]
    assert spans(toks, tag(toks, index, n)) == [(1, 3, "React Native"), (6, 7, "SQL"), (9, 10, "Go")]
