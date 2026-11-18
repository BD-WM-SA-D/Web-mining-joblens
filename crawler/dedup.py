"""WM1 – phát hiện tin đăng trùng (trong một trang và giữa các trang).

    uv run python -m crawler.dedup --snapshots data/crawl/topcv/topcv_v1.parquet
    uv run python -m crawler.dedup --snapshots <p1> <p2> --threshold 0.5 --out data/eval/dedup_candidates.csv

Hai tầng, từ dễ đến khó (báo cáo cả hai):
1. Baseline `title+company`: chuẩn hóa tiêu đề + tên công ty (chữ thường, bỏ dấu câu, bỏ hậu tố
   "tuyển gấp"/"lương upto…"), hai tin trùng nếu khóa giống hệt nhau.
2. MinHash LSH trên shingle từ (n-gram 3 từ) của title + mô tả + yêu cầu: bắt tin giống nội dung
   dù tiêu đề viết khác; LSH để khỏi so từng cặp O(n²).

v2 (2026-11-18, đăng ký trước trong experiments/results.md):
- `soft=True`: khóa baseline bỏ thêm từ chỉ hình thức làm việc / địa điểm ("On-site", "Remote", "Hà Nội"…),
  giữ cấp bậc. Sửa loại bỏ sót "Data Science Intern On-site" ↔ "Data Science Intern".
- `strip=True`: bỏ **khung công ty** trước MinHash – shingle có ở ≥ 50% số tin của cùng (nguồn, công ty),
  với công ty có ≥ 3 tin. Sửa loại báo nhầm "Android Engineer" ↔ "iOS Engineer" chung đoạn giới thiệu.

Kết quả: danh sách cặp ứng viên kèm điểm Jaccard ước lượng và nhãn nguồn (cùng trang / khác trang).
Cặp ứng viên chỉ là *ứng viên* – nhãn trùng/không trùng do người gán (300 cặp, xem experiments/results.md).
"""

from __future__ import annotations

import argparse
import itertools
import re
import unicodedata
from pathlib import Path

import pandas as pd
from datasketch import MinHash, MinHashLSH

NUM_PERM = 128
SHINGLE_N = 3
# đuôi quảng cáo hay gắn vào tiêu đề, bỏ trước khi so khớp baseline
AD_TAIL_RE = re.compile(
    r"[\(\[\-–|,]?\s*(tuyển gấp|gấp|urgent|hot|thu nhập.*|lương.*|upto.*|up to.*|salary.*|đi làm ngay.*)\s*[\)\]]?\s*$",
    re.IGNORECASE,
)
PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
WS_RE = re.compile(r"\s+")
# Tiền tố/hậu tố pháp lý: TopCV ghi tên đầy đủ ("công ty tnhh lg cns việt nam"),
# ITviec ghi tên thương hiệu ("lg cns việt nam") → phải bỏ mới khớp được công ty giữa hai trang.
COMPANY_AFFIX_RE = re.compile(
    r"^(tổng |tong |tập đoàn |tap doan |cong ty |công ty |cty |ngan hang |ngân hàng |"
    r"tnhh |co phan |cổ phần |mtv |một thành viên |mot thanh vien |"
    r"quốc tế |quoc te |đầu tư |dau tu |phát triển |phat trien |"
    r"ltd |co ltd |jsc |corp |corporation |inc |company |group |vietnam |việt nam )+"
)
# v2: từ không làm đổi vị trí – áp lên tiêu đề đã `norm` (nên "on-site" đã thành "on site")
SOFT_TITLE_RE = re.compile(
    r"\b(on site|onsite|remote|hybrid|wfh|work from home|hà nội|ha noi|hanoi|hn|hồ chí minh|ho chi minh|"
    r"tp hcm|tphcm|hcm|sài gòn|saigon|đà nẵng|da nang|danang|việt nam|vietnam|tại)\b"
)
BOILER_MIN_JOBS = 3
BOILER_FRAC = 0.5
COMPANY_TAIL_RE = re.compile(r"( co ltd| ltd| jsc| inc| corp| corporation| company| group| pte| llc)+$")


def norm(text: str | None) -> str:
    """Chuẩn hóa để so khớp: NFC, chữ thường, bỏ dấu câu, gộp khoảng trắng."""
    s = unicodedata.normalize("NFC", text or "").lower()
    s = PUNCT_RE.sub(" ", s)
    return WS_RE.sub(" ", s).strip()


def norm_company(name: str | None) -> str:
    """Tên công ty đã bỏ tiền tố/hậu tố pháp lý, để so được giữa TopCV và ITviec.

    "Công ty TNHH LG CNS Việt Nam" và "LG CNS Việt Nam" → cùng "lg cns".
    Bỏ lặp nhiều lần vì tiền tố hay chồng nhau ("tổng công ty cổ phần …").
    """
    s = norm(name)
    for _ in range(4):
        new = COMPANY_TAIL_RE.sub("", COMPANY_AFFIX_RE.sub("", s)).strip()
        if new == s:
            break
        s = new
    return s or norm(name)


def baseline_key(title: str | None, company: str | None) -> str:
    """Khóa baseline: tiêu đề đã cắt đuôi quảng cáo + tên công ty đã chuẩn hoá."""
    t = AD_TAIL_RE.sub("", title or "").strip()
    return f"{norm(t)}||{norm_company(company)}"


def soft_title_key(title: str | None, company: str | None) -> str:
    """Khóa baseline mềm: như `baseline_key` nhưng bỏ thêm hình thức làm việc và địa điểm."""
    t = norm(AD_TAIL_RE.sub("", title or "").strip())
    t = WS_RE.sub(" ", SOFT_TITLE_RE.sub(" ", t)).strip()
    return f"{t}||{norm_company(company)}"


def shingles(text: str, n: int = SHINGLE_N) -> set[str]:
    words = norm(text).split()
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def doc_text(row: dict) -> str:
    return " ".join(str(row.get(c) or "") for c in ("title", "description", "requirements_text"))


def minhash_of(sh: set[str]) -> MinHash:
    m = MinHash(num_perm=NUM_PERM)
    for s in sh:
        m.update(s.encode("utf-8"))
    return m


def shingle_sets(df: pd.DataFrame, strip: bool = False) -> dict[str, set[str]]:
    """Shingle của mỗi tin; `strip=True` bỏ khung công ty (xem docstring module)."""
    records = df.to_dict("records")
    sets = {r["job_uid"]: shingles(doc_text(r)) for r in records}
    if not strip:
        return sets
    groups: dict[tuple[str, str], list[str]] = {}
    for r in records:
        groups.setdefault((r["source"], norm_company(r["company_name"])), []).append(r["job_uid"])
    out = dict(sets)
    for uids in groups.values():
        if len(uids) < BOILER_MIN_JOBS:
            continue
        freq: dict[str, int] = {}
        for u in uids:
            for s in sets[u]:
                freq[s] = freq.get(s, 0) + 1
        boiler = {s for s, c in freq.items() if c >= BOILER_FRAC * len(uids)}
        for u in uids:
            kept = sets[u] - boiler
            out[u] = kept or sets[u]  # cắt hết thì giữ tập đầy đủ
    return out


def baseline_pairs(df: pd.DataFrame, soft: bool = False) -> set[tuple[str, str]]:
    """Cặp job_uid có cùng khóa tiêu đề + công ty (`soft=True`: khóa mềm v2)."""
    key = soft_title_key if soft else baseline_key
    pairs: set[tuple[str, str]] = set()
    by_key: dict[str, list[str]] = {}
    for r in df.to_dict("records"):
        by_key.setdefault(key(r["title"], r["company_name"]), []).append(r["job_uid"])
    for uids in by_key.values():
        pairs.update(tuple(sorted(p)) for p in itertools.combinations(uids, 2))
    return pairs


def minhash_pairs(df: pd.DataFrame, threshold: float, strip: bool = False) -> dict[tuple[str, str], float]:
    """Cặp job_uid LSH cho là giống nhau, kèm Jaccard ước lượng (đã lọc lại >= threshold)."""
    hashes = {u: minhash_of(sh) for u, sh in shingle_sets(df, strip).items()}
    lsh = MinHashLSH(threshold=threshold, num_perm=NUM_PERM)
    for uid, m in hashes.items():
        lsh.insert(uid, m)
    out: dict[tuple[str, str], float] = {}
    for uid, m in hashes.items():
        for other in lsh.query(m):
            if other == uid:
                continue
            key = tuple(sorted((uid, other)))
            if key not in out:
                j = hashes[key[0]].jaccard(hashes[key[1]])
                if j >= threshold:
                    out[key] = float(j)
    return out


def candidates(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Gộp cặp của hai tầng thành bảng ứng viên (mỗi cặp một dòng)."""
    base = baseline_pairs(df)
    mh = minhash_pairs(df, threshold)
    info = df.set_index("job_uid")[["source", "title", "company_name"]]
    rows = []
    for a, b in sorted(base | set(mh)):
        rows.append(
            {
                "job_uid_a": a,
                "job_uid_b": b,
                "by_baseline": (a, b) in base,
                "jaccard_est": mh.get((a, b)),
                "cross_source": info.at[a, "source"] != info.at[b, "source"],
                "title_a": info.at[a, "title"],
                "title_b": info.at[b, "title"],
                "company_a": info.at[a, "company_name"],
                "company_b": info.at[b, "company_name"],
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", nargs="+", type=Path, required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    df = pd.concat([pd.read_parquet(p) for p in args.snapshots], ignore_index=True)
    df = df.drop_duplicates("job_uid")
    cand = candidates(df, args.threshold)
    n_base = int(cand["by_baseline"].sum()) if len(cand) else 0
    n_mh = int(cand["jaccard_est"].notna().sum()) if len(cand) else 0
    n_cross = int(cand["cross_source"].sum()) if len(cand) else 0
    print(f"{len(df)} tin ({df['source'].value_counts().to_dict()})")
    print(f"{len(cand)} cặp ứng viên: baseline {n_base}, minhash(≥{args.threshold}) {n_mh}, khác trang {n_cross}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        cand.to_csv(args.out, index=False)
        print(f"→ {args.out}")


if __name__ == "__main__":
    main()
