"""Đọc sitemap ITviec → danh sách slug công ty (để biết crawl review của những công ty nào).

    uv run python -m crawler.itviec.sitemap --fetch --out data/crawl/itviec/companies.txt
    uv run python -m crawler.itviec.sitemap --fetch --hiring --out data/crawl/itviec/companies_hiring.txt

Sitemap chính thức (robots.txt → https://itviec.com/dunggiatminh.xml) có hai file dùng ở đây:
- `twinnings_companies_review_vn.xml`: 12.422 trang review `/nha-tuyen-dung/<slug>/danh-gia`.
  Nhưng ITviec tạo trang review cho MỌI nhà tuyển dụng: 8/8 công ty rút ngẫu nhiên không có review nào.
- `twinnings_jobs_desc_vn.xml`: 615 tin việc làm IT đang mở. URL dạng
  `/viec-lam-it/<chuc-danh>-<slug-cong-ty>-<id>` → tách ra **304 công ty đang tuyển IT**,
  nhóm này gần như chắc chắn là công ty IT thật và có review (6/6 công ty lớn thử đều có).
  Đây là cách lọc công ty mà KHÔNG tốn request nào.

Tải sitemap là 1–2 request, không phải crawl nội dung.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITEMAP_URL = "https://itviec.com/twinnings_companies_review_vn.xml"
JOBS_SITEMAP_URL = "https://itviec.com/twinnings_jobs_desc_vn.xml"
DEFAULT_XML = ROOT / "data" / "crawl" / "itviec" / "sitemap_review_vn.xml"
DEFAULT_JOBS_XML = ROOT / "data" / "crawl" / "itviec" / "sitemap_jobs_vn.xml"
LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
SLUG_RE = re.compile(r"/nha-tuyen-dung/([^/?#]+)/danh-gia")
JOB_ID_RE = re.compile(r"-\d+$")


def slugs_from_xml(xml: str) -> list[str]:
    out = []
    for loc in LOC_RE.findall(xml):
        m = SLUG_RE.search(loc)
        if m:
            out.append(m.group(1))
    return list(dict.fromkeys(out))


def hiring_companies(jobs_xml: str, all_slugs: list[str]) -> dict[str, int]:
    """Slug công ty đang tuyển IT → số tin, tách từ URL việc làm bằng cách khớp hậu tố.

    URL `/viec-lam-it/<chuc-danh>-<slug-cong-ty>-<id>`: bỏ `-<id>`, rồi tìm slug công ty dài nhất
    khớp phần cuối. Khớp slug dài trước để "fpt-is" không ăn vào "fpt-is-hanoi".
    """
    by_len = sorted(all_slugs, key=len, reverse=True)
    out: dict[str, int] = {}
    for loc in LOC_RE.findall(jobs_xml):
        tail = JOB_ID_RE.sub("", loc.rsplit("/", 1)[-1])
        hit = next((c for c in by_len if tail.endswith("-" + c) or tail == c), None)
        if hit:
            out[hit] = out.get(hit, 0) + 1
    return out


def fetch_sitemap(path: Path = DEFAULT_XML, url: str = SITEMAP_URL) -> str:
    """Tải sitemap (1 request) và lưu lại; lần sau đọc file đã lưu."""
    import os

    import requests

    ua = os.environ.get(
        "JOBLENS_CRAWL_USER_AGENT",
        "JobLensStudentProject/0.1 (HUST course project, non-commercial; contact in repo README)",
    )
    r = requests.get(url, headers={"User-Agent": ua}, timeout=60)
    if r.status_code in (403, 429):
        raise SystemExit(f"Bị chặn HTTP {r.status_code} – dừng, không thử lại hôm nay")
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text, encoding="utf-8")
    return r.text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="tải lại sitemap (1–2 request)")
    ap.add_argument("--xml", type=Path, default=DEFAULT_XML)
    ap.add_argument(
        "--hiring",
        action="store_true",
        help="chỉ lấy công ty ĐANG TUYỂN IT (lọc qua sitemap việc làm) – nên dùng, xem docstring",
    )
    ap.add_argument("--jobs-xml", type=Path, default=DEFAULT_JOBS_XML)
    ap.add_argument("--limit", type=int, help="chỉ lấy N slug đầu")
    ap.add_argument("--seed", type=int, help="nếu có, rút ngẫu nhiên --limit slug với seed này")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    xml = fetch_sitemap(args.xml) if args.fetch else args.xml.read_text(encoding="utf-8")
    slugs = slugs_from_xml(xml)
    print(f"{len(slugs)} công ty có trang review trong sitemap")
    if args.hiring:
        jobs_xml = (
            fetch_sitemap(args.jobs_xml, JOBS_SITEMAP_URL) if args.fetch else args.jobs_xml.read_text(encoding="utf-8")
        )
        hiring = hiring_companies(jobs_xml, slugs)
        slugs = [s for s, _ in sorted(hiring.items(), key=lambda kv: -kv[1])]
        print(f"{len(LOC_RE.findall(jobs_xml))} tin việc làm → {len(slugs)} công ty đang tuyển IT")
    if args.limit:
        if args.seed is not None:
            import random

            slugs = random.Random(args.seed).sample(slugs, min(args.limit, len(slugs)))
        else:
            slugs = slugs[: args.limit]
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(slugs) + "\n", encoding="utf-8")
        print(f"{len(slugs)} slug → {args.out}")


if __name__ == "__main__":
    main()
