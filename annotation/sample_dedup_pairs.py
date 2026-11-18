"""Rút cặp tin để gán nhãn trùng/không trùng (WM1).

    uv run python -m annotation.sample_dedup_pairs --snapshots data/crawl/topcv/topcv_v1.parquet \
        data/crawl/itviec-jobs/itviec_v1.parquet --n 300

Sinh trong data/annotation/ (không commit):
    dedup_batch1.labelstudio.json   nhập vào Label Studio (cấu hình: annotation/label_studio_dedup.xml)
    dedup_batch1.manifest.json      seed, snapshot, danh sách cặp đã rút

**Rút theo tầng, không rút ngẫu nhiên.** Lấy ngẫu nhiên từ mọi cặp có thể thì gần như 100% là cặp
không trùng (304 tin TopCV cho ~46.000 cặp, chỉ ~6 cặp đáng ngờ) → tập nhãn vô dụng.
Bốn tầng, trộn đều để người gán không đoán được tầng:

| Tầng | Lấy từ đâu | Vì sao cần |
|---|---|---|
| `baseline` | cặp cùng khóa tiêu đề + công ty | cặp baseline cho là trùng – đo precision của baseline |
| `minhash_high` | Jaccard ≥ 0,5 | cặp MinHash chắc chắn – đo precision của MinHash |
| `minhash_low` | 0,2 ≤ Jaccard < 0,5 | vùng ranh giới, quyết định ngưỡng |
| `same_company` | cùng công ty, hai tin khác nhau, không thuộc tầng trên | **cặp âm khó**: cùng công ty nhưng khác vị trí |

**Giới hạn lặp** (sửa 2026-11-17): một tin vào tối đa `MAX_PER_JOB` cặp, một công ty tối đa
`MAX_PER_COMPANY` cặp. Bản đầu không giới hạn: tầng `same_company` ghép mọi tin của một công ty với
nhau (15 tin → 105 cặp), nên MB Bank chiếm 72/300 cặp, LG CNS 73, có tin lặp trong 12 cặp – người gán
đọc đi đọc lại một tin và số đo phản ánh cách vài công ty đăng tin chứ không phải cả tập.
Không giới hạn tầng `baseline`, `minhash_high` (ít, và là nơi có cặp trùng); cặp **khác nguồn** không
tính giới hạn công ty (đó là câu hỏi chính của WM1), chỉ tính giới hạn mỗi tin.

Tầng `same_company` quan trọng nhất cho recall: nếu chỉ gán cặp do thuật toán đề xuất thì không bao giờ
biết thuật toán **bỏ sót** bao nhiêu. Cặp cùng công ty là nơi tin trùng thật hay nằm.
Ưu tiên cặp **khác nguồn** (TopCV ↔ ITviec) vì đó là câu hỏi chính của WM1.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from crawler.dedup import baseline_pairs, minhash_pairs, norm_company

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "annotation"
HIGH = 0.5
LOW = 0.2
STRATA = ("baseline", "minhash_high", "minhash_low", "same_company")
MAX_PER_JOB = 3
MAX_PER_COMPANY = 15
UNCAPPED = ("baseline", "minhash_high")


def same_company_pairs(df: pd.DataFrame, exclude: set[tuple[str, str]]) -> list[tuple[str, str]]:
    """Cặp hai tin khác nhau của cùng một công ty, chưa nằm trong tầng nào khác."""
    by_company: dict[str, list[str]] = defaultdict(list)
    for r in df.to_dict("records"):
        by_company[norm_company(r["company_name"])].append(r["job_uid"])
    out = []
    for uids in by_company.values():
        for i, a in enumerate(uids):
            for b in uids[i + 1 :]:
                key = (a, b) if a < b else (b, a)
                if key not in exclude:
                    out.append(key)
    return out


def build_strata(df: pd.DataFrame) -> dict[str, list[tuple[str, str]]]:
    base = baseline_pairs(df)
    mh = minhash_pairs(df, LOW)
    strata = {
        "baseline": sorted(base),
        "minhash_high": sorted(p for p, j in mh.items() if j >= HIGH and p not in base),
        "minhash_low": sorted(p for p, j in mh.items() if j < HIGH and p not in base),
    }
    used = set(base) | set(mh)
    strata["same_company"] = same_company_pairs(df, used)
    return strata


def pick(
    strata: dict[str, list[tuple[str, str]]],
    n: int,
    rng: random.Random,
    src: dict[str, str],
    company: dict[str, str] | None = None,
    keep: list[dict] | tuple = (),
    max_per_job: int = MAX_PER_JOB,
    max_per_company: int = MAX_PER_COMPANY,
) -> list[dict]:
    """Chia đều n cặp cho các tầng; tầng thiếu thì phần dư chia cho tầng còn lại.

    `company`: job_uid → tên công ty đã chuẩn hóa, dùng cho giới hạn mỗi công ty.
    `keep`: cặp đã gán nhãn, giữ nguyên (tính vào hạn mức tầng và vào giới hạn lặp).
    """
    company = company or {}
    job_n: Counter[str] = Counter()
    comp_n: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    chosen: list[tuple[str, tuple[str, str]]] = []

    def comps(p: tuple[str, str]) -> set[str]:
        return {company.get(p[0], ""), company.get(p[1], "")} - {""}

    def fits(name: str, p: tuple[str, str]) -> bool:
        if p in seen:
            return False
        if name in UNCAPPED:
            return True
        if job_n[p[0]] >= max_per_job or job_n[p[1]] >= max_per_job:
            return False
        cross = src[p[0]] != src[p[1]]
        return cross or all(comp_n[c] < max_per_company for c in comps(p))

    def add(name: str, p: tuple[str, str]) -> None:
        seen.add(p)
        job_n.update(p)
        if src[p[0]] == src[p[1]]:
            comp_n.update(comps(p))
        chosen.append((name, p))

    kept = Counter()
    for k in keep:
        add(k["stratum"], (k["a"], k["b"]))
        kept[k["stratum"]] += 1

    remaining = n
    todo = [s for s in STRATA if strata.get(s) or kept[s]]
    for i, name in enumerate(todo):
        quota = remaining // (len(todo) - i)
        pool = list(strata.get(name, []))
        # ưu tiên cặp khác nguồn – đó là câu hỏi chính của WM1; trong mỗi nhóm rút ngẫu nhiên
        cross = [p for p in pool if src[p[0]] != src[p[1]]]
        rest = [p for p in pool if src[p[0]] == src[p[1]]]
        rng.shuffle(cross)
        rng.shuffle(rest)
        taken = kept[name]
        for p in cross + rest:
            if taken >= quota:
                break
            if fits(name, p):
                add(name, p)
                taken += 1
        remaining -= taken
    rng.shuffle(chosen)  # trộn để người gán không đoán được tầng
    return [{"stratum": s, "a": p[0], "b": p[1]} for s, p in chosen]


def to_label_studio(pairs: list[dict], df: pd.DataFrame) -> list[dict]:
    """Task cho Label Studio – **không** có `stratum`.

    Label Studio hiện mọi trường trong `data` ở bảng danh sách task, nên để `stratum` ở đây là
    người gán thấy được cặp đến từ tầng nào và có thể đoán theo tầng (cặp `minhash_high` dễ bị
    gán "trùng" chỉ vì thuật toán đã đề xuất). Tầng nằm trong manifest, khớp lại bằng `index`.
    """
    info = df.set_index("job_uid")
    out = []
    for i, p in enumerate(pairs):
        ra, rb = info.loc[p["a"]], info.loc[p["b"]]
        out.append(
            {
                "data": {
                    "pair_id": f"{p['a'][:8]}-{p['b'][:8]}",
                    "index": i,
                    "job_uid_a": p["a"],
                    "job_uid_b": p["b"],
                    "source_a": ra["source"],
                    "source_b": rb["source"],
                    "title_a": ra["title"],
                    "title_b": rb["title"],
                    "company_a": ra["company_name"],
                    "company_b": rb["company_name"],
                    "text_a": (ra["description"] or "")[:1500],
                    "text_b": (rb["description"] or "")[:1500],
                }
            }
        )
    return out


def _rel(p: Path) -> str:
    """Đường dẫn tương đối với gốc repo nếu được, không thì giữ nguyên (chạy từ thư mục khác)."""
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", nargs="+", type=Path, required=True)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20261113)
    ap.add_argument("--batch", default="dedup_batch1")
    ap.add_argument("--keep", type=Path, help="JSON danh sách {stratum, a, b} đã gán nhãn – giữ nguyên khi rút lại")
    args = ap.parse_args()

    df = pd.concat([pd.read_parquet(p) for p in args.snapshots], ignore_index=True).drop_duplicates("job_uid")
    src = dict(zip(df["job_uid"], df["source"], strict=True))
    strata = build_strata(df)
    print(f"{len(df)} tin ({df['source'].value_counts().to_dict()})")
    for name in STRATA:
        pool = strata.get(name, [])
        cross = sum(1 for p in pool if src[p[0]] != src[p[1]])
        print(f"  {name:14s} {len(pool):7d} cặp (khác nguồn: {cross})")

    company = {u: norm_company(c) for u, c in zip(df["job_uid"], df["company_name"], strict=True)}
    keep = json.loads(args.keep.read_text("utf-8")) if args.keep else []
    pairs = pick(strata, args.n, random.Random(args.seed), src, company, keep)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{args.batch}.labelstudio.json").write_text(
        json.dumps(to_label_studio(pairs, df), ensure_ascii=False, indent=1), "utf-8"
    )
    manifest = {
        "batch": args.batch,
        "seed": args.seed,
        "snapshots": [_rel(p) for p in args.snapshots],
        "n_pairs": len(pairs),
        "by_stratum": {s: sum(1 for p in pairs if p["stratum"] == s) for s in STRATA},
        "cross_source": sum(1 for p in pairs if src[p["a"]] != src[p["b"]]),
        "max_per_job": MAX_PER_JOB,
        "max_per_company": MAX_PER_COMPANY,
        "kept_labeled": len(keep),
        "pairs": pairs,
    }
    (OUT_DIR / f"{args.batch}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    print({k: v for k, v in manifest.items() if k != "pairs"})


if __name__ == "__main__":
    main()
