"""Đóng băng dữ liệu crawl thành snapshot cố định (Parquet) để train/test tái lập được.

    uv run python -m crawler.snapshot --source topcv --name topcv_v1

Đọc mọi data/crawl/<source>/*/jobs.jsonl (message job_posting.v1), bỏ trùng theo source_job_id (giữ lần crawl
mới nhất), ghi data/crawl/<source>/<name>.parquet + <name>.manifest.json. Không commit (data/ đã gitignore).
Cột description/requirements_text cùng tên với snapshot VietJobs để annotation/sample_skill_batch.py dùng chung.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from joblens_contracts import job_uid

ROOT = Path(__file__).resolve().parents[1]


def load_messages(files: list[Path]) -> pd.DataFrame:
    rows = {}
    for f in sorted(files):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            m = json.loads(line)
            p = m["payload"]
            prev = rows.get(m["source_job_id"])
            if prev and prev["crawl_ts"] >= m["crawl_ts"]:
                continue
            rows[m["source_job_id"]] = {
                "job_uid": job_uid(m["source"], m["source_job_id"]),
                "source": m["source"],
                "source_job_id": m["source_job_id"],
                "url": m.get("url"),
                "crawl_ts": m["crawl_ts"],
                "content_hash": m["content_hash"],
                "title": p["title"],
                "company_name": p.get("company_name"),
                "category": p.get("category"),
                "locations": p.get("locations") or [],
                "salary_text": p.get("salary_text"),
                "date_posted": p.get("date_posted"),
                "skill_tags": p.get("skill_tags") or [],
                "description": p.get("description"),
                "requirements_text": p.get("requirements"),
            }
    return pd.DataFrame(list(rows.values())).sort_values(
        "source_job_id", key=lambda s: s.astype(int), ignore_index=True
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="topcv")
    ap.add_argument("--name", required=True, help="tên snapshot, ví dụ topcv_v1 – không ghi đè snapshot đã có")
    args = ap.parse_args()

    base = ROOT / "data" / "crawl" / args.source
    out = base / f"{args.name}.parquet"
    if out.exists():
        raise SystemExit(f"{out} đã có – snapshot là bất biến, đặt tên mới (ví dụ {args.source}_v2)")
    files = list(base.glob("*/jobs.jsonl"))
    df = load_messages(files)
    df.to_parquet(out, index=False)
    ids = "\n".join(df["source_job_id"]).encode()
    manifest = {
        "snapshot": args.name,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": args.source,
        "files": [str(f.relative_to(ROOT)) for f in sorted(files)],
        "rows": len(df),
        "ids_sha256": hashlib.sha256(ids).hexdigest(),
        "date_posted_min": df["date_posted"].min(),
        "date_posted_max": df["date_posted"].max(),
    }
    (base / f"{args.name}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
