"""WM2 – gắn mã ESCO cho từ điển kỹ năng (`ie/resources/skill_alias.csv`), qua API tìm kiếm công khai của ESCO.

    uv run python -m ie.esco_map search      # tra ESCO, lưu cache, ghi file duyệt data/esco/review.csv
    uv run python -m ie.esco_map apply       # ghi mapping đã chấp nhận vào ie/resources/skill_esco.csv + cột esco_uri

- Chỉ gửi **tên kỹ năng** trong từ điển (ví dụ "Python", "Photoshop") tới API ESCO; không gửi văn bản tin hay
  dữ liệu crawl. 2 giây giữa hai request, User-Agent ghi rõ mục đích học tập. Kết quả lưu cache trong data/esco/
  (không commit); chạy lại chỉ tra phần còn thiếu.
- Gặp lỗi HTTP (403, 429…) thì **dừng ngay**, ghi file duyệt cho phần đã tra, không thử lại trong ngày
  (2026-11-20: 403 sau 159 request ở 1,1 giây/request).
- **Tự nhận** (`auto`) chỉ khi nhãn ESCO, sau khi bỏ phần chú thích trong ngoặc và chuẩn hóa chữ, trùng đúng tên chuẩn
  hoặc một alias của kỹ năng. Mọi trường hợp khác đưa ra file duyệt: người duyệt điền cột `accept` = số thứ tự ứng
  viên (1–3) hoặc để trống (không có trong ESCO).
- Kỹ năng không có trong ESCO giữ `joblens:<slug>` (đúng contract `silver.job_skills`).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIAS_CSV = ROOT / "ie" / "resources" / "skill_alias.csv"
ESCO_CSV = ROOT / "ie" / "resources" / "skill_esco.csv"
OUT_DIR = ROOT / "data" / "esco"
CACHE = OUT_DIR / "search_cache.json"
REVIEW = OUT_DIR / "review.csv"
API = "https://ec.europa.eu/esco/api/search"
UA = "joblens-student-project/0.1 (university course project; skill normalization)"
DELAY = 2.0
MAX_QUERIES = 2  # mỗi kỹ năng: tên chuẩn + một alias tiếng Anh khác chữ (ESCO tìm không phân biệt hoa thường)
N_CAND = 3


def norm(s: str) -> str:
    s = re.sub(r"\(.*?\)", " ", s)
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[\s\-_./]+", " ", s).strip()


def is_ascii(s: str) -> bool:
    return all(ord(c) < 128 for c in s)


def load_dict() -> dict[str, list[str]]:
    by = defaultdict(list)
    with ALIAS_CSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            by[r["canonical"].strip()].append(r["alias"].strip())
    return dict(by)


class NotCached(Exception):
    pass


def search(text: str, cache: dict, offline: bool = False) -> list[dict]:
    if text in cache:
        return cache[text]
    if offline:
        raise NotCached(text)
    q = urllib.parse.urlencode({"text": text, "type": "skill", "language": "en", "limit": 10})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise SystemExit(f"ESCO trả HTTP {resp.status} – dừng")
        data = json.load(resp)
    res = [
        {
            "uri": x["uri"],
            "label": x["title"],
            "type": ",".join(s.rsplit("/", 1)[-1] for s in x.get("hasSkillType", [])),
        }
        for x in data.get("_embedded", {}).get("results", [])
    ]
    cache[text] = res
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), "utf-8")
    time.sleep(DELAY)
    return res


def cmd_search(args) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text("utf-8")) if CACHE.exists() else {}
    skills = load_dict()
    rows, n_auto = [], 0
    for i, (canon, aliases) in enumerate(sorted(skills.items()), 1):
        names = {norm(canon), *(norm(a) for a in aliases)}
        queries = list({q.lower(): q for q in reversed([canon, *(a for a in aliases if is_ascii(a))])}.values())
        queries = sorted(queries, key=lambda q: q != canon)
        if args.offline:  # dùng mọi truy vấn của kỹ năng này đã có trong cache; không có cái nào thì dừng
            queries = [q for q in queries if q in cache] or queries[:1]
        else:
            queries = queries[:MAX_QUERIES]
        cands: dict[str, dict] = {}
        try:
            for q in queries:
                for c in search(q, cache, args.offline):
                    cands.setdefault(c["uri"], c)
        except urllib.error.HTTPError as e:
            print(f"DỪNG: ESCO trả HTTP {e.code} ở kỹ năng thứ {i} ({canon}); không thử lại trong ngày", flush=True)
            break
        except NotCached:
            print(f"--offline: dừng ở kỹ năng thứ {i} ({canon}), chưa có trong cache", flush=True)
            break
        cands_l = list(cands.values())
        auto = next((c for c in cands_l if norm(c["label"]) in names), None)
        n_auto += auto is not None
        top = ([auto] if auto else []) + [c for c in cands_l if c is not auto][: N_CAND - (auto is not None)]
        row = {"canonical": canon, "aliases": "; ".join(aliases[:4]), "method": "auto" if auto else ""}
        for k in range(N_CAND):
            c = top[k] if k < len(top) else {"uri": "", "label": "", "type": ""}
            row |= {f"cand{k + 1}_label": c["label"], f"cand{k + 1}_uri": c["uri"], f"cand{k + 1}_type": c["type"]}
        row["accept"] = "1" if auto else ""
        rows.append(row)
        if i % 25 == 0:
            print(f"  {i}/{len(skills)} kỹ năng, tự nhận {n_auto}", flush=True)
    with REVIEW.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)}/{len(skills)} kỹ năng đã tra: tự nhận {n_auto}, cần duyệt {len(rows) - n_auto} → {REVIEW}")


def cmd_apply(_args) -> None:
    with REVIEW.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    accepted = {}
    for r in rows:
        k = r["accept"].strip()
        if k:
            accepted[r["canonical"]] = {
                "canonical": r["canonical"],
                "esco_uri": r[f"cand{k}_uri"],
                "esco_label": r[f"cand{k}_label"],
                "esco_type": r[f"cand{k}_type"],
                "method": r["method"] or "reviewed",
            }
    with ESCO_CSV.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=["canonical", "esco_uri", "esco_label", "esco_type", "method"])
        w.writeheader()
        w.writerows(sorted(accepted.values(), key=lambda x: x["canonical"]))
    with ALIAS_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields, alias_rows = reader.fieldnames, list(reader)
    for r in alias_rows:
        r["esco_uri"] = accepted.get(r["canonical"].strip(), {}).get("esco_uri", "")
    with ALIAS_CSV.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(alias_rows)
    by = defaultdict(int)
    for a in accepted.values():
        by[a["method"]] += 1
    print(
        f"{len(accepted)}/{len(rows)} kỹ năng có mã ESCO ({dict(by)}) → {ESCO_CSV}, cột esco_uri của {ALIAS_CSV.name}"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--offline", action="store_true", help="chỉ dùng cache, không gọi API")
    sub.add_parser("apply")
    args = ap.parse_args()
    cmd_search(args) if args.cmd == "search" else cmd_apply(args)


if __name__ == "__main__":
    main()
