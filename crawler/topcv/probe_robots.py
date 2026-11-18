"""Kiểm tra robots.txt TopCV trước khi crawl trang công ty. Gửi ĐÚNG 1 request.

    uv run python -m crawler.topcv.probe_robots
    uv run python -m crawler.topcv.probe_robots --companies data/crawl/topcv/shared_companies.txt

Vì sao có file này: đường dẫn `/cong-ty/<slug>/<id>.html` là đường dẫn mới, chưa từng crawl. Phải tự
kiểm tra robots.txt cho phép hay không *trước*, thay vì để spider phát hiện giữa lần chạy – spider vẫn
bật `ROBOTSTXT_OBEY` nhưng nếu bị chặn thì lần chạy đã tốn request vô ích.

In ra: trạng thái HTTP, các dòng `Disallow` liên quan tới `/cong-ty`, và kết luận cho từng URL sẽ crawl.
Không lưu robots.txt vào repo.
"""

from __future__ import annotations

import argparse
import sys
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests

from crawler.topcv.spider import DEFAULT_UA

ROBOTS_URL = "https://www.topcv.vn/robots.txt"
CHECK_PATHS = ("/cong-ty", "/cong-ty/fpt-software/3.html", "/viec-lam/x/1.html", "/sitemap/jobs.xml")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", type=Path, help="kiểm tra thêm từng URL trong file này")
    args = ap.parse_args()

    r = requests.get(ROBOTS_URL, headers={"User-Agent": DEFAULT_UA}, timeout=30)
    print(f"GET {ROBOTS_URL} -> HTTP {r.status_code}")
    if r.status_code != 200:
        print("Không đọc được robots.txt -> KHÔNG crawl. (429/403 thì dừng hẳn trong ngày.)")
        sys.exit(1)

    print("\nCác dòng liên quan /cong-ty:")
    for line in r.text.splitlines():
        if "cong-ty" in line.lower() or line.lower().startswith(("user-agent", "crawl-delay")):
            print("  ", line.strip())

    rp = urllib.robotparser.RobotFileParser()
    rp.parse(r.text.splitlines())
    delay = rp.crawl_delay(DEFAULT_UA)
    print(f"\nCrawl-delay robots.txt yêu cầu: {delay if delay is not None else 'không ghi'} giây")
    print("(spider dùng DOWNLOAD_DELAY 3.0; nếu robots yêu cầu lớn hơn thì phải nâng lên)")

    print("\nKết luận theo đường dẫn:")
    urls = [f"https://www.topcv.vn{p}" for p in CHECK_PATHS]
    if args.companies:
        urls += [ln.strip() for ln in args.companies.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ok = True
    for u in urls:
        allowed = rp.can_fetch(DEFAULT_UA, u)
        ok &= allowed
        print(f"  {'CHO PHEP ' if allowed else 'BI CHAN  '} {urlparse(u).path}")
    print("\n" + ("Được phép crawl trang công ty." if ok else "CÓ ĐƯỜNG DẪN BỊ CHẶN -> không crawl đường dẫn đó."))


if __name__ == "__main__":
    main()
