"""Gộp experiments/runs/*.json thành bảng Markdown (mỗi bài một bảng, nhiều seed → TB ± ĐLC).

uv run python -m experiments.aggregate              # in ra màn hình
uv run python -m experiments.aggregate --task WM2   # chỉ một bài
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from experiments.runlog import RUNS_DIR


def load(runs_dir: Path = RUNS_DIR) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(runs_dir.glob("*.json"))]


def _fmt(vals: list[float]) -> str:
    if len(vals) == 1:
        return f"{vals[0]:.3f}"
    return f"{statistics.mean(vals):.3f} ± {statistics.stdev(vals):.3f}"


def table(runs: list[dict]) -> str:
    """Một bài → một bảng; gộp các run cùng (phương pháp, tập, split) qua các seed."""
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in runs:
        groups[(r["method"], r["data"]["eval_set"], r["data"]["split"])].append(r)
    metric_names = sorted({m for r in runs for m in r["metrics"]})
    head = ["Phương pháp", "Tập", "n", "Seed", *metric_names, "CI95 (F1)", "Commit"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for (method, eval_set, split), rs in sorted(groups.items()):
        rs.sort(key=lambda r: r["seed"])
        cells = [
            method,
            f"{eval_set} ({split})",
            str(rs[-1]["data"]["n_items"]),
            ",".join(str(r["seed"]) for r in rs),
        ]
        for m in metric_names:
            vals = [r["metrics"][m] for r in rs if m in r["metrics"]]
            cells.append(_fmt(vals) if vals else "")
        ci = rs[0].get("ci95", {}).get("f1") if len(rs) == 1 else None
        cells.append(f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci else "")
        cells.append(", ".join(sorted({str(r["repro"]["git_commit"]) for r in rs})))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task")
    ap.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    args = ap.parse_args()
    by_task: dict[str, list[dict]] = defaultdict(list)
    for r in load(args.runs_dir):
        if not args.task or r["task"] == args.task:
            by_task[r["task"]].append(r)
    for task, runs in sorted(by_task.items()):
        print(f"### {task}\n\n{table(runs)}\n")


if __name__ == "__main__":
    main()
