"""Kiểm tra các hàm chuẩn bị dữ liệu WM2 (không cần file VietJobs)."""

import pandas as pd

from annotation.sample_skill_batch import mask_pii, sample, split_sentences
from ie.skill_alias import build, norm_key
from ie.vietjobs import to_list


def test_to_list():
    assert to_list("['Python', ' SQL ']") == ["Python", "SQL"]
    assert to_list("[]") == []
    assert to_list(None) == []


def test_norm_key_groups_variants():
    assert norm_key("ReactJS") == norm_key("React.js") == norm_key("React") == "react"
    assert norm_key("Adobe Photoshop") == norm_key("photoshop")
    assert norm_key("MS SQL") == norm_key("Microsoft SQL Server") == norm_key("SQL Server")
    assert norm_key("After Effect") == norm_key("Adobe After Effects")
    assert norm_key("React Native") != norm_key("React")
    assert norm_key("Kỹ năng giao tiếp") == ""


def test_build_picks_most_common_as_canonical():
    rows = build([["ReactJS", "Python"], ["React", "ReactJS"], ["Kỹ năng giao tiếp"]], top=10)
    assert {(r["canonical"], r["alias"]) for r in rows} == {
        ("ReactJS", "ReactJS"),
        ("ReactJS", "React"),
        ("Python", "Python"),
    }


def test_split_sentences_bullets():
    text = "- Lập trình Java, Spring Boot\n• Có kinh nghiệm Docker\n- Nam\n1. Thành thạo Git và Jira"
    assert split_sentences(text) == ["Lập trình Java, Spring Boot", "Có kinh nghiệm Docker", "Thành thạo Git và Jira"]
    assert split_sentences(None) == []


def test_mask_pii():
    assert mask_pii("Gửi CV về hr@abc.vn hoặc 0912 345 678") == "Gửi CV về <EMAIL> hoặc <PHONE>"


def test_sample_takes_whole_postings_and_is_reproducible():
    df = pd.DataFrame(
        {
            "job_uid": [f"{i:040d}" for i in range(20)],
            "description": ["- Viết code Python hằng ngày\n- Dùng Git để quản lý"] * 20,
            "requirements_text": ["- Biết Docker và Linux"] * 20,
        }
    )
    tasks, picked = sample(df, target=10, seed=1, exclude=set())
    assert len(picked) == 4 and len(tasks) == 12
    assert {t["job_uid"] for t in tasks} == set(picked)
    assert sample(df, target=10, seed=1, exclude=set())[1] == picked
    assert not set(picked) & set(sample(df, target=10, seed=1, exclude=set(picked))[1])


def test_sample_max_per_posting():
    df = pd.DataFrame(
        {
            "job_uid": [f"{i:040d}" for i in range(10)],
            "description": ["\n".join(f"- Câu mô tả số {k} có Python" for k in range(6))] * 10,
            "requirements_text": ["- Biết Docker và Linux"] * 10,
        }
    )
    tasks, picked = sample(df, target=12, seed=3, exclude=set(), max_per_posting=3)
    assert len(picked) == 4 and len(tasks) == 12
    assert all(sum(t["job_uid"] == u for t in tasks) == 3 for u in picked)
