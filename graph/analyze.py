"""WM6 – phân tích đồ thị kỹ năng: PageRank, cụm Louvain, và các mốc để biết số đó có nghĩa gì.

    uv run python -m graph.analyze rank   --graph data/graph/skill_graph_dict.json
    uv run python -m graph.analyze cluster --graph data/graph/skill_graph_dict.json
    uv run python -m graph.analyze stability

Ba mốc bắt buộc, vì cả PageRank lẫn modularity đều **tự nó không nói gì**:

1. **PageRank so với bậc có trọng số (strength).** Trên đồ thị vô hướng, PageRank xấp xỉ tỷ lệ với
   strength; nếu hai thứ hạng gần như trùng nhau thì PageRank không thêm tri thức gì và phải nói thẳng.
   Đo bằng tương quan Spearman và số đỉnh lệch hạng.
2. **Modularity so với đồ thị ngẫu nhiên giữ nguyên bậc.** Một đồ thị ngẫu nhiên cũng có modularity
   dương, nên Q = 0,3 không chứng minh có cấu trúc cụm. So với phân phối Q của đồ thị đã đảo cạnh
   (degree-preserving rewiring) mới kết luận được.
3. **Độ ổn định của cụm theo thời gian**, so với mốc gán cụm ngẫu nhiên: chia tin theo ngày đăng làm
   hai nửa, chạy Louvain mỗi nửa, đo NMI/ARI trên các đỉnh chung.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import networkx as nx

from graph.build import ROOT, SNAPSHOTS, cooccurrence, extract_dict, from_json, load_rows

SEED = 1
N_NULL = 200  # số đồ thị ngẫu nhiên để lấy phân phối modularity


def load(path: Path) -> nx.Graph:
    return from_json(json.loads(path.read_text(encoding="utf-8")))


def prune_npmi(g: nx.Graph, min_npmi: float) -> nx.Graph:
    """Bỏ cạnh NPMI thấp: đồ thị đồng xuất hiện thô rất dày, cụm bị dính thành một khối."""
    h = g.copy()
    h.remove_edges_from([(u, v) for u, v, d in g.edges(data=True) if d["npmi"] < min_npmi])
    h.remove_nodes_from([x for x in list(h) if h.degree(x) == 0])
    h.graph["n_jobs"] = g.graph["n_jobs"]
    return h


# ---------- 1. xếp hạng kỹ năng ----------


def strength(g: nx.Graph, weight: str) -> dict[str, float]:
    return dict(g.degree(weight=weight))


def cmd_rank(args) -> None:
    from scipy.stats import spearmanr

    g = load(args.graph)
    pr = nx.pagerank(g, weight=args.weight, alpha=0.85)
    st = strength(g, args.weight)
    df = {x: g.nodes[x]["df"] for x in g}

    nodes = sorted(g)
    rho_st = spearmanr([pr[x] for x in nodes], [st[x] for x in nodes]).statistic
    rho_df = spearmanr([pr[x] for x in nodes], [df[x] for x in nodes]).statistic

    r_pr = {x: i for i, x in enumerate(sorted(nodes, key=lambda x: -pr[x]), 1)}
    r_st = {x: i for i, x in enumerate(sorted(nodes, key=lambda x: -st[x]), 1)}
    moved = sorted(nodes, key=lambda x: -abs(r_pr[x] - r_st[x]))

    print(f"{args.graph.name}: {g.number_of_nodes()} đỉnh, {g.number_of_edges()} cạnh, trọng số `{args.weight}`")
    print(f"Spearman PageRank ~ strength: {rho_st:.4f};  PageRank ~ số tin (df): {rho_df:.4f}")
    shared = len({x for x in nodes if r_pr[x] <= 10} & {x for x in nodes if r_st[x] <= 10})
    print(f"Top-10 của hai cách trùng nhau {shared}/10")
    print("Lệch hạng lớn nhất: " + ", ".join(f"{x} ({r_st[x]}→{r_pr[x]})" for x in moved[:5]))

    print("\n| # | PageRank | strength | số tin nhiều nhất |")
    print("|---|---|---|---|")
    by_df = sorted(nodes, key=lambda x: -df[x])
    by_pr = sorted(nodes, key=lambda x: -pr[x])
    by_st = sorted(nodes, key=lambda x: -st[x])
    for i in range(10):
        print(f"| {i + 1} | {by_pr[i]} | {by_st[i]} | {by_df[i]} ({df[by_df[i]]}) |")


# ---------- 2. cụm kỹ năng ----------


def louvain(g: nx.Graph, weight: str, resolution: float, seed: int) -> list[set[str]]:
    return nx.community.louvain_communities(g, weight=weight, resolution=resolution, seed=seed)


def null_modularity(g: nx.Graph, weight: str, resolution: float, n: int, seed: int) -> list[float]:
    """Modularity của đồ thị đảo cạnh giữ nguyên bậc (mốc 'không có cấu trúc cụm')."""
    out = []
    rnd = random.Random(seed)
    for i in range(n):
        h = g.copy()
        try:
            nx.double_edge_swap(
                h, nswap=5 * h.number_of_edges(), max_tries=200 * h.number_of_edges(), seed=rnd.randint(0, 10**9)
            )
        except nx.NetworkXAlgorithmError:  # đồ thị quá dày/thưa để đảo đủ số lần
            pass
        parts = louvain(h, weight, resolution, seed + i)
        out.append(nx.community.modularity(h, parts, weight=weight, resolution=resolution))
    return out


def cmd_cluster(args) -> None:
    import statistics

    g = load(args.graph)
    if args.min_npmi is not None:
        before = (g.number_of_nodes(), g.number_of_edges())
        g = prune_npmi(g, args.min_npmi)
        print(
            f"lọc NPMI ≥ {args.min_npmi}: {before[0]} đỉnh/{before[1]} cạnh → {g.number_of_nodes()}/{g.number_of_edges()}"
        )

    parts = louvain(g, args.weight, args.resolution, SEED)
    q = nx.community.modularity(g, parts, weight=args.weight, resolution=args.resolution)
    null = null_modularity(g, args.weight, args.resolution, args.n_null, SEED)
    mu, sd = statistics.mean(null), statistics.pstdev(null) or 1e-9
    over = sum(1 for x in null if x >= q)

    print(f"\nLouvain (trọng số `{args.weight}`, resolution {args.resolution}): {len(parts)} cụm, Q = {q:.4f}")
    print(
        f"Mốc đồ thị ngẫu nhiên giữ bậc ({args.n_null} lần): Q = {mu:.4f} ± {sd:.4f}; "
        f"z = {(q - mu) / sd:.1f}; số lần ngẫu nhiên ≥ thật: {over}/{args.n_null}"
    )

    # độ ổn định theo seed: Louvain phụ thuộc thứ tự quét
    from sklearn.metrics import normalized_mutual_info_score

    base = labels(g, parts)
    nmis = []
    for s in range(2, 7):
        p = louvain(g, args.weight, args.resolution, s)
        nmis.append(normalized_mutual_info_score(base, labels(g, p)))
    print(f"Ổn định giữa 5 seed khác (NMI với seed 1): {min(nmis):.3f}–{max(nmis):.3f}")

    print("\n| Cụm | Số kỹ năng | Kỹ năng nhiều tin nhất trong cụm |")
    print("|---|---|---|")
    for i, part in enumerate(sorted(parts, key=len, reverse=True), 1):
        top = sorted(part, key=lambda x: -g.nodes[x]["df"])[:8]
        print(f"| {i} | {len(part)} | {', '.join(top)} |")


def labels(g: nx.Graph, parts: list[set[str]], nodes: list[str] | None = None) -> list[int]:
    m = {x: i for i, part in enumerate(parts) for x in part}
    return [m.get(x, -1) for x in (nodes if nodes is not None else sorted(g))]


# ---------- 3. cụm có lặp lại trên một nửa dữ liệu khác không ----------


def halves(df, how: str, seed: int):
    """Chia tin làm hai nửa theo `how`.

    - `time`: theo ngày đăng. **Cẩn thận:** hai snapshot lệch nhau về thời gian (TopCV 08–10/2026,
      ITviec 09–11/2026) nên chia theo thời gian cũng gần như chia theo nguồn – kết quả không tách
      được hai nguyên nhân. Dùng `source` và `random` để tách.
    - `source`: TopCV so với ITviec. Trả lời "cụm có phải chỉ là nếp riêng của một trang web không".
    - `random`: mốc đối chứng – cùng phân bố, chỉ khác mẫu. NMI ở đây là trần thực tế của hai nửa
      nhỏ, vì nửa nào cũng chỉ còn một nửa số tin.
    """
    if how == "time":
        d = df.sort_values("date_posted").reset_index(drop=True)
        cut = len(d) // 2
        return d.iloc[:cut], d.iloc[cut:]
    if how == "source":
        return df[df["source"] == "topcv"], df[df["source"] == "itviec"]
    d = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    cut = len(d) // 2
    return d.iloc[:cut], d.iloc[cut:]


def cmd_stability(args) -> None:
    import pandas as pd
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    from service.skills import SkillCatalog

    rows = load_rows(args.snapshots, collapse_dup=False)
    df = pd.DataFrame(rows)
    catalog = SkillCatalog()
    print(f"chia theo `{args.split}`, NPMI ≥ {args.min_npmi}, min_df {args.min_df}, min_weight {args.min_weight}")

    parts, graphs = [], []
    for i, h in enumerate(halves(df, args.split, SEED), 1):
        g = cooccurrence(extract_dict(h.to_dict("records"), catalog), args.min_df, args.min_weight)
        if args.min_npmi is not None:
            g = prune_npmi(g, args.min_npmi)
        graphs.append(g)
        parts.append(louvain(g, args.weight, args.resolution, SEED))
        src = dict(h["source"].value_counts())
        print(f"  nửa {i}: {len(h)} tin {src}, {g.number_of_nodes()} đỉnh, {len(parts[-1])} cụm")

    common = sorted(set(graphs[0]) & set(graphs[1]))
    a = labels(graphs[0], parts[0], common)
    b = labels(graphs[1], parts[1], common)
    nmi, ari = normalized_mutual_info_score(a, b), adjusted_rand_score(a, b)

    rnd = random.Random(SEED)
    null = []
    for _ in range(200):
        shuf = b[:]
        rnd.shuffle(shuf)
        null.append(normalized_mutual_info_score(a, shuf))

    print(
        f"  {len(common)} đỉnh chung: NMI {nmi:.3f} / ARI {ari:.3f} "
        f"(mốc gán ngẫu nhiên NMI {sum(null) / len(null):.3f})"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("rank", cmd_rank), ("cluster", cmd_cluster), ("stability", cmd_stability)):
        p = sub.add_parser(name)
        p.add_argument("--weight", default="weight", choices=["weight", "npmi"])
        p.add_argument("--graph", type=Path, default=ROOT / "data" / "graph" / "skill_graph_dict.json")
        if name != "rank":
            p.add_argument("--resolution", type=float, default=1.0)
            p.add_argument("--min-npmi", type=float, default=None)
        if name == "cluster":
            p.add_argument("--n-null", type=int, default=N_NULL)
        if name == "stability":
            p.add_argument("--snapshots", type=Path, nargs="+", default=SNAPSHOTS)
            p.add_argument("--split", choices=["time", "source", "random"], default="random")
            p.add_argument("--min-df", type=int, default=3)
            p.add_argument("--min-weight", type=int, default=2)
        p.set_defaults(fn=fn)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
