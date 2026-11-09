"""Ghi file kết quả JSON theo experiments/FORMAT-ket-qua.md (phần A).

    from experiments.runlog import save_run, ids_sha256, bootstrap_ci
    save_run(task="WM2", method="dict-alias-v0", eval_set="skill_batch1", split="dev",
             metrics={"precision": 0.87, "recall": 0.36, "f1": 0.51}, ids=[...], command="uv run ...")

Chỉ ghi số, không ghi câu văn hay dữ liệu gốc.
"""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

RUNS_DIR = Path(__file__).resolve().parent / "runs"

# Tên metric cố định theo bài (FORMAT-ket-qua.md); metric lạ bị từ chối để script gộp không phải đoán.
METRICS: dict[str, set[str]] = {
    "CRAWL": {"pii_recall", "http_429", "http_403", "schema_valid_rate"},
    "WM1": {"precision", "recall", "f1", "blocking_recall", "dup_rate"},
    "WM2": {"precision", "recall", "f1", "f1_partial", "novel_skill_rate", "norm_acc"},
    "WM3": {"aspect_f1_micro", "aspect_f1_macro", "sentiment_f1_macro", "spearman_stars"},
    "WM5": {"ndcg@10", "recall@10", "coverage", "explained_rate"},
    "WM6": {"modularity", "modularity_random_mean", "kendall_tau_pr_freq", "n_communities"},
    "WM4": {"ndcg@10", "mrr"},
    "KAPPA": {"kappa"},
    "SERVICE": {"p95_latency_ms", "contract_pass_rate"},
}


def ids_sha256(ids: Sequence[Any]) -> str:
    return hashlib.sha256("\n".join(sorted(map(str, ids))).encode()).hexdigest()


def bootstrap_ci(n: int, stat: Callable[[list[int]], float], b: int = 1000, seed: int = 0) -> list[float]:
    """Khoảng tin cậy 95% bằng bootstrap: lấy lại n chỉ số mẫu có hoàn lại, tính stat trên từng lần."""
    rng = random.Random(seed)
    vals = sorted(float(stat([rng.randrange(n) for _ in range(n)])) for _ in range(b))
    return [round(vals[int(0.025 * b)], 4), round(vals[int(0.975 * b) - 1], 4)]


def _git_commit() -> str | None:
    try:
        root = Path(__file__).resolve().parent.parent
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=root).returncode != 0
        return sha + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def save_run(
    *,
    task: str,
    method: str,
    eval_set: str,
    split: str,
    metrics: dict[str, float],
    ids: Sequence[Any],
    command: str | None = None,
    seed: int = 0,
    rq: str | None = None,
    baseline_of: str | None = None,
    snapshot: str | None = None,
    n_gold: int | None = None,
    ci95: dict[str, list[float]] | None = None,
    train: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
    models_yaml: str | None = None,
    out_dir: Path = RUNS_DIR,
) -> Path:
    unknown = set(metrics) - METRICS.get(task, set())
    if unknown and not all(k.startswith("field_acc_") for k in unknown):
        raise ValueError(f"metric không có trong danh sách cố định của {task}: {sorted(unknown)}")
    commit = _git_commit()
    if split == "test" and (commit is None or commit.endswith("-dirty")):
        print("CẢNH BÁO: chạy trên test mà repo chưa commit sạch – số này không tái lập được", file=sys.stderr)

    now = datetime.now().astimezone()
    run_id = f"{now:%Y-%m-%d}-{task.lower()}-{method}-{split}-s{seed}"
    record = {
        "run_id": run_id,
        "task": task,
        "rq": rq,
        "method": method,
        "baseline_of": baseline_of,
        "data": {
            "eval_set": eval_set,
            "split": split,
            "snapshot": snapshot,
            "ids_sha256": ids_sha256(ids),
            "n_items": len(ids),
            "n_gold": n_gold,
        },
        "train": train,
        "seed": seed,
        "metrics": {k: round(v, 4) for k, v in metrics.items()},
        "ci95": ci95 or {},
        "runtime": runtime or {},
        "repro": {"command": command or " ".join(sys.argv), "git_commit": commit, "models_yaml": models_yaml},
        "created_at": now.isoformat(timespec="seconds"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
