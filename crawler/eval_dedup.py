"""WM1 – chấm baseline và MinHash trên tập 300 cặp đã gán (Label Studio project dedup).

    uv run python -m crawler.eval_dedup --from-ls 10        # kéo nhãn từ Label Studio, lưu file rồi chấm
    uv run python -m crawler.eval_dedup                     # chấm lại từ file nhãn đã lưu

Nhãn lưu ở data/annotation/dedup_batch1.labels.jsonl (không commit). Snapshot lấy từ manifest.

**Hai cách tính, vì mẫu rút theo tầng chứ không ngẫu nhiên:**
- *Trên tập nhãn*: P/R/F1 coi 300 cặp là tập đánh giá. Đây là con số đã hứa ("P/R/F1 trên cặp"),
  nhưng tập này cố ý dồn cặp khó nên không phản ánh tỉ lệ trên toàn bộ cặp.
- *Ước lượng có trọng số*: mỗi cặp nhân `cỡ tầng / số cặp rút từ tầng`; cặp ngoài mọi tầng (khác công ty
  và Jaccard < 0,2) coi là không trùng. Ước lượng cho toàn bộ tin, xấp xỉ vì trong tầng có giới hạn lặp.

Ngưỡng MinHash **0,5 đặt trước** (mặc định của `crawler.dedup`), không chọn trên tập này. Bảng quét ngưỡng
chỉ để đọc xu hướng; ngưỡng tốt nhất trên bảng đó là số lạc quan.

v2 (đăng ký trước 2026-11-18): baseline mềm ∪ MinHash cắt khung công ty, so với v1 bằng bootstrap ghép cặp.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from annotation.sample_dedup_pairs import STRATA, build_strata
from crawler.dedup import baseline_pairs, minhash_of, shingle_sets
from experiments.bootstrap import ci, sentence_indices

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data" / "annotation"
LABELS = ANN / "dedup_batch1.labels.jsonl"
MANIFEST = ANN / "dedup_batch1.manifest.json"
THRESHOLD = 0.5
SWEEP = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)


def pull(project: int) -> list[dict]:
    """Nhãn từ Label Studio, mỗi cặp một dòng."""
    from annotation.preannotate_dict import TOKEN_FILE, LabelStudio

    ls = LabelStudio("http://localhost:8080", TOKEN_FILE.read_text().strip())
    out = []
    for t in ls._call("GET", f"/api/projects/{project}/export?exportType=JSON"):
        res = t["annotations"][0]["result"] if t.get("annotations") else []
        dup = [r["value"]["choices"][0] for r in res if r["from_name"] == "dup"]
        if not dup:
            continue
        com = [r["value"]["text"][0] for r in res if r["from_name"] == "comment"]
        d = t["data"]
        out.append(
            {
                "index": d["index"],
                "a": d["job_uid_a"],
                "b": d["job_uid_b"],
                "dup": dup[0] == "trùng",
                "hard": any(r["from_name"] == "flag" for r in res),
                "comment": com[0] if com else "",
            }
        )
    return out


def prf(gold: list[bool], pred: list[bool], w: list[float] | None = None) -> tuple[float, float, float]:
    """Precision / recall / F1 của lớp "trùng", có thể kèm trọng số mỗi cặp."""
    w = w or [1.0] * len(gold)
    tp = sum(x for g, p, x in zip(gold, pred, w, strict=True) if g and p)
    fp = sum(x for g, p, x in zip(gold, pred, w, strict=True) if not g and p)
    fn = sum(x for g, p, x in zip(gold, pred, w, strict=True) if g and not p)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def load(rows: list[dict]) -> tuple[list[dict], pd.DataFrame, dict[str, int]]:
    man = json.loads(MANIFEST.read_text("utf-8"))
    for r in rows:
        p = man["pairs"][r["index"]]
        assert (p["a"], p["b"]) == (r["a"], r["b"]), "nhãn không khớp manifest"
        r["stratum"] = p["stratum"]
    df = pd.concat([pd.read_parquet(ROOT / s) for s in man["snapshots"]], ignore_index=True)
    df = df.drop_duplicates("job_uid")
    src = dict(zip(df["job_uid"], df["source"], strict=True))
    base, base_soft = baseline_pairs(df), baseline_pairs(df, soft=True)
    full, cut = shingle_sets(df), shingle_sets(df, strip=True)
    mh: dict = {}

    def j(sets: dict, tag: str, a: str, b: str) -> float:
        for u in (a, b):
            if (tag, u) not in mh:
                mh[(tag, u)] = minhash_of(sets[u])
        return float(mh[(tag, a)].jaccard(mh[(tag, b)]))

    for r in rows:
        key = tuple(sorted((r["a"], r["b"])))
        r["jaccard"] = j(full, "full", r["a"], r["b"])
        r["jaccard_cut"] = j(cut, "cut", r["a"], r["b"])
        r["cross"] = src[r["a"]] != src[r["b"]]
        r["baseline"] = key in base
        r["baseline_soft"] = key in base_soft
    pools = {k: len(v) for k, v in build_strata(df).items()}
    return rows, df.set_index("job_uid"), pools


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-ls", type=int, metavar="PROJECT", help="kéo nhãn từ Label Studio trước khi chấm")
    ap.add_argument("--show", type=int, default=15, help="số cặp lỗi in ra mỗi loại")
    ap.add_argument(
        "--labels",
        type=Path,
        default=LABELS,
        help="file nhãn (mặc định guideline 0.1; 0.2: dedup_batch1.labels_v02.jsonl)",
    )
    args = ap.parse_args()

    if args.from_ls:
        pulled = pull(args.from_ls)
        LABELS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in pulled), "utf-8")
        print(f"lưu {len(pulled)} nhãn -> {LABELS.relative_to(ROOT)}")
    print(f"nhãn: {args.labels.name}")
    raw = [json.loads(x) for x in args.labels.read_text("utf-8").splitlines() if x.strip()]
    rows, info, pools = load(raw)
    n_by = Counter(r["stratum"] for r in rows)
    weight = [pools[r["stratum"]] / n_by[r["stratum"]] for r in rows]
    gold = [r["dup"] for r in rows]

    n_cross_dup = sum(r["dup"] and r["cross"] for r in rows)
    print(f"\n{len(rows)} cặp, {sum(gold)} trùng ({n_cross_dup} khác trang); {sum(r['hard'] for r in rows)} tick 'khó'")
    print("\n| Tầng | cỡ tầng | rút | trùng |")
    print("|---|---|---|---|")
    for s in STRATA:
        print(f"| {s} | {pools.get(s, 0)} | {n_by[s]} | {sum(r['dup'] for r in rows if r['stratum'] == s)} |")

    v1 = f"v1: baseline ∪ MinHash ≥ {THRESHOLD}"
    main_name = f"v2: baseline mềm ∪ MinHash cắt khung ≥ {THRESHOLD}"
    systems = {
        "baseline title+company": [r["baseline"] for r in rows],
        f"MinHash J ≥ {THRESHOLD}": [r["jaccard"] >= THRESHOLD for r in rows],
        v1: [r["baseline"] or r["jaccard"] >= THRESHOLD for r in rows],
        "baseline mềm": [r["baseline_soft"] for r in rows],
        f"MinHash cắt khung ≥ {THRESHOLD}": [r["jaccard_cut"] >= THRESHOLD for r in rows],
        main_name: [r["baseline_soft"] or r["jaccard_cut"] >= THRESHOLD for r in rows],
    }
    idx = list(sentence_indices(len(rows), 2000, 0))  # bootstrap theo cặp, dùng lại cho mọi hệ
    print("\n| Hệ | P | R | F1 | F1 CI95 | P / R / F1 có trọng số |")
    print("|---|---|---|---|---|---|")
    for name, pred in systems.items():
        p, r_, f = prf(gold, pred)
        lo, hi, _ = ci([prf([gold[i] for i in ix], [pred[i] for i in ix])[2] for ix in idx])
        wp, wr, wf = prf(gold, pred, weight)
        print(f"| {name} | {p:.3f} | {r_:.3f} | {f:.3f} | [{lo:.3f}; {hi:.3f}] | {wp:.3f} / {wr:.3f} / {wf:.3f} |")

    a, b = systems[main_name], systems[v1]
    d = [
        prf([gold[i] for i in ix], [a[i] for i in ix])[2] - prf([gold[i] for i in ix], [b[i] for i in ix])[2]
        for ix in idx
    ]
    lo, hi, p0 = ci(d)
    print(f"\nΔF1 v2 − v1 = {prf(gold, a)[2] - prf(gold, b)[2]:+.3f}, CI95 [{lo:+.3f}; {hi:+.3f}], p(Δ≤0) {p0:.3f}")

    print("\nQuét ngưỡng MinHash (chỉ đọc xu hướng, không dùng để chọn ngưỡng báo cáo):")
    print("| J ≥ | P | R | F1 | số cặp báo trùng |")
    print("|---|---|---|---|---|")
    for t in SWEEP:
        pred = [r["jaccard"] >= t for r in rows]
        p, r_, f = prf(gold, pred)
        print(f"| {t:.1f} | {p:.3f} | {r_:.3f} | {f:.3f} | {sum(pred)} |")

    pred = systems[main_name]
    for cross in (True, False):
        sub = [i for i, r in enumerate(rows) if r["cross"] == cross]
        p, r_, f = prf([gold[i] for i in sub], [pred[i] for i in sub])
        label = "khác trang" if cross else "cùng trang"
        print(
            f"{label}: {len(sub)} cặp, {sum(gold[i] for i in sub)} trùng; {main_name}: P {p:.3f} R {r_:.3f} F1 {f:.3f}"
        )

    kinds = (
        ("Bỏ sót (trùng, hệ không bắt)", lambda g, p: g and not p),
        ("Báo nhầm (không trùng, hệ báo trùng)", lambda g, p: p and not g),
    )
    for kind, cond in kinds:
        err = [r for r, g, p in zip(rows, gold, pred, strict=True) if cond(g, p)]
        err.sort(key=lambda r: -r["jaccard"])
        print(f"\n{kind}: {len(err)}")
        for r in err[: args.show]:
            where = "khác trang" if r["cross"] else "cùng trang"
            extra = (" [khó]" if r["hard"] else "") + (f" – {r['comment']}" if r["comment"] else "")
            ta, tb, ca = info.at[r["a"], "title"], info.at[r["b"], "title"], info.at[r["a"], "company_name"]
            print(f"  J={r['jaccard']:.2f} J_cắt={r['jaccard_cut']:.2f} {where} | {ca} | {ta} || {tb}{extra}")


if __name__ == "__main__":
    main()
