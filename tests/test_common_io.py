from common.io import read_jsonl


def test_read_jsonl_bo_dong_trong_va_giu_tieng_viet(tmp_path):
    f = tmp_path / "a.jsonl"
    f.write_text('{"x": "kỹ năng"}\n\n   \n{"x": 2}\n', encoding="utf-8")
    assert read_jsonl(f) == [{"x": "kỹ năng"}, {"x": 2}]


def test_read_jsonl_file_rong(tmp_path):
    f = tmp_path / "b.jsonl"
    f.write_text("", encoding="utf-8")
    assert read_jsonl(f) == []
