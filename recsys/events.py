"""WM5 – sinh log tương tác synthetic (không có người dùng thật).

    uv run python -m recsys.events --snapshot data/crawl/topcv/topcv_v1.parquet --users 400

Cách sinh (ghi rõ trong báo cáo – đây là hạn chế lớn nhất của WM5):
- Mỗi người dùng ảo thuộc một **nhóm nghề** (lấy từ cột category mức 2 của tin, ví dụ "Software Engineering").
  Hồ sơ kỹ năng = rút ngẫu nhiên từ các kỹ năng phổ biến của nhóm đó (mô phỏng người dùng khai kỹ năng trong app).
- Người dùng "xem" tin theo xác suất: tin cùng nhóm nghề nhiều hơn, tin khác nhóm ít hơn (nhiễu),
  và tin lương/ngày mới hơn được ưu tiên nhẹ (mô phỏng thói quen xem tin mới).
- **Thời điểm xem** = ngày đăng tin + 0..`--window` ngày (mặc định 21). Lượt xem rơi sau ngày cuối
  snapshot thì **bỏ** (chưa quan sát được), như log thật cắt ở ngày crawl. v1 dồn chúng về ngày cuối,
  làm 74% lượt xem rơi vào một ngày – xem `experiments/results.md`, mục WM5.
  Nhờ vậy một tin được xem ở nhiều thời điểm khác nhau; chia train/test **theo thời gian** mới có nghĩa
  (nếu đặt thời điểm xem đúng bằng ngày đăng thì mỗi tin chỉ nằm một phía, baseline độ phổ biến luôn = 0).

Log này KHÔNG dùng để chứng minh mô hình tốt với người thật; nó chỉ cho phép so sánh các chiến lược
gợi ý với nhau trên cùng một giả định hành vi.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "data" / "crawl" / "topcv" / "topcv_v1.parquet"
DEFAULT_OUT = ROOT / "data" / "eval" / "reco_events_v2.jsonl"
VERSION = "events-synthetic-v2"


def job_group(category: str | None) -> str:
    """Nhóm nghề = mức 2 của category TopCV ("Công nghệ Thông tin > Software Engineering > ...")."""
    parts = [p.strip() for p in (category or "").split(">")]
    return parts[1] if len(parts) > 1 else "Khác"


def skills_of(row: dict) -> list[str]:
    tags = row.get("skill_tags")
    return [str(t).strip() for t in tags if str(t).strip()] if tags is not None else []


def group_skill_pool(df: pd.DataFrame) -> dict[str, list[str]]:
    """Kỹ năng hay gặp của từng nhóm nghề, dùng làm nguồn rút hồ sơ người dùng."""
    pool: dict[str, Counter] = {}
    for r in df.to_dict("records"):
        pool.setdefault(job_group(r["category"]), Counter()).update(skills_of(r))
    return {g: [s for s, _ in c.most_common(30)] for g, c in pool.items() if c}


def generate(df: pd.DataFrame, n_users: int, seed: int, window: int = 21) -> list[dict]:
    rng = random.Random(seed)
    pools = group_skill_pool(df)
    groups = sorted(pools)
    jobs = df.to_dict("records")
    by_group: dict[str, list[dict]] = {}
    for j in jobs:
        by_group.setdefault(job_group(j["category"]), []).append(j)
    dates = sorted(str(j["date_posted"]) for j in jobs if j["date_posted"] is not None)
    if not groups or not dates:
        raise SystemExit("Snapshot không có category hoặc date_posted để sinh log")
    last_day = date.fromisoformat(dates[-1])

    events = []
    for i in range(n_users):
        g = groups[i % len(groups)]
        pool = pools[g]
        k = min(len(pool), rng.randint(3, 8))
        profile = rng.sample(pool, k) if k else []
        user = {"user_id": f"syn-u-{i:04d}", "group": g, "skills": profile}
        # 70% lượt xem trong nhóm nghề, 30% ngoài nhóm (nhiễu)
        n_views = rng.randint(5, 20)
        seen: set[str] = set()
        n_seen = 0
        # Thử tối đa 10 lần số lượt cần có: lượt xem rơi ngoài kỳ quan sát bị bỏ nên phải rút tiếp,
        # không thì log chỉ còn ~3 lượt/người (thử nghiệm: 1.094 lượt thay vì ~3.500).
        for _ in range(10 * n_views):
            if n_seen >= n_views:
                break
            pool_jobs = by_group.get(g, jobs) if rng.random() < 0.7 else jobs
            if not pool_jobs:
                continue
            # ưu tiên nhẹ tin mới: rút 3 tin, giữ tin có date_posted lớn nhất
            cand = [rng.choice(pool_jobs) for _ in range(3)]
            j = max(cand, key=lambda x: str(x["date_posted"] or ""))
            if j["job_uid"] in seen:
                continue
            seen.add(j["job_uid"])
            posted = date.fromisoformat(str(j["date_posted"]))
            # Lượt xem rơi sau ngày cuối snapshot thì BỎ (chưa quan sát được), giống log thật cắt ở ngày crawl.
            # v1 dồn chúng về đúng ngày cuối bằng `min(..., last_day)`: 2.612/3.541 lượt (74%) rơi vào một
            # ngày. Rút độ trễ trong số ngày còn lại cũng không ổn: vẫn dồn về mấy ngày cuối (36% một ngày).
            viewed = posted + timedelta(days=rng.randint(0, window))
            if viewed > last_day:
                continue
            n_seen += 1
            events.append(
                {
                    "user_id": user["user_id"],
                    "group": g,
                    "skills": profile,
                    "job_uid": j["job_uid"],
                    "event_ts": viewed.isoformat(),
                    "event_type": "view",
                }
            )
    return events


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--users", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261112)
    ap.add_argument("--window", type=int, default=21, help="số ngày tối đa sau ngày đăng mà người dùng xem tin")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    df = pd.read_parquet(args.snapshot).drop_duplicates("job_uid")
    events = generate(df, args.users, args.seed, args.window)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    users = len({e["user_id"] for e in events})
    print(
        f"{VERSION}: {users} người dùng ảo, {len(events)} lượt xem trên {len(df)} tin "
        f"(trung bình {len(events) / max(1, users):.1f} lượt/người) → {args.out}"
    )


if __name__ == "__main__":
    main()
