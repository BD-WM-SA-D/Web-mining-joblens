"""WM6 – gợi ý kỹ năng bằng PageRank cá nhân hoá, và các mốc phải vượt.

    uv run python -m graph.recommend
    uv run python -m graph.recommend --profile Java SQL

**Vì sao có file này.** PageRank toàn cục trên đồ thị đồng xuất hiện gần như bằng phép đếm
(`graph.analyze rank` đo được Spearman 0,90 với bậc có trọng số), nên nó không nói thêm gì. Chỗ
PageRank *không* thay thế được bằng đếm là **PageRank cá nhân hoá**: khởi động lại ngẫu nhiên chỉ về
các kỹ năng của một hồ sơ, nên kết quả phụ thuộc hồ sơ. Đầu ra là một bộ gợi ý kỹ năng, dùng được cho
WM5 và cho hồ sơ kỹ năng của app (UC004).

**Cách đánh giá.** Không có nhãn "kỹ năng nên học tiếp", nên dùng bài **đoán kỹ năng bị che**: mỗi tin
tuyển dụng là một "hồ sơ" có thật; che một kỹ năng của tin, đưa phần còn lại làm hồ sơ, xem hệ xếp kỹ
năng bị che lên hạng bao nhiêu. Đồ thị dựng **chỉ trên nửa train**, đánh giá trên các tin ở nửa test,
nên kỹ năng bị che không nằm trong đồ thị của chính tin đó.

Ba hệ, mỗi hệ phải hơn hệ trước mới đáng:

| Hệ | Cách xếp hạng |
|---|---|
| `popular` | theo số tin, không nhìn hồ sơ. Mốc sàn. |
| `count` | tổng **số tin** đồng xuất hiện với các kỹ năng trong hồ sơ. Phép đếm thô. |
| `count-npmi` | như trên nhưng cộng NPMI. **Mốc thật sự phải vượt.** |
| `ppr` | PageRank cá nhân hoá, khởi động lại về các kỹ năng trong hồ sơ, trọng số NPMI. |

Metric: Recall@10 (kỹ năng bị che có nằm trong 10 gợi ý đầu không) và MRR (một chia cho hạng của nó).

**Hai tham số và cách chọn.** Trọng số NPMI thay số tin, và `alpha` (xác suất đi tiếp thay vì nhảy về
hồ sơ) hạ từ 0,85 xuống **0,35**: 0,85 là giá trị dành cho người lướt web, còn ở đây cần bước đi ở
gần hồ sơ. Ảnh hưởng rất lớn – `ppr` với alpha 0,85 và trọng số số tin cho Recall@10 0,384, **thua cả
phép đếm**. Hai tham số chọn trên lần chia seed 1, rồi kiểm lại trên seed 2–5 (xem `experiments/results.md`).
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import networkx as nx
import numpy as np

from graph.build import MIN_DF, MIN_WEIGHT, SNAPSHOTS, cooccurrence, extract_dict, load_rows

SEED = 1
MIN_SKILLS = 4  # hồ sơ phải còn ≥ 3 kỹ năng sau khi che 1
TOP_K = 10
ALPHA = 0.35


def pos_weight(g: nx.Graph) -> nx.Graph:
    """Dùng NPMI làm trọng số, cạnh NPMI ≤ 0 hạ về gần 0 thay vì bỏ (giữ đồ thị liên thông)."""
    h = g.copy()
    for _, _, d in h.edges(data=True):
        d["w"] = max(d["npmi"], 0.001)
    return h


def rank_popular(g: nx.Graph, profile: set[str]) -> list[str]:
    return sorted((x for x in g if x not in profile), key=lambda x: -g.nodes[x]["df"])


def rank_count(g: nx.Graph, profile: set[str], key: str = "weight") -> list[str]:
    score: dict[str, float] = {}
    for s in profile:
        if s not in g:
            continue
        for nb, d in g[s].items():
            if nb not in profile:
                score[nb] = score.get(nb, 0) + d[key]
    return sorted(score, key=lambda x: (-score[x], -g.nodes[x]["df"]))


def rank_ppr(g: nx.Graph, profile: set[str], alpha: float = ALPHA) -> list[str]:
    seeds = {s: 1.0 for s in profile if s in g}
    if not seeds:
        return []
    pr = nx.pagerank(g, weight="w", personalization=seeds, alpha=alpha)
    return sorted((x for x in pr if x not in profile), key=lambda x: -pr[x])


RANKERS = {
    "popular": rank_popular,
    "count": rank_count,
    "count-npmi": lambda g, p: rank_count(g, p, key="w"),
    "ppr": rank_ppr,
}


def evaluate(g: nx.Graph, cases: list[tuple[set[str], str]], k: int = TOP_K) -> dict[str, dict[str, float]]:
    out = {}
    for name, fn in RANKERS.items():
        res = outcomes(g, cases, fn, k)
        n = len(cases)
        out[name] = {f"recall@{k}": sum(h for h, _ in res) / n, "mrr": sum(r for _, r in res) / n}
    return out


def outcomes(g: nx.Graph, cases: list[tuple[set[str], str]], fn, k: int = TOP_K) -> list[tuple[int, float]]:
    """Từng ca: (trúng top-k hay không, nghịch đảo hạng). Dùng cho kiểm định ghép cặp."""
    out = []
    for profile, held in cases:
        ranked = fn(g, profile)
        pos = ranked.index(held) + 1 if held in ranked else 0
        out.append((1 if 0 < pos <= k else 0, 1 / pos if pos else 0.0))
    return out


def build_cases(test_jobs: list[set[str]], vocab: set[str], seed: int) -> list[tuple[set[str], str]]:
    """Mỗi tin đủ kỹ năng → một ca: che một kỹ năng ngẫu nhiên, phần còn lại làm hồ sơ.

    Chỉ che kỹ năng có trong đồ thị train, vì kỹ năng ngoài đồ thị thì hệ nào cũng không đoán được –
    giữ lại chỉ làm cả ba hệ cùng tụt, không đổi thứ tự.
    """
    return [(profile, held) for _, profile, held in build_cases_ids(list(enumerate(test_jobs)), vocab, seed)]


def build_cases_ids(test_jobs: list[tuple], vocab: set[str], seed: int) -> list[tuple]:
    """Như `build_cases` nhưng giữ mã tin: [(mã tin, hồ sơ, kỹ năng bị che)]. Cùng seed thì cùng ca."""
    rnd = random.Random(seed)
    cases = []
    for uid, skills in test_jobs:
        inside = sorted(skills & vocab)
        if len(inside) < MIN_SKILLS:
            continue
        held = rnd.choice(inside)
        cases.append((uid, {s for s in inside if s != held}, held))
    return cases


def split(seed: int, snapshots: list[Path]) -> tuple[nx.Graph, dict[str, set[str]]]:
    from service.skills import SkillCatalog

    rows = load_rows(snapshots, collapse_dup=False)
    rnd = random.Random(seed)
    rnd.shuffle(rows)
    cut = len(rows) // 2
    catalog = SkillCatalog()
    train = extract_dict(rows[:cut], catalog)
    test = extract_dict(rows[cut:], catalog)
    g = pos_weight(cooccurrence(train, MIN_DF, MIN_WEIGHT))
    print(f"train {len(train)} tin → {g.number_of_nodes()} đỉnh / {g.number_of_edges()} cạnh;  test {len(test)} tin")
    return g, test


def cmd_eval(args) -> None:
    """Chạy trên nhiều lần chia train/test và báo trung bình ± độ lệch, kèm Δ từng lần.

    Một lần chia không đủ: chênh lệch giữa `ppr` và `count-npmi` cùng cỡ với dao động giữa các lần
    chia, nên phải xem Δ có cùng dấu ở mọi lần hay không.
    """
    import statistics as st

    acc: dict[str, dict[str, list[float]]] = {n: {"r": [], "m": []} for n in RANKERS}
    paired: list[tuple[str, tuple[int, float], tuple[int, float]]] = []  # (mã tin, ppr, count-npmi)
    for seed in args.seeds:
        g, test = split(seed, args.snapshots)
        with_ids = build_cases_ids(list(test.items()), set(g), seed)
        cases = [(p, h) for _, p, h in with_ids]
        res = evaluate(g, cases, args.k)
        for name in RANKERS:
            acc[name]["r"].append(res[name][f"recall@{args.k}"])
            acc[name]["m"].append(res[name]["mrr"])
        a = outcomes(g, cases, RANKERS["ppr"], args.k)
        b = outcomes(g, cases, RANKERS["count-npmi"], args.k)
        paired += [(uid, x, y) for (uid, _, _), x, y in zip(with_ids, a, b, strict=True)]

    n_split = len(args.seeds)
    print(f"\n{n_split} lần chia, alpha {ALPHA}")
    print(f"| Hệ | Recall@{args.k} | MRR |")
    print("|---|---|---|")
    for name in RANKERS:
        r, m = acc[name]["r"], acc[name]["m"]
        print(f"| {name} | {st.mean(r):.3f} ± {st.pstdev(r):.3f} | {st.mean(m):.3f} ± {st.pstdev(m):.3f} |")
    if n_split > 1:
        for key, lab in (("r", f"Recall@{args.k}"), ("m", "MRR")):
            d = [a - b for a, b in zip(acc["ppr"][key], acc["count-npmi"][key], strict=True)]
            print(f"Δ {lab} (ppr − count-npmi) từng lần: " + ", ".join(f"{x:+.3f}" for x in d))
    paired_test(paired, args.k)


def paired_test(paired: list[tuple[str, tuple[int, float], tuple[int, float]]], k: int, b: int = 2000) -> None:
    """Kiểm định ghép cặp `ppr` với `count-npmi` trên mọi ca của mọi lần chia.

    Bootstrap lấy lại **theo tin**: một tin có thể rơi vào nửa test của nhiều lần chia, các ca của nó
    không độc lập. Thêm kiểm định dấu trên các ca hai hệ cho kết quả top-k khác nhau.
    """
    from scipy.stats import binomtest

    from experiments.bootstrap import ci, cluster_indices

    groups = [uid for uid, _, _ in paired]
    dh = np.array([x[0] - y[0] for _, x, y in paired], dtype=float)
    dr = np.array([x[1] - y[1] for _, x, y in paired], dtype=float)
    print(f"\nKiểm định ghép cặp ppr − count-npmi: {len(paired)} ca, {len(set(groups))} tin, bootstrap theo tin")
    for lab, d in ((f"Recall@{k}", dh), ("MRR", dr)):
        lo, hi, p0 = ci([d[ix].mean() for ix in cluster_indices(groups, b)])
        print(f"  Δ {lab} = {d.mean():+.3f}  CI95 [{lo:+.3f}; {hi:+.3f}]  p(Δ≤0) = {p0:.3f}")
    win = int(sum(1 for _, x, y in paired if x[0] > y[0]))
    lose = int(sum(1 for _, x, y in paired if x[0] < y[0]))
    p = binomtest(win, win + lose, 0.5).pvalue if win + lose else float("nan")
    print(
        f"  Kiểm định dấu (top-{k}): ppr trúng mà count-npmi trượt {win} ca, ngược lại {lose} ca; p hai phía = {p:.3f}"
    )


def cmd_profile(args) -> None:
    g, _ = split(args.seed, args.snapshots)
    profile = {s for s in args.profile if s in g}
    missing = [s for s in args.profile if s not in g]
    if missing:
        print(f"không có trong đồ thị (bỏ qua): {', '.join(missing)}")
    if not profile:
        raise SystemExit("hồ sơ không còn kỹ năng nào nằm trong đồ thị")
    print(f"\nHồ sơ: {', '.join(sorted(profile))}\n")
    print(f"| # | {' | '.join(RANKERS)} |")
    print("|---|" + "---|" * len(RANKERS))
    lists = {name: fn(g, profile) for name, fn in RANKERS.items()}
    for i in range(args.k):
        cells = [lists[name][i] if i < len(lists[name]) else "–" for name in RANKERS]
        print(f"| {i + 1} | {' | '.join(cells)} |")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", nargs="+", help="kỹ năng của hồ sơ; không có thì chạy đánh giá")
    ap.add_argument("--snapshots", type=Path, nargs="+", default=SNAPSHOTS)
    ap.add_argument("--seed", type=int, default=SEED, help="lần chia dùng cho --profile")
    ap.add_argument("--seeds", type=int, nargs="+", default=[2, 3, 4, 5], help="các lần chia để đánh giá")
    ap.add_argument("--k", type=int, default=TOP_K)
    args = ap.parse_args()
    (cmd_profile if args.profile else cmd_eval)(args)


if __name__ == "__main__":
    main()
