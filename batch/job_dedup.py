"""Image `job-dedup` (WM1): silver.job_postings → silver.job_dedup (contract 0.1.1, merge theo job_uid).

    uv run python -m batch.job_dedup --input-file data/crawl/topcv/topcv_v2.parquet \\
        --output-file data/batch/job_dedup.parquet --run-id local-1
    python -m batch.job_dedup --input-table silver.job_postings --input-snapshot <id> \\
        --output-table silver.job_dedup --run-id <airflow-run-id>

Thuật toán = **dedup v2** đã chấm trên 300 cặp gán tay (`experiments/results.md`, mục "Kết quả dedup v2"):
khóa tiêu đề mềm + công ty ∪ MinHash LSH (shingle 3 từ, đã cắt khung mô tả chung của công ty) với Jaccard ≥ 0,5.
F1 trên cặp 0,667 (nhãn guideline 0.1) / 0,645 (0.2). `--stub` = baseline khóa tiêu đề + công ty chính xác
(P 1,000, R 0,33–0,39): không bao giờ gộp nhầm, nhưng bỏ sót nhiều.

Cặp → nhóm bằng hợp nhất tập (union-find), nên trùng có tính bắc cầu: A~B, B~C thì A, B, C cùng nhóm. Đại diện
nhóm (`dup_group_id`) là tin xuất hiện sớm nhất (`posted_date`, rồi `first_seen_ts`/`crawl_ts`, rồi `job_uid`
để tất định). Mọi tin đều có đúng một dòng; tin không trùng ai thì `dup_group_id` = chính nó, `score` = null.
`score` = Jaccard ước lượng (MinHash, sau khi cắt khung) giữa tin và đại diện.

Giới hạn đã biết (từ đánh giá): hai vị trí khác cấp bậc của cùng công ty có mô tả gần như y hệt vẫn bị gộp
(MB Bank "Middle, Senior" và "All Level"); ở công ty ít tin, phần chung của hai tin trùng có thể bị coi là khung.
"""

from __future__ import annotations

import argparse

import pandas as pd

from batch.tables import add_io_args, load_input, save_output, version
from crawler.dedup import baseline_pairs, minhash_of, minhash_pairs, shingle_sets

THRESHOLD = 0.5
INPUT_COLUMNS = (
    "job_uid",
    "source",
    "title",
    "company_name",
    "description",
    "requirements",
    "posted_date",
    "first_seen_ts",
)


class UnionFind:
    def __init__(self, items) -> None:
        self.parent = {x: x for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def seen_key(r: dict) -> tuple[str, str, str]:
    first = r.get("posted_date") or r.get("first_seen_ts") or r.get("crawl_ts")
    return (
        str(first) if first is not None else "9999",
        str(r.get("first_seen_ts") or r.get("crawl_ts") or ""),
        r["job_uid"],
    )


def groups(jobs: list[dict], stub: bool) -> tuple[dict[str, str], dict[str, float]]:
    """job_uid → dup_group_id, và job_uid → Jaccard với đại diện (chỉ tin không phải đại diện)."""
    df = pd.DataFrame(jobs)
    if stub:
        pairs = baseline_pairs(df)
    else:
        pairs = baseline_pairs(df, soft=True) | set(minhash_pairs(df, THRESHOLD, strip=True))
    uf = UnionFind(df["job_uid"])
    for a, b in pairs:
        uf.union(a, b)
    members: dict[str, list[dict]] = {}
    for r in jobs:
        members.setdefault(uf.find(r["job_uid"]), []).append(r)
    group = {}
    for rows in members.values():
        rep = min(rows, key=seen_key)["job_uid"]
        for r in rows:
            group[r["job_uid"]] = rep
    score: dict[str, float] = {}
    multi = {u for u, g in group.items() if u != g}
    if multi:
        sets = shingle_sets(df, strip=not stub)
        mh = {u: minhash_of(sets[u]) for u in multi | {group[u] for u in multi}}
        score = {u: float(mh[u].jaccard(mh[group[u]])) for u in multi}
    return group, score


def dedup(jobs: list[dict], stub: bool, run_id: str) -> list[dict]:
    group, score = groups(jobs, stub)
    ver = version(stub)
    return [
        {
            "job_uid": r["job_uid"],
            "dup_group_id": group[r["job_uid"]],
            "score": score.get(r["job_uid"]),
            "dedup_version": ver,
            "run_id": run_id,
        }
        for r in jobs
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_io_args(ap, "silver.job_dedup")
    args = ap.parse_args()
    jobs = load_input(args, INPUT_COLUMNS)
    rows = dedup(jobs, args.stub, args.run_id)
    n_groups = len({r["dup_group_id"] for r in rows})
    print(f"{len(jobs)} tin → {n_groups} nhóm ({len(jobs) - n_groups} tin bị gộp vào tin khác)", flush=True)
    save_output(rows, args, key="job_uid")


if __name__ == "__main__":
    main()
