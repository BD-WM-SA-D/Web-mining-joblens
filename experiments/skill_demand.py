"""WM2 (ứng dụng) – nhu cầu kỹ năng: bảng thống kê từ đầu ra trích kỹ năng.

    uv run python -m experiments.skill_demand                      # từ điển, corpus tự crawl + VietJobs IT
    uv run python -m experiments.skill_demand --all-categories     # thêm VietJobs đủ 48.092 tin (đọc CSV 103 MB)
    uv run python -m experiments.skill_demand --extractor phobert --model data/models/wm2-phobert-selftrain-s1

Đề tài đã đăng ký là *"Mining Vietnamese Job Postings for Skill Demand"*, nhưng `results.md` chỉ có số
chất lượng mô hình, chưa có bảng nào về **nhu cầu**. Script này sinh bốn bảng đó. Không cần gán nhãn,
không cần crawl thêm.

**Nguồn và vai trò – không trộn lẫn.**

| Nguồn | Số tin | Vai trò |
|---|---|---|
| TopCV + ITviec (tự crawl) | ~900 | Dữ liệu chính của môn; tập test WM2 lấy từ đây |
| VietJobs IT (`vietjobs_it`) | 1.906 | **Chỉ để so sánh và lấy bề rộng**, không bao giờ là tập test (quy tắc repo) |
| VietJobs đủ bộ | 48.092 | Bề rộng theo ngành, với `--all-categories` |

Mọi bảng đều tách theo nguồn. Trộn ba nguồn thành một con số là che mất thiên lệch nguồn, mà thiên
lệch nguồn ở đây lớn: ITviec là tin tiếng Anh của công ty IT nước ngoài, TopCV là tin tiếng Việt diện
rộng, VietJobs là một bộ dữ liệu đã qua xử lý của nhóm khác.

**Hạn chế phải ghi kèm mọi bảng.**

- Từ điển alias có **200 kỹ năng chuẩn**, phủ 54,9% số lần gắn tag `technical_skills` của VietJobs;
  đuôi dài 3.771 tag khác nhau không được đếm. Mọi con số là nhu cầu *trong phạm vi 200 kỹ năng đó*.
- Sitemap chỉ chứa **tin đang mở**, nên bảng theo tháng là lát cắt tin còn sống tại lúc crawl, không
  phải chuỗi thời gian của thị trường. Tin cũ đã đóng không có trong dữ liệu.
- Tin trùng giữa hai nguồn chưa gộp (WM1 chưa xong) → một vị trí đăng hai nơi đếm hai lần. `--collapse-dup`
  gộp theo khóa baseline để xem kết luận có đổi không.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from service.skills import SkillCatalog

ROOT = Path(__file__).resolve().parents[1]
CRAWL = {
    "topcv": ROOT / "data" / "crawl" / "topcv" / "topcv_20261115.parquet",
    "itviec": ROOT / "data" / "crawl" / "itviec-jobs" / "itviec_20261113.parquet",
}
VIETJOBS_IT = ROOT / "data" / "vietjobs" / "vietjobs_it.parquet"
VIETJOBS_ALL = ROOT / "data" / "vietjobs" / "VietJobs.csv"
TEXT_FIELDS = ("title", "job_title", "description", "requirements_text")
OUT = ROOT / "data" / "eval" / "skill_demand.json"


# ---------- trích kỹ năng ----------


def job_text(row: dict) -> str:
    return "\n".join(str(row.get(f) or "") for f in TEXT_FIELDS if row.get(f) is not None)


def skills_dict(rows: list[dict], catalog: SkillCatalog) -> list[set[str]]:
    """Khớp từ điển trên toàn văn + tag kỹ năng của nguồn (nếu có)."""
    out = []
    for r in rows:
        labels = {s.label for *_, s in catalog.extract(job_text(r))}
        for field in ("skill_tags", "technical_skills"):
            tags = r.get(field)
            if tags is None or (isinstance(tags, float) and tags != tags):
                continue
            items = tags if not isinstance(tags, str) else tags.split(",")
            for tag in items:
                skill = catalog.lookup(str(tag).strip())
                if skill:
                    labels.add(skill.label)
        out.append(labels)
    return out


def skills_phobert(rows: list[dict], catalog: SkillCatalog, model_dir: Path) -> list[set[str]]:
    """Dùng chính đường trích của WM6 để hai bài nói cùng một thứ."""
    from graph.build import extract_phobert

    for i, r in enumerate(rows):
        r.setdefault("job_uid", f"row-{i}")
    by_uid = extract_phobert(rows, catalog, model_dir)
    return [by_uid.get(r["job_uid"], set()) for r in rows]


# ---------- thống kê ----------


def cat_level2(category: str | None) -> str:
    """Cấp 2 của cây danh mục TopCV ("CNTT > Thiết kế > Game Development" → "Thiết kế").

    Cấp 3 cho nhóm 20-30 tin, quá nhỏ; cấp 1 thì cả corpus là một nhóm. ITviec chỉ có một giá trị
    phẳng ("Information Technology") nên nhóm nghề chỉ đọc được trong TopCV.
    """
    parts = [x.strip() for x in str(category or "?").split(">") if x.strip()]
    return parts[1] if len(parts) > 1 else (parts[0] if parts else "?")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """CI95 của một tỷ lệ theo Wilson: đúng hơn CI chuẩn khi tỷ lệ nhỏ, mà kỹ năng đuôi dài thì rất nhỏ."""
    if n == 0:
        return (float("nan"), float("nan"))
    p, z2 = k / n, z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def log_odds_dirichlet(group: Counter, rest: Counter, prior: Counter, alpha: float = 100.0) -> dict[str, float]:
    """Log-odds-ratio có tiên nghiệm Dirichlet (Monroe et al. 2008), chuẩn hóa theo độ lệch chuẩn.

    Lấy "kỹ năng phổ biến nhất trong nhóm" thì nhóm nào cũng ra Python/SQL. Chỉ số này trả lời câu khác:
    kỹ năng nào **đặc trưng** cho nhóm so với phần còn lại, và nó không bị kỹ năng tần số thấp đánh lừa
    như tỷ lệ thô (tiên nghiệm kéo các kỹ năng hiếm về 0).
    """
    n_prior = sum(prior.values()) or 1
    n_g, n_r = sum(group.values()), sum(rest.values())
    out = {}
    for term in set(group) | set(rest):
        a0 = alpha * prior.get(term, 0) / n_prior
        yg, yr = group.get(term, 0) + a0, rest.get(term, 0) + a0
        if yg <= 0 or yr <= 0:
            continue
        delta = math.log(yg / (n_g + alpha - yg)) - math.log(yr / (n_r + alpha - yr))
        var = 1 / yg + 1 / yr
        out[term] = delta / math.sqrt(var)
    return out


def share_table(name: str, skill_sets: list[set[str]], top: int) -> list[dict]:
    n = len(skill_sets)
    cnt = Counter(s for labels in skill_sets for s in labels)
    rows = []
    for skill, k in cnt.most_common(top):
        lo, hi = wilson(k, n)
        rows.append({"skill": skill, "n_jobs": k, "share": k / n, "ci95": [lo, hi]})
    return [{"source": name, "n_total": n, **r} for r in rows]


def fmt_share(name: str, rows: list[dict]) -> str:
    n = rows[0]["n_total"] if rows else 0
    lines = [f"**{name}** ({n} tin)\n", "| # | Kỹ năng | tin | % tin | CI95 |", "|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | {r['skill']} | {r['n_jobs']} | {r['share']:.1%} |" f" [{r['ci95'][0]:.1%}; {r['ci95'][1]:.1%}] |"
        )
    return "\n".join(lines)


def fmt_distinctive(by_group: dict[str, list[tuple[str, float]]], min_jobs: int) -> str:
    lines = [
        "| Nhóm | tin | Kỹ năng đặc trưng (log-odds chuẩn hóa, |z| lớn nhất) |",
        "|---|---|---|",
    ]
    for group, (n, terms) in sorted(by_group.items(), key=lambda kv: -kv[1][0]):
        if n < min_jobs:
            continue
        top = ", ".join(f"{t} ({z:+.1f})" for t, z in terms)
        lines.append(f"| {group} | {n} | {top} |")
    return "\n".join(lines)


def distinctive(groups: dict[str, list[set[str]]], top: int) -> dict[str, tuple[int, list[tuple[str, float]]]]:
    counts = {g: Counter(s for labels in sets for s in labels) for g, sets in groups.items()}
    prior = Counter()
    for c in counts.values():
        prior.update(c)
    out = {}
    for g, c in counts.items():
        rest = Counter()
        for other, oc in counts.items():
            if other != g:
                rest.update(oc)
        z = log_odds_dirichlet(c, rest, prior)
        terms = sorted(z.items(), key=lambda kv: -kv[1])[:top]
        out[g] = (len(groups[g]), terms)
    return out


def agreement(per_source: dict[str, list[set[str]]], top: int) -> str:
    """Cùng một kỹ năng, tỷ lệ tin ở từng nguồn: bảng để lộ thiên lệch nguồn thay vì che nó."""
    shares = {src: Counter(s for labels in sets for s in labels) for src, sets in per_source.items()}
    totals = {src: len(sets) for src, sets in per_source.items()}
    pooled = Counter()
    for c in shares.values():
        pooled.update(c)
    lines = [
        "| Kỹ năng | " + " | ".join(f"% {s} (n={totals[s]})" for s in per_source) + " | chênh lớn nhất |",
        "|---" * (len(per_source) + 2) + "|",
    ]
    for skill, _ in pooled.most_common(top):
        vals = [shares[s].get(skill, 0) / totals[s] for s in per_source]
        lines.append(f"| {skill} | " + " | ".join(f"{v:.1%}" for v in vals) + f" | {max(vals) - min(vals):.1%} |")
    return "\n".join(lines)


def by_month(rows: list[dict], skill_sets: list[set[str]], top: int) -> str:
    months: dict[str, list[set[str]]] = defaultdict(list)
    for r, labels in zip(rows, skill_sets, strict=True):
        d = str(r.get("date_posted") or "")[:7]
        if len(d) == 7:
            months[d].append(labels)
    if not months:
        return "_không có `date_posted`_"
    skills = [s for s, _ in Counter(s for labels in skill_sets for s in labels).most_common(top)]
    lines = ["| Tháng | tin | " + " | ".join(skills) + " |", "|---" * (len(skills) + 2) + "|"]
    for m in sorted(months):
        sets = months[m]
        c = Counter(s for labels in sets for s in labels)
        lines.append(f"| {m} | {len(sets)} | " + " | ".join(f"{c.get(s,0)/len(sets):.0%}" for s in skills) + " |")
    return "\n".join(lines)


# ---------- chạy ----------


def load_crawl(collapse_dup: bool) -> dict[str, list[dict]]:
    import pandas as pd

    out = {}
    for src, path in CRAWL.items():
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        if collapse_dup:
            from crawler.dedup import baseline_key

            df["_k"] = [baseline_key(r.title, r.company_name) for r in df.itertuples()]
            df = df.drop_duplicates("_k", keep="first").drop(columns="_k")
        out[src] = df.to_dict("records")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extractor", choices=["dict", "phobert"], default="dict")
    ap.add_argument("--model", type=Path, default=ROOT / "data" / "models" / "wm2-phobert-selftrain-s1")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--top-distinctive", type=int, default=6)
    ap.add_argument("--min-jobs", type=int, default=20, help="nhóm dưới ngưỡng này không in (số quá nhỏ)")
    ap.add_argument("--all-categories", action="store_true", help="đọc cả VietJobs đủ bộ (CSV 103 MB)")
    ap.add_argument("--collapse-dup", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    catalog = SkillCatalog()
    sources = load_crawl(args.collapse_dup)
    if VIETJOBS_IT.exists():
        import pandas as pd

        sources["vietjobs_it"] = pd.read_parquet(VIETJOBS_IT).to_dict("records")

    extract = skills_dict if args.extractor == "dict" else (lambda rows, cat: skills_phobert(rows, cat, args.model))
    per_source = {src: extract(rows, catalog) for src, rows in sources.items()}
    payload: dict = {"extractor": args.extractor, "collapse_dup": args.collapse_dup, "tables": {}}

    print(f"# Nhu cầu kỹ năng (bộ trích: {args.extractor})\n")
    for src, rows in sources.items():
        got = sum(1 for s in per_source[src] if s)
        print(f"- `{src}`: {len(rows)} tin, {got} tin có ít nhất một kỹ năng ({got/len(rows):.0%})")
    print()

    print("## Bảng 1 – kỹ năng phổ biến nhất, theo từng nguồn\n")
    for src in per_source:
        rows = share_table(src, per_source[src], args.top)
        payload["tables"].setdefault("share", {})[src] = rows
        print(fmt_share(src, rows), "\n")

    print("## Bảng 2 – thiên lệch nguồn: cùng kỹ năng, khác nguồn\n")
    print(agreement(per_source, args.top), "\n")

    print("## Bảng 3 – kỹ năng đặc trưng theo nhóm nghề, TÁCH THEO NGUỒN\n")
    print(
        "> Gộp các nguồn ở bảng này là sai: ITviec gắn một giá trị `category` phẳng cho cả 536 tin,\n"
        "> nên 'nhóm nghề' của bản gộp chỉ là dấu vết nguồn. Chỉ TopCV và VietJobs có cây danh mục thật.\n"
    )
    for src in sources:
        groups: dict[str, list[set[str]]] = defaultdict(list)
        for r, labels in zip(sources[src], per_source[src], strict=True):
            groups[cat_level2(r.get("category"))].append(labels)
        if len(groups) < 2:
            print(f"**{src}**: chỉ có {len(groups)} nhóm (`{list(groups)[0]}`) → không đọc được nhóm nghề\n")
            continue
        dis = distinctive(groups, args.top_distinctive)
        payload["tables"].setdefault("distinctive", {})[src] = {g: {"n": n, "terms": t} for g, (n, t) in dis.items()}
        kept = sum(1 for _, (n, _) in dis.items() if n >= args.min_jobs)
        print(f"**{src}** – {kept}/{len(dis)} nhóm đạt ngưỡng {args.min_jobs} tin\n")
        print(fmt_distinctive(dis, args.min_jobs), "\n")

    print("## Bảng 4 – nhu cầu theo tháng, TÁCH THEO NGUỒN (chỉ tin đang mở lúc crawl)\n")
    print(
        "> Cũng không được gộp: `topcv_20261115` dừng ở 24/10 còn ITviec có tin tháng 11, nên đường tăng của\n"
        "> bản gộp là chuyển nguồn chứ không phải xu hướng thị trường.\n"
    )
    for src in CRAWL:
        if src in sources:
            print(f"**{src}**\n")
            print(by_month(sources[src], per_source[src], 8), "\n")

    if args.all_categories and VIETJOBS_ALL.exists():
        import pandas as pd

        print("## Bảng 5 – kỹ năng đặc trưng theo ngành (VietJobs đủ bộ)\n")
        df = pd.read_csv(
            VIETJOBS_ALL, usecols=["job_title", "description", "requirements_text", "technical_skills", "category"]
        )
        rows = df.to_dict("records")
        sets = skills_dict(rows, catalog)
        gb: dict[str, list[set[str]]] = defaultdict(list)
        for r, labels in zip(rows, sets, strict=True):
            gb[str(r.get("category") or "?")].append(labels)
        dis_all = distinctive(gb, args.top_distinctive)
        payload["tables"]["distinctive_vietjobs"] = {g: {"n": n, "terms": t} for g, (n, t) in dis_all.items()}
        print(f"_{len(rows)} tin, {len(gb)} ngành_\n")
        print(fmt_distinctive(dis_all, args.min_jobs * 5), "\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
