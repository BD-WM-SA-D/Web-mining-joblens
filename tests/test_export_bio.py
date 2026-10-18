"""Kiểm tra đổi nhãn Label Studio sang BIO (không cần Label Studio)."""

from annotation.export_bio import convert, to_bio, trim


def test_trim_edges_keeps_plus():
    s = "Biết  SEO, C++."
    assert s[slice(*trim(s, 4, 9))] == "SEO"
    assert s[slice(*trim(s, 10, 15))] == "C++"
    assert "Dùng .NET"[slice(*trim("Dùng .NET", 4, 9))] == ".NET"


def test_to_bio_multi_token_and_slash():
    s = "Dùng CI/CD và Spring Boot"
    toks, tags, bad = to_bio(s, [(5, 10), (14, 25)])
    assert list(zip(toks, tags)) == [
        ("Dùng", "O"),
        ("CI", "B-SKILL"),
        ("/", "I-SKILL"),
        ("CD", "I-SKILL"),
        ("và", "O"),
        ("Spring", "B-SKILL"),
        ("Boot", "I-SKILL"),
    ]
    assert bad == 0


def test_convert_skips_cancelled_and_trims():
    text = "Biết Docker."
    task = {
        "data": {"id": "x-req00", "job_uid": "u", "text": text, "double": True},
        "annotations": [
            {
                "was_cancelled": False,
                "updated_at": "2026-10-18",
                "result": [{"type": "labels", "value": {"start": 4, "end": 12, "labels": ["SKILL"]}}],
            }
        ],
    }
    rows, stats = convert([task, {"data": task["data"], "annotations": [{"was_cancelled": True, "result": []}]}])
    assert len(rows) == 1 and rows[0]["tags"] == ["O", "B-SKILL", "O"] and rows[0]["double"]
    assert stats["trimmed"] == 1 and stats["misaligned"] == 0
