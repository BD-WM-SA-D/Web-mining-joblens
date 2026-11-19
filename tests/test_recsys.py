import pandas as pd

from recsys.baseline import idf_weights, ndcg_at_k, rank_popularity, score_content_skill, split_time
from recsys.events import generate, group_skill_pool, job_group


def df_jobs():
    return pd.DataFrame(
        [
            {
                "job_uid": f"j{i}",
                "category": f"Công nghệ Thông tin > {g} > Vị trí {i}",
                "skill_tags": tags,
                "date_posted": f"2026-09-{(i % 20) + 1:02d}",
                "title": f"Tin {i}",
                "description": " ".join(tags),
                "requirements_text": "",
            }
            for i, (g, tags) in enumerate(
                [
                    ("Software Engineering", ["Java", "Spring"]),
                    ("Software Engineering", ["Python", "Django"]),
                    ("Software Testing", ["Selenium", "Manual test"]),
                    ("Software Testing", ["Postman", "Selenium"]),
                    ("Software Engineering", ["Java", "Kafka"]),
                ]
            )
        ]
    )


def test_job_group_lay_muc_hai():
    assert job_group("Công nghệ Thông tin > Software Engineering > Backend") == "Software Engineering"
    assert job_group("Không có dấu lớn hơn") == "Khác"
    assert job_group(None) == "Khác"


def test_group_skill_pool_gom_theo_nhom():
    pool = group_skill_pool(df_jobs())
    assert "Java" in pool["Software Engineering"]
    assert "Selenium" in pool["Software Testing"]
    assert "Java" not in pool["Software Testing"]


def test_generate_sinh_log_on_dinh_theo_seed():
    df = df_jobs()
    a = generate(df, n_users=10, seed=1)
    b = generate(df, n_users=10, seed=1)
    assert a == b
    assert generate(df, n_users=10, seed=2) != a
    assert {e["event_type"] for e in a} == {"view"}
    # thời điểm xem không sớm hơn ngày đăng
    posted = dict(zip(df["job_uid"], df["date_posted"], strict=True))
    assert all(e["event_ts"] >= posted[e["job_uid"]] for e in a)


def test_split_time_theo_phan_vi_luot_xem():
    events = [{"event_ts": f"2026-09-{d:02d}", "user_id": "u", "job_uid": f"j{d}"} for d in range(1, 11)]
    train, test = split_time(events, 0.3)
    assert len(train) == 7 and len(test) == 3
    assert max(e["event_ts"] for e in train) < min(e["event_ts"] for e in test)


def test_ndcg_at_k():
    assert ndcg_at_k(["a", "b", "c"], {"a"}, k=3) == 1.0
    assert ndcg_at_k(["x", "y", "z"], {"a"}, k=3) == 0.0
    assert 0 < ndcg_at_k(["x", "a", "y"], {"a"}, k=3) < 1.0


def test_popularity_dem_luot_xem_trong_train():
    train = [{"job_uid": "j1"}, {"job_uid": "j1"}, {"job_uid": "j2"}]
    pop = rank_popularity(train, ["j1", "j2", "j3"])
    assert pop["j1"] == 2 and pop["j2"] == 1 and pop["j3"] == 0


def test_content_skill_uu_tien_tin_trung_ky_nang():
    skills = {"j1": ["Java", "Spring"], "j2": ["Selenium"], "j3": []}
    idf = idf_weights(skills)
    scores = score_content_skill(["java", "spring"], skills, idf)
    assert scores["j1"] > scores["j2"] >= scores["j3"]


def test_chia_theo_thoi_gian_khong_de_mot_ngay_dong_keo_lech_ty_le():
    """Nhiều lượt xem trùng một ngày: mốc phải là ranh giới giữa hai ngày gần tỷ lệ mục tiêu nhất."""
    from recsys.baseline import split_time

    days = ["2026-10-01"] * 30 + ["2026-10-02"] * 40 + ["2026-10-03"] * 30
    events = [{"event_ts": d} for d in days]
    train, test = split_time(events, 0.3)
    assert len(train) == 70 and len(test) == 30  # ranh giới trước ngày 03 cho đúng 70/30
    assert max(e["event_ts"] for e in train) < min(e["event_ts"] for e in test)


def test_log_synthetic_khong_don_luot_xem_vao_ngay_cuoi():
    """Lượt xem rơi sau ngày cuối snapshot bị bỏ, không bị dồn về ngày cuối (lỗi của log cũ)."""
    import collections

    import pandas as pd

    from recsys.events import generate

    df = pd.DataFrame(
        [
            {"job_uid": f"j{i}", "category": "IT > Dev", "skill_tags": ["Python"], "date_posted": f"2026-10-{d:02d}"}
            for i, d in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 3)
        ]
    )
    events = generate(df, n_users=40, seed=1, window=21)
    last = max(e["event_ts"] for e in events)
    assert last <= "2026-10-10"
    share_last = collections.Counter(e["event_ts"] for e in events)[last] / len(events)
    assert share_last < 0.3
