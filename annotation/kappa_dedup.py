"""WM1 – Cohen's κ giữa hai người gán cặp tin trùng.

Bước 1, rút lô cho người thứ hai (30 cặp lấy từ 300 cặp người thứ nhất đã gán):

    uv run python -m annotation.kappa_dedup sample
    uv run python -m annotation.make_ls_project --title "WM1 dedup - κ (người 2)" \\
        --config annotation/label_studio_dedup.xml --tasks data/annotation/dedup_kappa1.labelstudio.json

Bước 2, sau khi người thứ hai gán xong (project id xem trên URL Label Studio):

    uv run python -m annotation.kappa_dedup score --from-ls <project>

**Lô κ được làm giàu cặp trùng, có chủ đích.** 300 cặp chỉ có 15 cặp trùng (5%). Rút ngẫu nhiên 30 cặp thì
trung bình chỉ được 1–2 cặp trùng, κ gần như không xác định. Nên lô gồm: mọi cặp người 1 gán "trùng", mọi cặp
tick "khó", phần còn lại rút ngẫu nhiên trong cặp "không trùng" (chia theo tầng). Hệ quả cần báo cáo: κ này
đo đồng thuận **trên tập đã làm giàu**, không phải trên phân bố của 300 cặp. Người thứ hai không được biết
tỉ lệ này, cũng không thấy nhãn người 1 (task không chứa nhãn, project riêng).

Bước 3, rà lại theo guideline mới (sau khi κ lộ ra 4 kiểu lệch):

    uv run python -m annotation.kappa_dedup recheck
    uv run python -m annotation.make_ls_project --title "WM1 dedup - rà lại" \
        --config annotation/label_studio_dedup.xml --tasks data/annotation/dedup_recheck02.labelstudio.json
    uv run python -m annotation.kappa_dedup merge --from-ls <project>
    uv run python -m crawler.eval_dedup --labels data/annotation/dedup_batch1.relabeled.jsonl

Lô rà lại chọn theo **nhãn và nguồn, không theo dự đoán của hệ**: mọi cặp người 1 gán "trùng", mọi cặp tick
"khó", mọi cặp khác trang. Gán lại **mù** (project mới, không thấy nhãn cũ). Nhãn mới ghi đè nhãn cũ ở các
cặp đó; 253 cặp còn lại giữ nhãn cũ. Hạn chế: quy tắc 8 mới (tiêu đề khác → xét mô tả) có thể biến vài cặp
"không trùng" cùng trang thành "trùng"; các cặp đó không được rà lại vì muốn tìm chúng phải dựa vào độ giống
mô tả, tức là dựa vào chính thứ đang được chấm.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score
from common.io import read_jsonl

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data" / "annotation"
LABELS = ANN / "dedup_batch1.labels.jsonl"
TASKS = ANN / "dedup_batch1.labelstudio.json"
MANIFEST = ANN / "dedup_batch1.manifest.json"
OUT = ANN / "dedup_kappa1"
N = 30
SEED = 20261118


def select(rows: list[dict], strata: dict[int, str], n: int, seed: int) -> list[dict]:
    """Mọi cặp trùng + mọi cặp "khó", bù đủ n bằng cặp không trùng rút theo tầng (xoay vòng các tầng)."""
    rng = random.Random(seed)
    must = [r for r in rows if r["dup"] or r["hard"]]
    rest_by: dict[str, list[dict]] = {}
    for r in rows:
        if not (r["dup"] or r["hard"]):
            rest_by.setdefault(strata[r["index"]], []).append(r)
    for v in rest_by.values():
        rng.shuffle(v)
    fill: list[dict] = []
    order = sorted(rest_by)
    while len(must) + len(fill) < n and any(rest_by.values()):
        for s in order:
            if rest_by[s] and len(must) + len(fill) < n:
                fill.append(rest_by[s].pop())
    out = must + fill
    rng.shuffle(out)
    return out


def cmd_sample(_: argparse.Namespace) -> None:
    rows = read_jsonl(LABELS)
    man = json.loads(MANIFEST.read_text("utf-8"))
    strata = {i: p["stratum"] for i, p in enumerate(man["pairs"])}
    picked = select(rows, strata, N, SEED)
    by_index = {t["data"]["index"]: t for t in json.loads(TASKS.read_text("utf-8"))}
    tasks = [by_index[r["index"]] for r in picked]  # cùng dữ liệu cặp, không có nhãn người 1
    OUT.with_suffix(".labelstudio.json").write_text(json.dumps(tasks, ensure_ascii=False, indent=1), "utf-8")
    meta = {
        "seed": SEED,
        "from": "dedup_batch1",
        "n": len(picked),
        "person1_dup": sum(r["dup"] for r in picked),
        "person1_hard": sum(r["hard"] for r in picked),
        "by_stratum": Counter(strata[r["index"]] for r in picked),
        "indices": [r["index"] for r in picked],
    }
    OUT.with_suffix(".manifest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    print({k: v for k, v in meta.items() if k != "indices"})
    print(f"-> {OUT.with_suffix('.labelstudio.json').relative_to(ROOT)}")


def cmd_score(args: argparse.Namespace) -> None:
    from crawler.eval_dedup import pull

    p1 = {(r["a"], r["b"]): r for r in (json.loads(x) for x in LABELS.read_text("utf-8").splitlines() if x.strip())}
    p2 = {(r["a"], r["b"]): r for r in pull(args.from_ls)}
    keys = [k for k in p2 if k in p1]
    if not keys:
        raise SystemExit("không có cặp chung giữa hai người")
    a = [p1[k]["dup"] for k in keys]
    b = [p2[k]["dup"] for k in keys]
    k = cohen_kappa_score(a, b)
    rng = np.random.default_rng(0)
    boot = []
    for _ in range(2000):
        ix = rng.integers(0, len(keys), size=len(keys))
        aa, bb = [a[i] for i in ix], [b[i] for i in ix]
        if len(set(aa) | set(bb)) > 1:
            boot.append(cohen_kappa_score(aa, bb))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    agree = sum(x == y for x, y in zip(a, b, strict=True))
    print(f"{len(keys)} cặp chung; người 1 trùng {sum(a)}, người 2 trùng {sum(b)}; khớp {agree}/{len(keys)}")
    print(f"κ = {k:.3f}, CI95 bootstrap theo cặp [{lo:.3f}; {hi:.3f}] (trên lô đã làm giàu cặp trùng)")
    diff = [key for key, x, y in zip(keys, a, b, strict=True) if x != y]
    print(f"\n{len(diff)} cặp lệch:")
    for key in diff:
        r1, r2 = p1[key], p2[key]
        lab = lambda r: "trùng" if r["dup"] else "không trùng"  # noqa: E731
        note = f" – người 2: {r2['comment']}" if r2["comment"] else ""
        print(f"  index {r1['index']}: người 1 {lab(r1)}, người 2 {lab(r2)}{note}")


RECHECK = ANN / "dedup_recheck02.labelstudio.json"
LABELS_RELABELED = ANN / "dedup_batch1.relabeled.jsonl"


def recheck_indices(rows: list[dict], tasks: dict[int, dict]) -> list[int]:
    """Cặp phải rà lại theo guideline mới: nhãn "trùng", tick "khó", hoặc khác trang."""
    out = []
    for r in rows:
        d = tasks[r["index"]]["data"]
        if r["dup"] or r["hard"] or d["source_a"] != d["source_b"]:
            out.append(r["index"])
    return out


def cmd_recheck(_: argparse.Namespace) -> None:
    rows = read_jsonl(LABELS)
    tasks = {t["data"]["index"]: t for t in json.loads(TASKS.read_text("utf-8"))}
    sel = recheck_indices(rows, tasks)
    random.Random(SEED).shuffle(sel)
    RECHECK.write_text(json.dumps([tasks[i] for i in sel], ensure_ascii=False, indent=1), "utf-8")
    print(f"{len(sel)} cặp -> {RECHECK.relative_to(ROOT)}")


def cmd_merge(args: argparse.Namespace) -> None:
    from crawler.eval_dedup import pull

    rows = read_jsonl(LABELS)
    new = {r["index"]: r for r in pull(args.from_ls)}
    changed = [
        (r["index"], r["dup"], new[r["index"]]["dup"])
        for r in rows
        if r["index"] in new and r["dup"] != new[r["index"]]["dup"]
    ]
    merged = [dict(new[r["index"]], relabeled=True) if r["index"] in new else dict(r, relabeled=False) for r in rows]
    LABELS_RELABELED.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in merged), "utf-8")
    print(
        f"rà lại {len(new)} cặp, đổi nhãn {len(changed)}: trùng {sum(r['dup'] for r in rows)} -> {sum(r['dup'] for r in merged)}"
    )
    for i, old, now in changed:
        print(f"  index {i}: {'trùng' if old else 'không trùng'} -> {'trùng' if now else 'không trùng'}")
    print(f"-> {LABELS_RELABELED.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sample").set_defaults(fn=cmd_sample)
    sc = sub.add_parser("score")
    sc.add_argument("--from-ls", type=int, required=True, metavar="PROJECT")
    sc.set_defaults(fn=cmd_score)
    sub.add_parser("recheck").set_defaults(fn=cmd_recheck)
    mg = sub.add_parser("merge")
    mg.add_argument("--from-ls", type=int, required=True, metavar="PROJECT")
    mg.set_defaults(fn=cmd_merge)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
