"""Rút mẫu câu từ tập IT để gán nhãn kỹ năng (WM2) – tập vàng do người gán, dùng làm dev/test.

Cách chạy (cần data/vietjobs/it_v1.parquet – xem ie/vietjobs.py):
    uv run python -m annotation.sample_skill_batch --sentences 1500

Ghi ra data/annotation/ (đã gitignore – KHÔNG commit):
    skill_batch1.labelstudio.json   nhập vào Label Studio (cấu hình nhãn: annotation/label_studio_skill.xml)
    skill_batch1.manifest.json      seed, snapshot, danh sách job_uid đã rút – để không rút lại tin cũ ở đợt sau

Lấy cả tin, không lấy câu lẻ: tin bị rút thì mọi câu của tin đều vào tập gán nhãn, tránh rò rỉ khi chia train/test.
10% số tin đầu tiên được đánh dấu double=true để hai người cùng gán và đo Cohen's κ.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "vietjobs" / "it_v1.parquet"
OUT_DIR = ROOT / "data" / "annotation"
SECTIONS = {"description": "desc", "requirements_text": "req"}

BULLET_RE = re.compile(r"^\s*(?:[-•*+–>]|\d+[.)])\s*")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+84|0)(?:[\s.-]?\d){8,10}")
MIN_WORDS = 3
MAX_WORDS = 80


def mask_pii(text: str) -> str:
    """Che email, số điện thoại nếu nhà tuyển dụng ghi trong mô tả."""
    return PHONE_RE.sub("<PHONE>", EMAIL_RE.sub("<EMAIL>", text))


def split_sentences(text: str | None) -> list[str]:
    """Mô tả VietJobs thường là gạch đầu dòng: mỗi dòng một câu; dòng quá dài thì tách thêm theo dấu chấm."""
    if not isinstance(text, str):
        return []
    out = []
    for line in text.splitlines():
        line = BULLET_RE.sub("", line).strip()
        parts = re.split(r"(?<=[.;!?])\s+(?=[A-ZÀ-Ỹ])", line) if len(line.split()) > MAX_WORDS else [line]
        out += [p.strip() for p in parts if len(p.split()) >= MIN_WORDS]
    return out


def sample(
    df: pd.DataFrame, target: int, seed: int, exclude: set[str], max_per_posting: int | None = None
) -> tuple[list[dict], list[str]]:
    """Rút theo tin. max_per_posting: lấy ngẫu nhiên tối đa N câu mỗi tin (giữ thứ tự) để trải ra nhiều tin hơn."""
    rng = random.Random(seed)
    uids = sorted(set(df["job_uid"]) - exclude)
    rng.shuffle(uids)
    by_uid = df.set_index("job_uid")
    tasks, picked = [], []
    for uid in uids:
        if len(tasks) >= target:
            break
        row = by_uid.loc[uid]
        picked.append(uid)
        sents = [(tag, i, s) for col, tag in SECTIONS.items() for i, s in enumerate(split_sentences(row[col]))]
        if max_per_posting and len(sents) > max_per_posting:
            keep = set(rng.sample(range(len(sents)), max_per_posting))
            sents = [x for k, x in enumerate(sents) if k in keep]
        for tag, i, sent in sents:
            tasks.append({"id": f"{uid[:12]}-{tag}{i:02d}", "job_uid": uid, "section": tag, "text": mask_pii(sent)})
    double = set(picked[: max(1, len(picked) // 10)])
    for t in tasks:
        t["double"] = t["job_uid"] in double
    return tasks, picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    ap.add_argument("--sentences", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=20261007)
    ap.add_argument("--batch", default="skill_batch1")
    ap.add_argument("--exclude", type=Path, nargs="*", default=[], help="manifest các đợt trước")
    ap.add_argument("--max-per-posting", type=int, default=None, help="tối đa N câu mỗi tin (tập test: 8)")
    args = ap.parse_args()

    df = pd.read_parquet(args.snapshot)
    exclude = set()
    for m in args.exclude:
        exclude |= set(json.loads(m.read_text("utf-8"))["job_uids"])
    tasks, picked = sample(df, args.sentences, args.seed, exclude, args.max_per_posting)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{args.batch}.labelstudio.json").write_text(
        json.dumps([{"data": t} for t in tasks], ensure_ascii=False, indent=1), "utf-8"
    )
    manifest = {
        "batch": args.batch,
        "snapshot": args.snapshot.stem,
        "seed": args.seed,
        "max_per_posting": args.max_per_posting,
        "sentences": len(tasks),
        "postings": len(picked),
        "double_postings": sum(1 for u in picked[: max(1, len(picked) // 10)]),
        "double_sentences": sum(t["double"] for t in tasks),
        "job_uids": picked,
    }
    (OUT_DIR / f"{args.batch}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    print({k: v for k, v in manifest.items() if k != "job_uids"})


if __name__ == "__main__":
    main()
