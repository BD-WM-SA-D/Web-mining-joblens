"""WM6 – dựng đồ thị đồng xuất hiện kỹ năng từ tin tuyển dụng đã crawl.

    uv run python -m graph.build --extractor dict
    uv run python -m graph.build --extractor phobert --model data/models/wm2-phobert-v3-s1

Đỉnh là một kỹ năng (đã chuẩn hóa về `canonical` của `ie/resources/skill_alias.csv`), cạnh nối hai
kỹ năng cùng xuất hiện trong một tin. Đây là bài WM6 **tiêu thụ đầu ra của WM2**: chất lượng đồ thị
phụ thuộc trực tiếp vào bộ trích kỹ năng, nên có hai bộ trích để so:

| `--extractor` | Cách lấy kỹ năng | Số trên test WM2 |
|---|---|---|
| `dict` | từ điển alias khớp trên toàn văn tin | P 0,742 / R 0,315 |
| `phobert` | PhoBERT WM2 trên từng câu, span khớp lại về canonical | P ~0,70 / R ~0,47 |

**Trọng số cạnh.** Lưu cả hai: `weight` là số tin chứa cả hai kỹ năng, `npmi` là NPMI
(normalized pointwise mutual information). Đếm thô thiên về kỹ năng phổ biến – "Python–SQL" nhiều
tin chỉ vì cả hai đều phổ biến, không hẳn vì chúng gắn với nhau. NPMI khử phần đó:

    npmi(u,v) = log(p(u,v) / (p(u)·p(v))) / (-log p(u,v)),  trong [-1, 1]

**Hạn chế đã biết (ghi vào báo cáo).** Tin trùng giữa TopCV và ITviec chưa được gộp (WM1 đang gán
nhãn), nên một vị trí đăng hai nơi bị đếm hai lần. `--collapse-dup` gộp theo khóa baseline
(tiêu đề + công ty đã chuẩn hóa) để đo xem kết luận có đổi không.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
from collections import Counter
from pathlib import Path

import networkx as nx

from service.skills import SkillCatalog

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = [
    ROOT / "data" / "crawl" / "topcv" / "topcv_v2.parquet",
    ROOT / "data" / "crawl" / "itviec-jobs" / "itviec_v1.parquet",
]
OUT = ROOT / "data" / "graph"
TEXT_FIELDS = ("title", "description", "requirements_text")
TOKEN_RE = re.compile(r"\w+[+#]*|[^\w\s]")  # giống annotation/export_bio.py
MAX_LEN = 256  # giống mặc định của ie/phobert.py
MIN_DF = 5  # kỹ năng xuất hiện dưới 5 tin thì bỏ: cạnh của chúng gần như là nhiễu
MIN_WEIGHT = 3  # cạnh dưới 3 tin cũng bỏ


def job_text(row: dict) -> str:
    return "\n".join(str(row.get(f) or "") for f in TEXT_FIELDS)


def extract_dict(rows: list[dict], catalog: SkillCatalog) -> dict[str, set[str]]:
    """job_uid → tập nhãn kỹ năng, khớp từ điển trên toàn văn + tag nhà tuyển dụng."""
    out = {}
    for r in rows:
        labels = {s.label for *_, s in catalog.extract(job_text(r))}
        tags = r.get("skill_tags")
        for tag in [] if tags is None else tags:
            skill = catalog.lookup(str(tag).strip())
            if skill:
                labels.add(skill.label)
        if labels:
            out[r["job_uid"]] = labels
    return out


def spans_to_labels(tokens: list[str], tags: list[str], catalog: SkillCatalog) -> set[str]:
    """Span BIO → nhãn canonical. Span không tra được trong từ điển thì bỏ (không tự tạo đỉnh mới).

    Bỏ span lạ là có chủ ý: PhoBERT bắt được tên hiếm (`GoldenGate`, `HiStaff`) mà từ điển chưa có,
    nhưng mỗi tên như vậy chỉ xuất hiện 1-2 tin nên sẽ bị `MIN_DF` loại, còn nếu giữ thì chúng kéo
    theo rủi ro gộp sai dạng viết (`Node`, `NodeJS`, `Node.js` thành ba đỉnh).
    """
    labels, cur = set(), []
    for tok, tag in zip(tokens, tags, strict=True):
        if tag.startswith("B-"):
            if cur:
                labels.add(" ".join(cur))
            cur = [tok]
        elif tag.startswith("I-") and cur:
            cur.append(tok)
        else:
            if cur:
                labels.add(" ".join(cur))
            cur = []
    if cur:
        labels.add(" ".join(cur))
    out = set()
    for form in labels:
        skill = catalog.lookup(form) or catalog.lookup(form.replace(" ", ""))
        if skill:
            out.add(skill.label)
    return out


def extract_phobert(rows: list[dict], catalog: SkillCatalog, model_dir: Path) -> dict[str, set[str]]:
    """Chạy PhoBERT WM2 trên từng câu của tin, gộp span về nhãn canonical."""
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    from annotation.sample_skill_batch import split_sentences
    from ie.phobert import prepare

    sents = []
    for r in rows:
        for field in TEXT_FIELDS:
            for i, text in enumerate(split_sentences(str(r.get(field) or ""))):
                toks = TOKEN_RE.findall(text)
                if toks:
                    sents.append(
                        {
                            "id": f"{r['job_uid'][:12]}-{field[:4]}{i:02d}",
                            "job_uid": r["job_uid"],
                            "tokens": toks,
                            "tags": ["O"] * len(toks),
                        }
                    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForTokenClassification.from_pretrained(model_dir).to(device).eval()
    from ie.phobert import predict

    print(f"{len(sents)} câu, thiết bị {device}")
    rows_prep = prepare(sents, ROOT / "data" / "models" / "seg_cache.jsonl")
    pred = predict(model, tok, rows_prep, MAX_LEN, device)
    out: dict[str, set[str]] = {}
    for s, tags in zip(sents, pred, strict=True):
        labels = spans_to_labels(s["tokens"], tags, catalog)
        if labels:
            out.setdefault(s["job_uid"], set()).update(labels)
    return out


def cooccurrence(job_skills: dict[str, set[str]], min_df: int = MIN_DF, min_weight: int = MIN_WEIGHT) -> nx.Graph:
    """Đồ thị vô hướng: đỉnh = kỹ năng, cạnh = số tin chứa cả hai, kèm NPMI."""
    n = len(job_skills)
    df = Counter(s for skills in job_skills.values() for s in skills)
    keep = {s for s, c in df.items() if c >= min_df}
    pairs: Counter[tuple[str, str]] = Counter()
    for skills in job_skills.values():
        for u, v in itertools.combinations(sorted(skills & keep), 2):
            pairs[(u, v)] += 1

    g = nx.Graph()
    for s in keep:
        g.add_node(s, df=df[s])
    for (u, v), w in pairs.items():
        if w < min_weight:
            continue
        p_uv, p_u, p_v = w / n, df[u] / n, df[v] / n
        # p_uv = 1 nghĩa là cả hai kỹ năng có trong mọi tin: p_uv = p_u·p_v nên PMI = 0 (độc lập),
        # và mẫu số -log p_uv cũng = 0. Giới hạn ở đây là 0: kỹ năng có ở mọi tin không mang tín hiệu
        # gắn bó nào. Không chặn thì chia cho 0 (gặp khi dựng đồ thị trên tập con nhỏ).
        npmi = 0.0 if p_uv >= 1.0 else math.log(p_uv / (p_u * p_v)) / -math.log(p_uv)
        g.add_edge(u, v, weight=w, npmi=round(npmi, 4))
    g.remove_nodes_from([x for x in list(g) if g.degree(x) == 0])
    g.graph["n_jobs"] = n
    return g


def to_json(g: nx.Graph) -> dict:
    return {
        "n_jobs": g.graph["n_jobs"],
        "nodes": [{"skill": x, "df": g.nodes[x]["df"]} for x in sorted(g)],
        "edges": [
            {"u": u, "v": v, "weight": d["weight"], "npmi": d["npmi"]}
            for u, v, d in sorted(g.edges(data=True), key=lambda e: (e[0], e[1]))
        ],
    }


def from_json(payload: dict) -> nx.Graph:
    g = nx.Graph()
    g.graph["n_jobs"] = payload["n_jobs"]
    for x in payload["nodes"]:
        g.add_node(x["skill"], df=x["df"])
    for e in payload["edges"]:
        g.add_edge(e["u"], e["v"], weight=e["weight"], npmi=e["npmi"])
    return g


def load_rows(paths: list[Path], collapse_dup: bool) -> list[dict]:
    import pandas as pd

    frames = [pd.read_parquet(p) for p in paths if p.exists()]
    if not frames:
        raise SystemExit(f"không có snapshot nào trong {[str(p) for p in paths]}")
    df = pd.concat(frames, ignore_index=True)
    if collapse_dup:
        from crawler.dedup import baseline_key

        df["_k"] = [baseline_key(r.title, r.company_name) for r in df.itertuples()]
        before = len(df)
        df = df.drop_duplicates("_k", keep="first").drop(columns="_k")
        print(f"gộp theo khóa baseline: {before} → {len(df)} tin")
    return df.to_dict("records")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extractor", choices=["dict", "phobert"], default="dict")
    ap.add_argument("--model", type=Path, default=ROOT / "data" / "models" / "wm2-phobert-v3-s1")
    ap.add_argument("--snapshots", type=Path, nargs="+", default=SNAPSHOTS)
    ap.add_argument("--collapse-dup", action="store_true", help="gộp tin cùng tiêu đề+công ty (thử độ bền)")
    ap.add_argument("--min-df", type=int, default=MIN_DF)
    ap.add_argument("--min-weight", type=int, default=MIN_WEIGHT)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    rows = load_rows(args.snapshots, args.collapse_dup)
    catalog = SkillCatalog()
    if args.extractor == "dict":
        job_skills = extract_dict(rows, catalog)
    else:
        job_skills = extract_phobert(rows, catalog, args.model)
    g = cooccurrence(job_skills, args.min_df, args.min_weight)

    name = args.extractor + ("-collapsed" if args.collapse_dup else "")
    out = args.out or OUT / f"skill_graph_{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(to_json(g), ensure_ascii=False, indent=1), encoding="utf-8")
    per_job = sum(len(v) for v in job_skills.values()) / max(1, len(job_skills))
    print(
        f"{len(rows)} tin, {len(job_skills)} tin có kỹ năng ({per_job:.1f} kỹ năng/tin); "
        f"đồ thị {g.number_of_nodes()} đỉnh, {g.number_of_edges()} cạnh → {out}"
    )


if __name__ == "__main__":
    main()
