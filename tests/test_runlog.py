"""Kiểm tra ghi và gộp file kết quả JSON (experiments/runlog.py, experiments/aggregate.py)."""

import json

import pytest

from experiments.aggregate import load, table
from experiments.runlog import bootstrap_ci, ids_sha256, save_run


def test_ids_sha256_order_independent():
    assert ids_sha256([3, 1, 2]) == ids_sha256(["1", "2", "3"])


def test_bootstrap_ci_brackets_mean():
    data = [0, 1] * 50
    lo, hi = bootstrap_ci(len(data), lambda ix: sum(data[i] for i in ix) / len(ix))
    assert lo < 0.5 < hi


def test_save_run_rejects_unknown_metric(tmp_path):
    with pytest.raises(ValueError):
        save_run(task="WM2", method="m", eval_set="e", split="dev", metrics={"acc": 1.0}, ids=[1], out_dir=tmp_path)


def test_save_and_aggregate_seeds(tmp_path):
    for seed, f1 in [(1, 0.70), (2, 0.74)]:
        save_run(
            task="WM2",
            method="phobert",
            eval_set="skill_test1",
            split="test",
            metrics={"f1": f1},
            ids=[1, 2, 3],
            seed=seed,
            out_dir=tmp_path,
        )
    p = save_run(
        task="WM2",
        method="dict",
        eval_set="skill_test1",
        split="test",
        metrics={"f1": 0.5},
        ids=[1, 2, 3],
        ci95={"f1": [0.45, 0.55]},
        out_dir=tmp_path,
    )
    rec = json.loads(p.read_text(encoding="utf-8"))
    assert rec["data"]["n_items"] == 3 and "sentence" not in json.dumps(rec)
    out = table(load(tmp_path))
    assert "0.720 ± 0.028" in out
    assert "[0.450, 0.550]" in out
