"""WM3 – đối chiếu đầu ra ABSA với điểm sao của ITviec (phép đo không cần nhãn người).

    uv run python -m absa.company_eval
    uv run python -m absa.company_eval --b 2000 --out data/eval/wm3_stars.json

**Vì sao cần phép đo này.** Trên tập gán tay mức câu, một luật một dòng theo trường `section`
("Đề nghị cải thiện" → chê, "Điều tôi thích" → khen) được 0,583 trên TEST, gần bằng mô hình lai
(0,590, p = 0,264). Phép đo mức câu đó là phép đo mà `section` gần như luôn thắng, vì nó dự đoán
cùng một đáp án cho mọi review. Hai điểm yếu nữa: người gán **nhìn thấy** `section` trên Label
Studio, và văn bản công khai của ITviec không có review 1–2 sao nào.

Điểm sao thì không có hai điểm yếu đó:

- Nó **không do người gán tạo ra** → không rò rỉ được từ guideline hay từ `section`.
- Mỗi review có điểm sao **riêng cho từng khía cạnh**; 75% review có sao khác nhau giữa các khía cạnh
  (sd trong review median 0,49). Luật `section` cho cùng một cực cho mọi khía cạnh của cùng một câu,
  nên nó **không thể** bắt được phần biến thiên này.
- Điểm sao của review **bị che** vẫn hiện: 1.100 bản ghi, 23–32% ô có sao ≤ 3. Đây là lời chê mà
  phần văn bản không có.

Hai mức đo:

1. **Mức review** – mỗi ô là (review, khía cạnh): điểm cực tính dự đoán từ văn bản so với **sao của
   chính review đó** cho khía cạnh đó.
2. **Mức công ty** – mỗi ô là (công ty, khía cạnh): dự đoán từ văn bản review công khai so với **sao
   trung bình của các review BỊ CHE** của công ty đó. Đích hoàn toàn nằm ngoài văn bản mà hệ nhìn thấy:
   đo xem một review có nói đúng về công ty theo đánh giá của những người khác không.

Số chính báo cáo trên **các review ngoài dev** (dev là nguồn train duy nhất của mô hình lai), kèm cột
"tất cả review" để tham khảo.

Hạn chế đã biết, phải ghi trong báo cáo:

- ITviec chỉ cho sao 5 khía cạnh. `work_life_balance` **không có sao** → phép đo này không nói gì về
  khía cạnh đó, trong khi đó lại là khía cạnh cả hai hệ làm tệ nhất.
- Sao là của **cả review**, không phải của từng câu; một review khen lương ở câu A và chê lương ở câu B
  chỉ có một con số. Đây là nhiễu đích, làm mọi tương quan thấp đi ở cả ba hệ như nhau.
- Tương quan không phải F1; nó trả lời "hệ có xếp đúng thứ tự hài lòng không", không trả lời "hệ gán
  đúng nhãn không". Hai phép đo bổ sung cho nhau, không thay nhau.
"""

from __future__ import annotations

from common.io import read_jsonl

import argparse
import json
from collections import defaultdict
from pathlib import Path

from absa.eval_dev import GOLD, SENTS
from absa.lexicon import VERSION as DICT_VERSION
from absa.lexicon import predict as dict_predict
from absa.score import as_dict
from absa.supervised import TEST_GOLD, fit_predict_hybrid, section_rule, splits
from experiments.runlog import bootstrap_ci, save_run

ROOT = Path(__file__).resolve().parents[1]
RATINGS = sorted((ROOT / "data" / "crawl" / "itviec").glob("*/review_ratings.jsonl"))
# ITviec chỉ chấm sao 5 khía cạnh; work_life_balance của guideline WM3 không có sao.
STAR_ASPECTS = ("salary_benefits", "training_learning", "management_care", "culture_fun", "office_workspace")
POL_SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


# ---------- dữ liệu ----------


def load_ratings() -> list[dict]:
    """Mọi bản ghi điểm sao, khử trùng theo (công ty, vị trí trên trang, tháng, sao tổng)."""
    seen, out = set(), []
    for p in RATINGS:
        for r in read_jsonl(p):
            key = (r["company_id"], r["position"], r.get("review_month"), r.get("rating_overall"))
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
    return out


def blurred_company_stars(ratings: list[dict]) -> dict[tuple[str, str], tuple[float, int]]:
    """(công ty, khía cạnh) → (sao trung bình, số review) tính CHỈ trên review bị che.

    Loại review có văn bản để đích không chứa chính review mà hệ đọc.
    """
    agg: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in ratings:
        if r.get("has_text"):
            continue
        for aspect, star in (r.get("aspect_ratings") or {}).items():
            if star is not None:
                agg[(r["company_id"], aspect)].append(float(star))
    return {k: (sum(v) / len(v), len(v)) for k, v in agg.items()}


def predictions(rows: list[dict], train_rows: list[dict], seed: int) -> dict[str, list[dict[str, str]]]:
    """Ba hệ, cùng một cách phát hiện khía cạnh (`match_aspects`) nên độ phủ ô bằng nhau."""
    return {
        f"từ điển {DICT_VERSION}": [as_dict(dict_predict(r["text"])) for r in rows],
        "luật phần review": section_rule(rows),
        "lai (từ điển + hồi quy logistic)": fit_predict_hybrid(train_rows, rows, seed=seed),
    }


def cells(rows: list[dict], pred: list[dict[str, str]], stars: dict, unit: str) -> list[dict]:
    """Gộp dự đoán theo (đơn vị, khía cạnh) rồi ghép với đích.

    unit = "review": đích là sao của chính review đó. unit = "company": đích là sao trung bình của
    các review bị che của công ty.
    """
    key = "source_review_id" if unit == "review" else "company_id"
    by: dict[tuple[str, str], list[float]] = defaultdict(list)
    meta: dict[str, dict] = {}
    for row, p in zip(rows, pred, strict=True):
        meta.setdefault(row[key], row)
        for aspect, polarity in p.items():
            if aspect in STAR_ASPECTS:
                by[(row[key], aspect)].append(POL_SCORE[polarity])
    out = []
    for (unit_id, aspect), scores in sorted(by.items()):
        if unit == "review":
            star = (meta[unit_id].get("aspect_ratings") or {}).get(aspect)
            n_target = 1
        else:
            got = stars.get((unit_id, aspect))
            star, n_target = (got[0], got[1]) if got else (None, 0)
        if star is None:
            continue
        out.append(
            {
                "unit": unit_id,
                "aspect": aspect,
                "pred": sum(scores) / len(scores),
                "n_sent": len(scores),
                "star": float(star),
                "n_target": n_target,
            }
        )
    return out


# ---------- thống kê ----------


def spearman(xs: list[float], ys: list[float]) -> float:
    from scipy.stats import spearmanr

    if len({round(x, 9) for x in xs}) < 2 or len({round(y, 9) for y in ys}) < 2:
        return float("nan")  # một bên là hằng số → tương quan không xác định
    return float(spearmanr(xs, ys).statistic)


def demeaned(cs: list[dict]) -> tuple[list[float], list[float]]:
    """Trừ trung bình theo khía cạnh ở cả hai phía: gộp các khía cạnh mà không để chênh lệch
    mức sao giữa các khía cạnh tạo ra tương quan giả."""
    mp: dict[str, list[float]] = defaultdict(list)
    ms: dict[str, list[float]] = defaultdict(list)
    for c in cs:
        mp[c["aspect"]].append(c["pred"])
        ms[c["aspect"]].append(c["star"])
    avg_p = {a: sum(v) / len(v) for a, v in mp.items()}
    avg_s = {a: sum(v) / len(v) for a, v in ms.items()}
    return (
        [c["pred"] - avg_p[c["aspect"]] for c in cs],
        [c["star"] - avg_s[c["aspect"]] for c in cs],
    )


def auc_low_star(cs: list[dict], threshold: float = 3.0) -> tuple[float, int]:
    """AUC khi dùng (−điểm cực tính) để phát hiện ô có sao ≤ ngưỡng."""
    from sklearn.metrics import roc_auc_score

    y = [1 if c["star"] <= threshold else 0 for c in cs]
    if len(set(y)) < 2:
        return float("nan"), sum(y)
    return float(roc_auc_score(y, [-c["pred"] for c in cs])), sum(y)


def by_unit(cs: list[dict]) -> list[list[int]]:
    """Nhóm chỉ số ô theo đơn vị, để bootstrap lấy lại theo review/công ty chứ không theo ô."""
    groups: dict[str, list[int]] = defaultdict(list)
    for i, c in enumerate(cs):
        groups[c["unit"]].append(i)
    return list(groups.values())


def evaluate(cs: list[dict], b: int, seed: int) -> dict:
    xs, ys = demeaned(cs)
    rho = spearman(xs, ys)
    auc, n_low = auc_low_star(cs)
    groups = by_unit(cs)

    def stat(idx: list[int]) -> float:
        sub = [cs[i] for g in idx for i in groups[g]]
        if len(sub) < 3:
            return 0.0
        v = spearman(*demeaned(sub))
        return 0.0 if v != v else v  # NaN (một bên hằng số) tính là 0

    ci = bootstrap_ci(len(groups), stat, b=b, seed=seed) if len(groups) > 2 else [float("nan")] * 2
    per_aspect = {}
    for aspect in STAR_ASPECTS:
        sub = [c for c in cs if c["aspect"] == aspect]
        per_aspect[aspect] = {
            "n": len(sub),
            "rho": spearman([c["pred"] for c in sub], [c["star"] for c in sub]) if len(sub) > 2 else float("nan"),
        }
    return {
        "n_cells": len(cs),
        "n_units": len(groups),
        "rho": rho,
        "ci95": ci,
        "auc_star_le_3": auc,
        "n_low_star": n_low,
        "n_distinct_pred": len({round(c["pred"], 6) for c in cs}),
        "neg_rate": sum(1 for c in cs if c["pred"] < 0) / len(cs),
        "per_aspect": per_aspect,
    }


def paired(cs_a: list[dict], cs_b: list[dict], b: int, seed: int) -> dict:
    """Δ Spearman giữa hai hệ, bootstrap ghép cặp theo đơn vị (cùng các review/công ty mỗi lần lấy lại).

    CI của từng hệ chồng nhau không trả lời được "hệ nào hơn"; chỉ kiểm định ghép cặp trả lời được.
    Hai hệ dùng cùng cách phát hiện khía cạnh nên tập ô trùng khít – ghép theo (đơn vị, khía cạnh).
    """
    key = lambda c: (c["unit"], c["aspect"])  # noqa: E731
    a = {key(c): c for c in cs_a}
    shared = [k for k in (key(c) for c in cs_b) if k in a]
    pa = [a[k] for k in shared]
    pb = [{**a[k], "pred": next(c["pred"] for c in cs_b if key(c) == k)} for k in shared]
    groups: dict[str, list[int]] = defaultdict(list)
    for i, k in enumerate(shared):
        groups[k[0]].append(i)
    gl = list(groups.values())

    def rho_of(rows: list[dict]) -> float:
        v = spearman(*demeaned(rows))
        return 0.0 if v != v else v

    delta = rho_of(pa) - rho_of(pb)
    import random as _random

    rng = _random.Random(seed)
    diffs = []
    for _ in range(b):
        idx = [rng.randrange(len(gl)) for _ in range(len(gl))]
        sub = [i for g in idx for i in gl[g]]
        if len(sub) < 3:
            continue
        diffs.append(rho_of([pa[i] for i in sub]) - rho_of([pb[i] for i in sub]))
    diffs.sort()
    lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]
    return {
        "n_cells": len(shared),
        "delta": delta,
        "ci95": [lo, hi],
        "p_le_0": sum(1 for d in diffs if d <= 0) / len(diffs),
    }


def fmt_table(name_to_rep: dict[str, dict]) -> str:
    head = (
        "| Hệ | ô | đơn vị | Spearman (đã trừ TB khía cạnh) | CI95 | AUC sao ≤ 3 | giá trị dự đoán khác nhau | tỷ lệ ô gọi chê |\n"
        "|---|---|---|---|---|---|---|---|"
    )
    lines = [head]
    for name, rep in name_to_rep.items():
        lines.append(
            f"| {name} | {rep['n_cells']} | {rep['n_units']} | {rep['rho']:.3f} |"
            f" [{rep['ci95'][0]:.3f}; {rep['ci95'][1]:.3f}] | {rep['auc_star_le_3']:.3f} |"
            f" {rep['n_distinct_pred']} | {rep['neg_rate']:.3f} |"
        )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sentences", type=Path, default=SENTS)
    ap.add_argument("--gold", type=Path, nargs="+", default=GOLD)
    ap.add_argument("--test-gold", type=Path, default=TEST_GOLD)
    ap.add_argument("--b", type=int, default=2000, help="số lần bootstrap")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "eval" / "wm3_stars.json")
    ap.add_argument("--no-run-log", action="store_true")
    args = ap.parse_args()

    sents = read_jsonl(args.sentences)
    ratings = load_ratings()
    blurred = blurred_company_stars(ratings)
    drows, _, _, _ = splits(args.gold, args.test_gold, args.sentences)
    dev_reviews = {r["review_id"] for r in drows}

    rows = [r for r in sents if r.get("text") and r.get("section") in {"liked", "improvement", "title"}]
    print(
        f"câu: {len(rows)} | review: {len({r['source_review_id'] for r in rows})} |"
        f" công ty: {len({r['company_id'] for r in rows})} | bản ghi sao: {len(ratings)}"
        f" (bị che {sum(1 for r in ratings if not r.get('has_text'))})"
    )
    print(f"review dev (nguồn train của mô hình lai): {len(dev_reviews)} – số chính đo ngoài các review này\n")

    out: dict[str, dict] = {}
    for scope, keep in (("ngoài dev", lambda r: r["source_review_id"] not in dev_reviews), ("tất cả", lambda r: True)):
        sel = [r for r in rows if keep(r)]
        preds = predictions(sel, drows, args.seed)
        for unit, label in (
            ("review", "Mức review (đích: sao của chính review)"),
            ("company", "Mức công ty (đích: sao TB của review BỊ CHE)"),
        ):
            reps, cell_sets = {}, {}
            for name, pred in preds.items():
                cs = cells(sel, pred, blurred, unit)
                if cs:
                    reps[name] = evaluate(cs, args.b, args.seed)
                    cell_sets[name] = cs
            if not reps:
                continue
            print(f"### {label} – review {scope}\n")
            print(fmt_table(reps), "\n")
            # Hệ lai so với hai mốc, ghép cặp theo đơn vị
            hyb = next((n for n in cell_sets if n.startswith("lai")), None)
            pairs = {}
            if hyb:
                for base in (n for n in cell_sets if n != hyb):
                    d = paired(cell_sets[hyb], cell_sets[base], args.b, args.seed)
                    pairs[base] = d
                    print(
                        f"- lai so với **{base}**: Δρ = {d['delta']:+.3f},"
                        f" CI95 [{d['ci95'][0]:+.3f}; {d['ci95'][1]:+.3f}], p(Δ≤0) = {d['p_le_0']:.3f}"
                        f" ({d['n_cells']} ô)"
                    )
                print()
            out[f"{unit}|{scope}"] = {"systems": reps, "paired_vs_hybrid": pairs}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {args.out}")

    if not args.no_run_log:
        main_key = "company|ngoài dev"
        for name, rep in out.get(main_key, {}).get("systems", {}).items():
            save_run(
                task="WM3",
                method=name,
                eval_set="itviec_stars_blurred",
                split="eval",
                rq="WM3 có nói đúng về công ty theo đánh giá của người khác không",
                metrics={"spearman_stars": 0.0 if rep["rho"] != rep["rho"] else rep["rho"]},
                ci95={"spearman_stars": rep["ci95"]},
                ids=[f"{c}" for c in range(rep["n_cells"])],
                n_gold=rep["n_cells"],
                seed=args.seed,
                command="uv run python -m absa.company_eval",
            )


if __name__ == "__main__":
    main()
