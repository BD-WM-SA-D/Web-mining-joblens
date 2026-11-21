"""WM5 – chấm tay gợi ý việc làm: người chấm không biết phương pháp nào gợi ý tin nào.

    uv run python -m recsys.judge_kit make --profiles data/eval/wm5_profiles.csv     # → phiếu chấm + khóa
    # người chấm điền cột `grade` (0 không hợp, 1 hợp một phần, 2 hợp) trong data/eval/wm5_judge.csv
    uv run python -m recsys.judge_kit score                                          # nDCG@10 từng phương pháp

- Hồ sơ (`--profiles`): CSV `profile_id,skills,note`; `skills` cách nhau bằng dấu `;`. Hồ sơ do nhóm soạn trước
  khi xem gợi ý, không sửa sau khi đã thấy kết quả.
- Mỗi hồ sơ lấy top-10 của từng phương pháp, gộp lại (tin trùng chỉ chấm một lần), xáo thứ tự với seed cố định.
  Phương pháp nào gợi ý tin nào nằm ở file khóa riêng, người chấm không mở file đó.
- Phương pháp: `popularity` (số lượt xem trong log synthetic), `content-skill` (trùng kỹ năng có trọng số IDF),
  `content-tfidf` (cosine TF-IDF giữa hồ sơ và văn bản tin), `hybrid` (TF-IDF + 0,1 × độ phổ biến) – giống hệt
  `recsys.baseline`.
- nDCG@10 dùng điểm 0/1/2 làm gain; ideal tính trên mọi tin đã chấm của hồ sơ đó (gộp các phương pháp). So hai
  phương pháp bằng bootstrap ghép cặp theo hồ sơ.
- File hồ sơ, phiếu chấm, khóa nằm trong data/ (không commit).
"""

from __future__ import annotations

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
    load_events,
    rank_popularity,
    score_content_skill,
    split_time,
)

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "data" / "eval"
SNAPSHOT = ROOT / "data" / "crawl" / "topcv" / "topcv_20261012.parquet"
EVENTS = EVAL / "reco_events.jsonl"
JUDGE = EVAL / "wm5_judge.csv"
KEY = EVAL / "wm5_judge_key.json"
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
    train, _ = split_time(load_events(EVENTS), 0.3)
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
    with JUDGE.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    KEY.write_text(json.dumps({"seed": SEED, "snapshot": str(args.snapshot), "key": key}, ensure_ascii=False), "utf-8")
    n_prof = len(key)
    print(f"{n_prof} hồ sơ, {len(rows)} dòng cần chấm (trung bình {len(rows) / max(1, n_prof):.1f}/hồ sơ) → {JUDGE}")
    print(f"khóa (người chấm không mở): {KEY}")


def ndcg(ranked: list[str], grades: dict[str, int]) -> float:
    dcg = sum((2 ** grades.get(j, 0) - 1) / math.log2(i + 2) for i, j in enumerate(ranked[:K]))
    ideal_g = sorted(grades.values(), reverse=True)[:K]
    idcg = sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(ideal_g))
    return dcg / idcg if idcg else 0.0


def cmd_score(args) -> None:
    key = json.loads(KEY.read_text("utf-8"))["key"]
    grades: dict[str, dict[str, int]] = defaultdict(dict)
    missing = 0
    with JUDGE.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            g = r["grade"].strip()
            if g == "":
                missing += 1
                continue
            grades[r["profile_id"]][r["job_uid"]] = int(g)
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
    args = ap.parse_args()
    cmd_make(args) if args.cmd == "make" else cmd_score(args)


if __name__ == "__main__":
    main()
