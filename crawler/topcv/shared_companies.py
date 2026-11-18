"""WM1 – chọn công ty có mặt ở CẢ TopCV và ITviec, để crawl nhắm đúng đích.

    uv run python -m crawler.topcv.shared_companies --out data/crawl/topcv/shared_companies.txt

Không gửi request nào: đọc hai snapshot và bảng "tin → trang công ty" dựng từ HTML đã lưu.

Tên công ty hai trang viết khác nhau (TopCV ghi tên pháp lý "Công ty TNHH LG CNS Việt Nam", ITviec ghi
tên thương hiệu "LG CNS Việt Nam") nên so bằng `crawler.dedup.norm_company`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from crawler.dedup import norm_company
from crawler.topcv.company import index_from_saved_html

ROOT = Path(__file__).resolve().parents[2]


def shared(topcv: pd.DataFrame, itviec: pd.DataFrame, job_to_company: dict[str, str]) -> pd.DataFrame:
    """Bảng công ty chung: tên chuẩn hóa, số tin mỗi nguồn, trang công ty trên TopCV."""
    t = topcv.assign(co=[norm_company(c) for c in topcv["company_name"]])
    i = itviec.assign(co=[norm_company(c) for c in itviec["company_name"]])
    n_itviec = i["co"].value_counts()
    rows = []
    for co, g in t[t["co"].isin(set(i["co"]))].groupby("co"):
        urls = sorted({u for u in (job_to_company.get(str(s)) for s in g["source_job_id"]) if u})
        rows.append(
            {
                "company": co,
                "n_topcv": len(g),
                "n_itviec": int(n_itviec.get(co, 0)),
                "company_url": urls[0] if urls else None,
                "n_urls": len(urls),
            }
        )
    return pd.DataFrame(rows).sort_values("n_itviec", ascending=False, ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topcv", type=Path, default=ROOT / "data" / "crawl" / "topcv" / "topcv_v2.parquet")
    ap.add_argument("--itviec", type=Path, default=ROOT / "data" / "crawl" / "itviec-jobs" / "itviec_v1.parquet")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "crawl" / "topcv" / "shared_companies.txt")
    args = ap.parse_args()

    df = shared(pd.read_parquet(args.topcv), pd.read_parquet(args.itviec), index_from_saved_html())
    print(df.to_string(index=False))
    urls = [u for u in df["company_url"] if u]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(urls) + "\n", encoding="utf-8")
    missing = df[df["company_url"].isna()]["company"].tolist()
    print(f"\n{len(urls)} trang công ty → {args.out}")
    if missing:
        print(f"chưa có trang công ty cho: {missing}")


if __name__ == "__main__":
    main()
