"""Chỉ mục gợi ý cho mining-service: job_uid → tập skill_id, dựng từ snapshot tin crawl.

    uv run python -m service.index --jobs data/crawl/topcv/topcv_v1.parquet --out data/index/job_skills.json

File chỉ mục chỉ chứa job_uid và skill_id (không có văn bản tin), dùng khi build image.
Bản stub: trích bằng từ điển trên tiêu đề + mô tả + yêu cầu, cộng tag "Kỹ năng cần có" khớp từ điển.
Sau này thay bằng silver.job_skills (WM2) khi có.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from service.skills import SkillCatalog

TEXT_FIELDS = ("title", "description", "requirements_text")


def build(rows: list[dict], catalog: SkillCatalog) -> dict[str, list[str]]:
    index = {}
    for r in rows:
        ids = catalog.skill_ids("\n".join(str(r.get(f) or "") for f in TEXT_FIELDS))
        tags = r.get("skill_tags")
        for tag in [] if tags is None else tags:
            skill = catalog.lookup(str(tag).strip())
            if skill:
                ids.add(skill.skill_id)
        if ids:
            index[r["job_uid"]] = sorted(ids)
    return index


def main() -> None:
    import pandas as pd

    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=Path, default=Path("data/crawl/topcv/topcv_v1.parquet"))
    ap.add_argument("--out", type=Path, default=Path("data/index/job_skills.json"))
    args = ap.parse_args()
    rows = pd.read_parquet(args.jobs).to_dict("records")
    index = build(rows, SkillCatalog())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"snapshot": args.jobs.stem, "jobs": index}
    args.out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"{len(index)}/{len(rows)} tin có kỹ năng → {args.out}")


if __name__ == "__main__":
    main()
