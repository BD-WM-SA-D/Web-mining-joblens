"""Kiểm tra tách từ và ánh xạ nhãn token ↔ đơn vị cho PhoBERT (không cần torch, không cần model)."""

from ie.phobert import from_units, hybrid, segment, to_units


def fake_wt(text):
    # giả lập underthesea: gộp "kinh nghiệm", tách "C++" thành C + +
    out = []
    for t in text.replace("kinh nghiệm", "kinh\x00nghiệm").split():
        out += ["C", "+", "+"] if t == "C++" else [t.replace("\x00", " ")]
    return out


def test_segment_merges_words_and_survives_split_tokens():
    toks = ["Có", "kinh", "nghiệm", "C++"]
    units = segment(toks, fake_wt)
    assert units == [("Có", [0]), ("kinh_nghiệm", [1, 2]), ("C++", [3])]


def test_units_roundtrip():
    toks = ["Có", "kinh", "nghiệm", "C++"]
    units = segment(toks, fake_wt)
    tags = ["O", "B-SKILL", "I-SKILL", "B-SKILL"]
    assert from_units(to_units(tags, units), units, len(toks)) == tags


def test_hybrid_fills_gaps_only():
    model = ["B-SKILL", "I-SKILL", "O", "O"]
    dct = ["B-SKILL", "O", "O", "B-SKILL"]
    assert hybrid(model, dct) == ["B-SKILL", "I-SKILL", "O", "B-SKILL"]
