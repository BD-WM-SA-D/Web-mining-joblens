"""WM6 – xuất đồ thị kỹ năng kèm toạ độ và cụm, để vẽ hình cho báo cáo.

    uv run python -m graph.export_viz --min-npmi 0.3 --out data/graph/viz_dict.json

Toạ độ tính bằng `spring_layout` của networkx (Fruchterman-Reingold) với `seed` cố định, nên chạy lại
cho đúng cùng một hình. Trọng số dùng cho lực hút là `npmi` chứ không phải số tin: lấy số tin thì các
kỹ năng phổ biến bị kéo dồn vào giữa và hình thành một cục.

File ra chỉ có tên kỹ năng, số tin, số cụm và toạ độ – không có nội dung tin nào.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx

from graph.analyze import load, louvain, prune_npmi
from graph.build import ROOT

SEED = 1


def layout(g: nx.Graph, seed: int = SEED) -> dict[str, tuple[float, float]]:
    pos = nx.spring_layout(g, weight="npmi", seed=seed, iterations=200)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    # chuẩn hoá về [0, 1] để trang vẽ không phải tự co giãn
    sx, sy = (max(xs) - min(xs)) or 1.0, (max(ys) - min(ys)) or 1.0
    return {k: (round((p[0] - min(xs)) / sx, 4), round((p[1] - min(ys)) / sy, 4)) for k, p in pos.items()}


def export(g: nx.Graph, parts: list[set[str]], pos: dict[str, tuple[float, float]]) -> dict:
    """Cụm được đánh số theo kích thước giảm dần, để màu trong hình ổn định giữa các lần chạy."""
    order = sorted(parts, key=len, reverse=True)
    comm = {x: i for i, part in enumerate(order) for x in part}
    q = nx.community.modularity(g, order, weight="weight")
    return {
        "n_jobs": g.graph["n_jobs"],
        "modularity": round(q, 4),
        "communities": [
            {"id": i, "size": len(part), "top": sorted(part, key=lambda x: -g.nodes[x]["df"])[:8]}
            for i, part in enumerate(order)
        ],
        "nodes": [
            {
                "skill": x,
                "df": g.nodes[x]["df"],
                "community": comm[x],
                "x": pos[x][0],
                "y": pos[x][1],
                "degree": g.degree(x),
            }
            for x in sorted(g)
        ],
        "edges": [
            {"u": u, "v": v, "weight": d["weight"], "npmi": round(d["npmi"], 3)}
            for u, v, d in sorted(g.edges(data=True), key=lambda e: -e[2]["npmi"])
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", type=Path, default=ROOT / "data" / "graph" / "skill_graph_dict.json")
    ap.add_argument("--min-npmi", type=float, default=0.3)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "graph" / "viz_dict.json")
    args = ap.parse_args()

    g = prune_npmi(load(args.graph), args.min_npmi)
    parts = louvain(g, "weight", 1.0, SEED)
    payload = export(g, parts, layout(g))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"{len(payload['nodes'])} đỉnh, {len(payload['edges'])} cạnh, {len(payload['communities'])} cụm, "
        f"Q = {payload['modularity']} → {args.out}"
    )


if __name__ == "__main__":
    main()
