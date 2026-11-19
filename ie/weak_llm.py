"""Nhãn yếu v5 cho WM2: file v3, thay nhãn câu VietJobs bằng nhãn LLM (ie/llm_label.py).

    uv run python -m ie.weak_llm --llm data/llm/train_luna.bio.jsonl

Câu TopCV giữ nhãn v3 (không được gửi ra API). Câu VietJobs mà LLM chưa gán (dừng vì ngân sách, lỗi) giữ nhãn v3
và được đếm. Theo mục đăng ký trước "Kết quả bước thử nhãn LLM trên dev" trong `experiments/results.md`.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

WEAK_DIR = Path(__file__).resolve().parents[1] / "data" / "weak"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", type=Path, required=True)
    ap.add_argument("--src", type=Path, default=WEAK_DIR / "wm2_weak_v3.bio.jsonl")
    ap.add_argument("--out", type=Path, default=WEAK_DIR / "wm2_weak_v5.bio.jsonl")
    args = ap.parse_args()

    llm = {r["id"]: r for r in map(json.loads, args.llm.read_text("utf-8").splitlines())}
    n = Counter()
    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for line in args.src.read_text("utf-8").splitlines():
            r = json.loads(line)
            new = llm.get(r["id"])
            if new is not None:
                assert new["tokens"] == r["tokens"], r["id"]
                r = {**r, "tags": new["tags"]}
                n["llm"] += 1
            else:
                n[f"v3_{r['source']}"] += 1
            n["pos"] += "B-SKILL" in r["tags"]
            n["span"] += r["tags"].count("B-SKILL")
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"v5: {dict(n)} → {args.out}")


if __name__ == "__main__":
    main()
