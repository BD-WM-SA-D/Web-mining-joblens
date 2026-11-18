"""Mẫu đo κ không được mang nhãn của người thứ nhất sang cho người thứ hai."""

from __future__ import annotations

import json

from annotation.sample_absa_kappa import load_gold, to_label_studio

ROW = {
    "sentence_id": "abc123",
    "text": "Lương thấp hơn thị trường.",
    "section": "improvement",
    "lang": "vi",
    "company_name": "Công ty A",
    "gold": {"salary_benefits": "negative"},
    "flag": "khó / cần bàn",
    "comment": "câu này hơi mơ hồ",
    "n_annotations": 1,
}


def test_khong_lot_nhan_nguoi_thu_nhat():
    task = to_label_studio([ROW])[0]
    blob = json.dumps(task, ensure_ascii=False)
    assert set(task["data"]) == {"sentence_id", "index", "text", "company_name", "section", "lang"}
    for leak in ("gold", "flag", "comment", "negative", "salary_benefits", "mơ hồ"):
        assert leak not in blob


def test_bo_cau_khong_gan_duoc(tmp_path):
    rows = [
        ROW,
        {**ROW, "sentence_id": "def456", "flag": "không gán được (câu vô nghĩa, lẫn ngôn ngữ)"},
    ]
    p = tmp_path / "gold.absa.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    kept = load_gold(p)
    assert [r["sentence_id"] for r in kept] == ["abc123"]
