"""WM5 – chấm tay gợi ý việc làm: người chấm không biết phương pháp nào gợi ý tin nào.

    uv run python -m recsys.judge_kit make --profiles data/eval/wm5_profiles.csv     # → phiếu chấm + khóa
    # người chấm điền cột `grade` (0 không hợp, 1 hợp một phần, 2 hợp) trong data/eval/wm5_judge.xlsx
    uv run python -m recsys.judge_kit score                                          # nDCG@10 từng phương pháp
    uv run python -m recsys.judge_kit kappa-make --n 50   # phiếu cho người chấm thứ hai (không kèm điểm người 1)
    uv run python -m recsys.judge_kit kappa               # Cohen's κ giữa hai người

- Hồ sơ (`--profiles`): CSV `profile_id,skills,note`; `skills` cách nhau bằng dấu `;`. Hồ sơ do nhóm soạn trước
  khi xem gợi ý, không sửa sau khi đã thấy kết quả.
- Mỗi hồ sơ lấy top-10 của từng phương pháp, gộp lại (tin trùng chỉ chấm một lần), xáo thứ tự với seed cố định.
  Phương pháp nào gợi ý tin nào nằm ở file khóa riêng, người chấm không mở file đó.
- Phương pháp: `popularity` (số lượt xem trong log synthetic), `content-skill` (trùng kỹ năng có trọng số IDF),
  `content-tfidf` (cosine TF-IDF giữa hồ sơ và văn bản tin), `hybrid` (TF-IDF + 0,1 × độ phổ biến) – giống hệt
  `recsys.baseline`.
- nDCG@10 dùng điểm 0/1/2 làm gain; ideal tính trên mọi tin đã chấm của hồ sơ đó (gộp các phương pháp). So hai
  phương pháp bằng bootstrap ghép cặp theo hồ sơ.
- Phiếu chấm là file Excel (.xlsx), mọi ô ghi dạng chữ: CSV mở bằng Excel sẽ hiểu mô tả bắt đầu bằng "-" là công
  thức (#NAME?) và có thể làm hỏng dữ liệu khi lưu lại.
- File hồ sơ, phiếu chấm, khóa nằm trong data/ (không commit).
"""

from __future__ import annotations

from common.io import read_jsonl

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import pandas as pd

from recsys.baseline import (
    K,
    idf_weights,
    job_skills,
    job_text,
    rank_popularity,
    score_content_skill,
    split_time,
)

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "data" / "eval"
SNAPSHOT = ROOT / "data" / "crawl" / "topcv" / "topcv_20261012.parquet"
EVENTS = EVAL / "reco_events.jsonl"
JUDGE = EVAL / "wm5_judge.xlsx"
KEY = EVAL / "wm5_judge_key.json"
JUDGE2 = EVAL / "wm5_judge_k2.xlsx"
KAPPA_SEED = 20261122
SEED = 20261120
DESC_CHARS = 400


def read_profiles(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [
        {"profile_id": r["profile_id"], "skills": [s.strip() for s in r["skills"].split(";") if s.strip()]}
        for r in rows
    ]


def scorers(df: pd.DataFrame, skills_path: Path | None) -> dict:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    jobs = list(df["job_uid"])
    train, _ = split_time(read_jsonl(EVENTS), 0.3)
    pop = rank_popularity(train, jobs)
    pop_max = max(pop.values()) or 1.0
    skills_by_job = job_skills(df, skills_path)
    idf = idf_weights(skills_by_job)
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000)
    mat = vec.fit_transform([job_text(r) for r in df.to_dict("records")])

    def tfidf(p: list[str]) -> dict[str, float]:
        sims = cosine_similarity(vec.transform([" ".join(p)]), mat)[0]
        return dict(zip(jobs, sims, strict=True))

    return {
        "popularity": lambda p: pop,
        "content-skill": lambda p: score_content_skill(p, skills_by_job, idf),
        "content-tfidf": tfidf,
        "hybrid": lambda p: {j: s + 0.1 * pop[j] / pop_max for j, s in tfidf(p).items()},
    }


def top_k(scores: dict[str, float]) -> list[str]:
    # hòa điểm: xếp theo job_uid để tất định
    return [j for j, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:K]]


def cmd_make(args) -> None:
    df = pd.read_parquet(args.snapshot).drop_duplicates("job_uid")
    info = df.set_index("job_uid")
    fns = scorers(df, args.skills)
    rng = random.Random(SEED)
    key: dict[str, dict[str, list[str]]] = {}
    rows = []
    for prof in read_profiles(args.profiles):
        ranked = {name: top_k(fn(prof["skills"])) for name, fn in fns.items()}
        key[prof["profile_id"]] = ranked
        pool = sorted({j for lst in ranked.values() for j in lst})
        rng.shuffle(pool)
        for j in pool:
            r = info.loc[j]
            tags = r.get("skill_tags")
            rows.append(
                {
                    "profile_id": prof["profile_id"],
                    "profile_skills": "; ".join(prof["skills"]),
                    "job_uid": j,
                    "title": r.get("title"),
                    "company": r.get("company_name"),
                    "tags": "; ".join(map(str, tags)) if tags is not None else "",
                    "description": str(r.get("description") or "")[:DESC_CHARS].replace("\n", " "),
                    "grade": "",
                }
            )
    if JUDGE.exists() and not args.force:
        raise SystemExit(f"{JUDGE} đã có (có thể đã chấm) – dùng --force nếu chắc chắn muốn tạo lại")
    write_sheet(rows, JUDGE)
    KEY.write_text(json.dumps({"seed": SEED, "snapshot": str(args.snapshot), "key": key}, ensure_ascii=False), "utf-8")
    n_prof = len(key)
    print(f"{n_prof} hồ sơ, {len(rows)} dòng cần chấm (trung bình {len(rows) / max(1, n_prof):.1f}/hồ sơ) → {JUDGE}")
    print(f"khóa (người chấm không mở): {KEY}")


WIDTHS = {
    "profile_id": 8,
    "profile_skills": 28,
    "job_uid": 10,
    "title": 32,
    "company": 22,
    "tags": 28,
    "description": 70,
    "grade": 7,
}


def write_sheet(rows: list[dict], path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "cham"
    cols = list(rows[0])
    ws.append(cols)
    for r in rows:
        ws.append(["" if r[c] is None else str(r[c]) for c in cols])
    for i, c in enumerate(cols, 1):
        letter = ws.cell(1, i).column_letter
        ws.column_dimensions[letter].width = WIDTHS.get(c, 15)
        ws.cell(1, i).font = Font(bold=True)
        for cell in ws[letter][1:]:
            cell.data_type = "s"  # luôn là chữ, không phải công thức hay số
            cell.alignment = Alignment(wrap_text=c != "job_uid", vertical="top")
    g = ws.cell(1, cols.index("grade") + 1).column_letter
    dv = DataValidation(type="list", formula1='"0,1,2"', allow_blank=True)
    dv.add(f"{g}2:{g}{len(rows) + 1}")
    ws.add_data_validation(dv)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


def read_sheet(path: Path) -> list[dict]:
    from openpyxl import load_workbook

    ws = load_workbook(path, read_only=True).active
    it = ws.iter_rows(values_only=True)
    cols = [str(c) for c in next(it)]
    return [{c: "" if v is None else str(v) for c, v in zip(cols, row, strict=False)} for row in it]


def ndcg(ranked: list[str], grades: dict[str, int]) -> float:
    dcg = sum((2 ** grades.get(j, 0) - 1) / math.log2(i + 2) for i, j in enumerate(ranked[:K]))
    ideal_g = sorted(grades.values(), reverse=True)[:K]
    idcg = sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(ideal_g))
    return dcg / idcg if idcg else 0.0


def cmd_score(args) -> None:
    key = json.loads(KEY.read_text("utf-8"))["key"]
    grades: dict[str, dict[str, int]] = defaultdict(dict)
    missing = 0
    for r in read_sheet(JUDGE):
        g = r["grade"].strip()
        if g == "":
            missing += 1
            continue
        grades[r["profile_id"]][r["job_uid"]] = int(float(g))
    if missing:
        print(f"CẢNH BÁO: {missing} dòng chưa chấm – các tin đó tính là 0")
    methods = list(next(iter(key.values())))
    per = {m: [ndcg(key[p][m], grades[p]) for p in key] for m in methods}
    prec = {m: [sum(grades[p].get(j, 0) >= 1 for j in key[p][m]) / K for p in key] for m in methods}
    print(f"{len(key)} hồ sơ")
    for m in methods:
        print(f"  {m:14s} nDCG@10={sum(per[m]) / len(per[m]):.3f}  P@10(điểm ≥ 1)={sum(prec[m]) / len(prec[m]):.3f}")
    rng = random.Random(SEED)
    base = args.baseline
    n = len(key)
    for m in methods:
        if m == base:
            continue
        diffs = [a - b for a, b in zip(per[m], per[base], strict=True)]
        boots = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(1000))
        print(f"  Δ nDCG {m} − {base}: {sum(diffs) / n:+.3f}, CI95 [{boots[24]:+.3f}; {boots[974]:+.3f}]")


def cmd_kappa_make(args) -> None:
    rows = read_sheet(JUDGE)
    sample = random.Random(KAPPA_SEED).sample(rows, min(args.n, len(rows)))
    if JUDGE2.exists() and not args.force:
        raise SystemExit(f"{JUDGE2} đã có (có thể đã chấm) – dùng --force nếu chắc chắn muốn tạo lại")
    write_sheet([{**r, "grade": ""} for r in sample], JUDGE2)
    print(f"{len(sample)} dòng (seed {KAPPA_SEED}), cột grade để trống → {JUDGE2}")


def kappa_scores(a: list[int], b: list[int]) -> dict[str, float]:
    from sklearn.metrics import cohen_kappa_score

    return {
        "κ 3 mức (0/1/2)": cohen_kappa_score(a, b, labels=[0, 1, 2]),
        "κ trọng số tuyến tính": cohen_kappa_score(a, b, labels=[0, 1, 2], weights="linear"),
        "κ hợp/không (≥ 1)": cohen_kappa_score([x >= 1 for x in a], [x >= 1 for x in b]),
    }


def cmd_kappa(_args) -> None:
    first = {(r["profile_id"], r["job_uid"]): int(float(r["grade"])) for r in read_sheet(JUDGE) if r["grade"].strip()}
    pairs = [
        (first[(r["profile_id"], r["job_uid"])], int(float(r["grade"])))
        for r in read_sheet(JUDGE2)
        if r["grade"].strip() and (r["profile_id"], r["job_uid"]) in first
    ]
    a, b = [x for x, _ in pairs], [y for _, y in pairs]
    agree = sum(x == y for x, y in pairs)
    print(f"{len(pairs)} dòng cả hai cùng chấm; trùng điểm {agree} ({agree / max(1, len(pairs)):.0%})")
    for name, k in kappa_scores(a, b).items():
        print(f"  {name}: {k:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--profiles", type=Path, required=True)
    m.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    m.add_argument("--skills", type=Path, help="JSONL {job_uid, skills[]} từ WM2 (mặc định: tag nhà tuyển dụng)")
    m.add_argument("--force", action="store_true")
    s = sub.add_parser("score")
    s.add_argument("--baseline", default="popularity")
    km = sub.add_parser("kappa-make")
    km.add_argument("--n", type=int, default=50)
    km.add_argument("--force", action="store_true")
    sub.add_parser("kappa")
    args = ap.parse_args()
    cmds = {"make": cmd_make, "score": cmd_score, "kappa-make": cmd_kappa_make, "kappa": cmd_kappa}
    cmds[args.cmd](args)


if __name__ == "__main__":
    main()
