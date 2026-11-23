"""WM5 – gợi ý việc làm: độ phổ biến (baseline) và content-based, đánh giá chia theo thời gian.

    uv run python -m recsys.baseline --snapshot data/crawl/topcv/topcv_20261012.parquet \
        --events data/eval/reco_events.jsonl --eval-set reco_synthetic

Chiến lược:
- `popularity`  : xếp hạng theo số lượt xem trong phần train (không cá nhân hóa) – BASELINE.
- `content-skill`: trùng kỹ năng giữa hồ sơ người dùng và kỹ năng của tin (Jaccard có trọng số IDF). Hai phía
  đều được đưa về tên chuẩn qua từ điển alias trước khi so ("React", "React.js" → ReactJS); tên không có trong
  từ điển thì so theo chữ thường.
- `content-tfidf`: cosine giữa hồ sơ (ghép kỹ năng thành câu) và văn bản tin, TF-IDF n-gram từ.
- `hybrid`      : content-tfidf + 0,1 × điểm phổ biến đã chuẩn hóa.

Kỹ năng của tin lấy từ `skill_tags` (tag nhà tuyển dụng) HOẶC từ file span WM2 nếu truyền `--skills`,
để đo xem đầu ra WM2 có giúp gợi ý tốt hơn tag sẵn có không.

Chia theo thời gian: lượt xem sớm nhất = train, phần sau = test (mặc định 30% cuối theo mốc thời gian).
Metric: Recall@10 và nDCG@10 trung bình trên người dùng có ít nhất 1 lượt xem trong test.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from experiments.runlog import bootstrap_ci, save_run
from common.io import read_jsonl

ROOT = Path(__file__).resolve().parents[1]
K = 10
VERSION = "recsys-content"


def split_time(events: list[dict], test_frac: float) -> tuple[list[dict], list[dict]]:
    """Chia theo mốc thời gian: mọi lượt xem trước mốc là train, từ mốc trở đi là test.

    Mốc lấy theo **phân vị của số lượt xem**, không theo danh sách ngày: ngày đăng dồn về cuối kỳ
    nên chia đều theo ngày sẽ cho train quá nhỏ.

    Thời điểm xem chỉ có độ phân giải **ngày**, nên nhiều lượt xem trùng mốc. Bản cũ lấy phần tử ở vị
    trí phân vị rồi đưa mọi lượt `>= mốc` sang test: khi mốc rơi đúng vào một ngày đông, cả ngày đó sang
    test và tỷ lệ lệch xa mục tiêu (log cũ: mục tiêu 70/30, thực tế 26/74). Giờ chọn trong các **ranh
    giới giữa hai ngày** ranh giới nào cho tỷ lệ train gần mục tiêu nhất.
    """
    stamps = sorted(e["event_ts"] for e in events)
    n = len(stamps)
    target = 1 - test_frac
    days = sorted(set(stamps))
    if len(days) < 2:
        raise ValueError("cần ít nhất hai ngày xem khác nhau để chia theo thời gian")
    # số lượt xem trước mỗi ngày (train = các ngày trước mốc)
    before, i = {}, 0
    for d in days:
        before[d] = i
        while i < n and stamps[i] == d:
            i += 1
    cut = min(days[1:], key=lambda d: abs(before[d] / n - target))
    return [e for e in events if e["event_ts"] < cut], [e for e in events if e["event_ts"] >= cut]


@cache
def _catalog():
    from service.skills import SkillCatalog

    return SkillCatalog()


@cache
def canon_skill(name: str) -> str:
    """Tên kỹ năng → tên chuẩn (chữ thường) theo từ điển alias; không có trong từ điển thì giữ chữ thường."""
    name = name.strip()
    hit = _catalog().lookup(name)
    return (hit.label if hit else name).lower()


def job_skills(df: pd.DataFrame, spans_path: Path | None) -> dict[str, list[str]]:
    """job_uid → danh sách kỹ năng (tag nhà tuyển dụng, hoặc span WM2 nếu có file)."""
    if spans_path:
        out: dict[str, list[str]] = defaultdict(list)
        for line in spans_path.read_text(encoding="utf-8").splitlines():
            if line:
                r = json.loads(line)
                out[r["job_uid"]].extend(canon_skill(x) for x in r.get("skills", []) if x.strip())
        return {k: sorted(set(v)) for k, v in out.items()}
    out = {}
    for r in df.to_dict("records"):
        tags = r.get("skill_tags")
        out[r["job_uid"]] = sorted({canon_skill(str(t)) for t in tags if str(t).strip()}) if tags is not None else []
    return out


def job_text(row: dict) -> str:
    parts = []
    for c in ("title", "skill_tags", "description", "requirements_text"):
        v = row.get(c)
        if v is None:
            continue
        parts.append(" ".join(map(str, v)) if hasattr(v, "__len__") and not isinstance(v, str) else str(v))
    return " ".join(parts)


def rank_popularity(train: list[dict], jobs: list[str]) -> dict[str, float]:
    c = Counter(e["job_uid"] for e in train)
    return {j: float(c.get(j, 0)) for j in jobs}


def idf_weights(skills_by_job: dict[str, list[str]]) -> dict[str, float]:
    n = max(1, len(skills_by_job))
    df_ = Counter(s for v in skills_by_job.values() for s in set(v))
    return {s: math.log(1 + n / (1 + c)) for s, c in df_.items()}


def score_content_skill(profile: list[str], skills_by_job: dict[str, list[str]], idf: dict[str, float]) -> dict:
    p = {canon_skill(s) for s in profile if s.strip()}
    out = {}
    for j, sk in skills_by_job.items():
        js = {canon_skill(s) for s in sk}
        inter = p & js
        union = p | js
        out[j] = sum(idf.get(s, 1.0) for s in inter) / (len(union) or 1)
    return out


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int = K) -> float:
    dcg = sum(1 / math.log2(i + 2) for i, j in enumerate(ranked[:k]) if j in relevant)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / ideal if ideal else 0.0


def evaluate(
    users: list[dict],
    scorers: dict[str, object],
    seen_train: dict[str, set[str]],
    truth: dict[str, set[str]],
) -> tuple[dict[str, dict[str, float]], dict[str, list[tuple[float, float]]]]:
    per_user: dict[str, list[tuple[float, float]]] = {name: [] for name in scorers}
    for u in users:
        rel = truth[u["user_id"]]
        if not rel:
            continue
        for name, fn in scorers.items():
            scores = fn(u)
            ranked = [j for j, _ in sorted(scores.items(), key=lambda kv: -kv[1]) if j not in seen_train[u["user_id"]]]
            top = ranked[:K]
            per_user[name].append((len(set(top) & rel) / len(rel), ndcg_at_k(ranked, rel)))
    res = {}
    for name, vals in per_user.items():
        res[name] = {
            "recall@10": sum(v[0] for v in vals) / max(1, len(vals)),
            "ndcg@10": sum(v[1] for v in vals) / max(1, len(vals)),
            "n_users": len(vals),
        }
    return res, per_user


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, default=ROOT / "data" / "crawl" / "topcv" / "topcv_20261012.parquet")
    ap.add_argument("--events", type=Path, default=ROOT / "data" / "eval" / "reco_events.jsonl")
    ap.add_argument("--skills", type=Path, help="JSONL {job_uid, skills[]} từ WM2 (mặc định: dùng skill_tags)")
    ap.add_argument("--test-frac", type=float, default=0.3)
    ap.add_argument("--eval-set")
    ap.add_argument("--snapshot-name", default="topcv_20261012")
    args = ap.parse_args()

    df = pd.read_parquet(args.snapshot).drop_duplicates("job_uid")
    events = read_jsonl(args.events)
    train, test = split_time(events, args.test_frac)
    jobs = list(df["job_uid"])
    skills_by_job = job_skills(df, args.skills)
    idf = idf_weights(skills_by_job)

    users = list({e["user_id"]: {"user_id": e["user_id"], "skills": e["skills"]} for e in events}.values())
    seen_train = defaultdict(set)
    for e in train:
        seen_train[e["user_id"]].add(e["job_uid"])
    truth = defaultdict(set)
    for e in test:
        if e["job_uid"] not in seen_train[e["user_id"]]:
            truth[e["user_id"]].add(e["job_uid"])

    pop = rank_popularity(train, jobs)
    pop_max = max(pop.values()) or 1.0
    texts = [job_text(r) for r in df.to_dict("records")]
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000)
    mat = vec.fit_transform(texts)

    def tfidf_scores(u: dict) -> dict[str, float]:
        q = vec.transform([" ".join(u["skills"])])
        sims = cosine_similarity(q, mat)[0]
        return dict(zip(jobs, sims, strict=True))

    scorers = {
        "popularity": lambda u: pop,
        "content-skill": lambda u: score_content_skill(u["skills"], skills_by_job, idf),
        "content-tfidf": tfidf_scores,
        "hybrid": lambda u: {j: s + 0.1 * pop[j] / pop_max for j, s in tfidf_scores(u).items()},
    }
    res, per_user = evaluate(users, scorers, seen_train, truth)

    n_eval = res["popularity"]["n_users"]
    print(f"{len(events)} lượt xem: train {len(train)} / test {len(test)}; {n_eval} người dùng có nhãn test")
    for name, m in res.items():
        print(f"  {name:14s} Recall@10={m['recall@10']:.3f} nDCG@10={m['ndcg@10']:.3f}")

    if args.eval_set:
        for name, m in res.items():
            vals = per_user[name]
            ci = bootstrap_ci(len(vals), lambda ix, v=vals: sum(v[i][1] for i in ix) / max(1, len(ix)))
            save_run(
                task="WM5",
                rq="RQ5",
                method=name if name == "popularity" else f"{name}-{VERSION}",
                baseline_of=None if name == "popularity" else "popularity",
                eval_set=args.eval_set,
                split="test",
                snapshot=args.snapshot_name,
                metrics={"recall@10": m["recall@10"], "ndcg@10": m["ndcg@10"]},
                ci95={"ndcg@10": ci},
                ids=sorted(truth),
            )
        print(f"→ experiments/runs/ ({len(res)} run)")


if __name__ == "__main__":
    main()
