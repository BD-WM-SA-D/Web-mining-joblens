"""Đo độ trễ trích kỹ năng của mining-service ở chế độ PhoBERT trên CPU (yêu cầu ADR 0002: p95 ≤ 3 giây).

    uv run python -m service.bench --model data/models/skill-extractor --n 100 --threads 2

Đầu vào giả lập văn bản người dùng dán vào app: mô tả + yêu cầu của các tin trong snapshot (độ dài gần một CV
ngắn). Đo trọn lời gọi `/v1/skills:extract` qua TestClient, gồm tách từ, PhoBERT và tra từ điển; không tính lần
nạp model. Không in văn bản đầu vào.
"""

from __future__ import annotations

import argparse
import os
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=ROOT / "data" / "models" / "skill-extractor")
    ap.add_argument("--snapshot", type=Path, default=ROOT / "data" / "crawl" / "topcv" / "topcv_20261118.parquet")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()

    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["JOBLENS_MINING_SKILL_MODEL"] = str(args.model)
    import pandas as pd
    import torch
    from fastapi.testclient import TestClient

    torch.set_num_threads(args.threads)
    import service.app as svc

    df = pd.read_parquet(args.snapshot).head(args.n)
    texts = [
        "\n".join(str(r.get(c) or "") for c in ("description", "requirements_text", "requirements"))[:20000]
        for r in df.to_dict("records")
    ]
    client = TestClient(svc.app)
    client.post("/v1/skills:extract", json={"text": texts[0]})  # khởi động (tách từ, cache)
    times, n_skills = [], 0
    for t in texts:
        s = time.perf_counter()
        r = client.post("/v1/skills:extract", json={"text": t})
        times.append(time.perf_counter() - s)
        n_skills += len(r.json()["skills"])
    times.sort()
    p95 = times[int(0.95 * (len(times) - 1))]
    print(
        f"{len(texts)} văn bản (TB {statistics.mean(map(len, texts)):.0f} ký tự), {args.threads} luồng CPU, "
        f"{svc.MODEL_VERSION}: p50 {statistics.median(times):.2f}s, p95 {p95:.2f}s, max {times[-1]:.2f}s; "
        f"{n_skills / len(texts):.1f} kỹ năng/văn bản"
    )


if __name__ == "__main__":
    main()
