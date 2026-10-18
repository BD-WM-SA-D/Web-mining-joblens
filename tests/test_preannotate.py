"""Kiểm tra gợi ý span bằng từ điển (không cần Label Studio)."""

from annotation.preannotate_dict import build_matcher, find_spans, load_aliases, to_result

M = build_matcher(load_aliases())


def texts(s):
    return [t for _, _, t in find_spans(s, M)]


def test_longest_alias_and_boundaries():
    assert texts("Thành thạo React Native, C++ và C#") == ["React Native", "C++", "C#"]
    assert texts("Có kinh nghiệm Docker, kubernetes") == ["Docker", "kubernetes"]
    assert texts("Ai cũng có thể học, làm việc tại Gold Coast") == []  # "Ai", "Go" không khớp bừa


def test_too_generic_skipped():
    assert texts("Hiểu quy trình phát triển phần mềm") == []


def test_result_offsets():
    s = "Biết dùng Git hằng ngày"
    (r,) = to_result(find_spans(s, M))
    v = r["value"]
    assert s[v["start"] : v["end"]] == "Git" and v["labels"] == ["SKILL"]
