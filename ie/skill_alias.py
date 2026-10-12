"""Dựng bản nháp từ điển alias kỹ năng (baseline WM2) từ cột technical_skills của tập IT.

Cách chạy (cần data/vietjobs/it_v1.parquet – xem ie/vietjobs.py):
    uv run python -m ie.skill_alias --top 200

Ghi ra ie/resources/skill_alias.csv (commit được – chỉ là tên kỹ năng, không phải dữ liệu tin):
    canonical, alias, count, esco_uri, note
Bản này tự sinh, cần người xem lại: gộp/tách nhóm sai, điền esco_uri, đánh dấu note = "drop" cho mục không phải
kỹ năng cứng. Sau khi sửa tay thì KHÔNG chạy lại với --out trùng file (sẽ ghi đè).
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "vietjobs" / "it_v1.parquet"
OUT = Path(__file__).resolve().parent / "resources" / "skill_alias.csv"

# Gộp tay những cách viết mà quy tắc chuẩn hóa không bắt được (khóa sau chuẩn hóa → khóa đích)
MANUAL_MERGE = {
    "aftereffect": "aftereffects",
    "restfulapis": "restfulapi",
    "restapi": "restfulapi",
    "restapis": "restfulapi",
    "mssql": "sqlserver",
    "microsoftsqlserver": "sqlserver",
    "go": "golang",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "premierepro": "premiere",
    "reactnative": "reactnative",  # giữ riêng, không gộp vào react
    "amazonwebservices": "aws",
    "googlecloud": "gcp",
    "googlecloudplatform": "gcp",
    "microsoftexcel": "excel",
    "msexcel": "excel",
    "microsoftazure": "azure",
    "powerbi": "powerbi",
    "dotnet": "net",
    "aspnet": "aspnet",
    "netcore": "netcore",
    "aspnetcore": "netcore",
    "microsoftsql": "sqlserver",
    "3dmax": "3dsmax",
    "microservice": "microservices",
    "microservicesarchitecture": "microservices",
    "googlesheet": "googlesheets",
    "networking": "network",
    "cicdpipelines": "ci/cd",
    "agilemethodologies": "agile",
}
# Bỏ phần đầu là tên hãng khi phần còn lại vẫn rõ nghĩa: "Adobe Photoshop" → photoshop
VENDOR_PREFIXES = ("adobe", "microsoft", "ms", "apache", "autodesk")
KEEP_WITH_VENDOR = {
    "microsoftsqlserver",
    "microsoftsql",
    "mssql",
    "msexcel",
    "microsoftexcel",
    "microsoftazure",
    "adobexd",
}
# Không phải kỹ năng cứng → không đưa vào từ điển (kỹ năng mềm đã có cột soft_skills riêng)
SOFT_PREFIXES = ("kỹ năng", "khả năng", "tư duy", "tinh thần")
# Gợi ý cho người xem lại (khóa sau chuẩn hóa → ghi chú)
REVIEW_NOTES = {
    "ai": "mơ hồ: Adobe Illustrator hay trí tuệ nhân tạo – xem ngữ cảnh",
    "c": "dễ khớp nhầm khi dò trong văn bản – chỉ khớp khi đứng riêng",
    "r": "dễ khớp nhầm khi dò trong văn bản – chỉ khớp khi đứng riêng",
    "lậptrình": "quá chung – có thể drop",
    "phầnmềm": "quá chung – có thể drop",
    "hệđiềuhành": "quá chung – có thể drop",
    "cloud": "quá chung – có thể drop",
    "storage": "quá chung – có thể drop",
    "network": "quá chung – có thể drop",
}


def norm_key(s: str) -> str:
    """Khóa so khớp: chữ thường, bỏ khoảng trắng/dấu chấm/gạch, bỏ hậu tố 'js', bỏ tên hãng ở đầu."""
    s = unicodedata.normalize("NFC", s).lower().strip()
    if s.startswith(SOFT_PREFIXES):
        return ""
    words = s.split()
    compact = re.sub(r"[\s.\-_]", "", s)
    if len(words) > 1 and words[0] in VENDOR_PREFIXES and compact not in KEEP_WITH_VENDOR:
        s = " ".join(words[1:])
    k = re.sub(r"[\s.\-_]", "", s)
    if k.endswith("js") and len(k) >= 5:  # reactjs, react.js → react; nodejs → node
        k = k[:-2]
    return MANUAL_MERGE.get(k, k)


def build(skill_lists, top: int) -> list[dict]:
    variants: dict[str, Counter] = defaultdict(Counter)
    for skills in skill_lists:
        for s in skills:
            s = " ".join(str(s).split())
            k = norm_key(s)
            if k:
                variants[k][s] += 1
    groups = sorted(variants.items(), key=lambda kv: -sum(kv[1].values()))[:top]
    rows = []
    for key, cnt in groups:
        canonical = cnt.most_common(1)[0][0]
        for i, (alias, n) in enumerate(cnt.most_common()):
            note = REVIEW_NOTES.get(key, "") if i == 0 else ""
            rows.append({"canonical": canonical, "alias": alias, "count": n, "esco_uri": "", "note": note})
    return rows


def coverage(df: pd.DataFrame, rows: list[dict]) -> tuple[float, float]:
    """(tỉ lệ tag được từ điển phủ, tỉ lệ tag xuất hiện nguyên văn trong mô tả/yêu cầu)."""
    keys = {norm_key(r["alias"]) for r in rows}
    total = in_dict = in_text = 0
    for skills, desc, req in zip(df["technical_skills"], df["description"], df["requirements_text"], strict=True):
        text = f"{desc or ''}\n{req or ''}".lower()
        for s in skills:
            total += 1
            in_dict += norm_key(s) in keys
            in_text += str(s).lower() in text
    return in_dict / max(total, 1), in_text / max(total, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    ap.add_argument("--top", type=int, default=200, help="số kỹ năng chuẩn giữ lại")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    df = pd.read_parquet(args.snapshot)
    rows = build(df["technical_skills"], args.top)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["canonical", "alias", "count", "esco_uri", "note"])
        w.writeheader()
        w.writerows(rows)

    cov_dict, cov_text = coverage(df, rows)
    n_canon = len({r["canonical"] for r in rows})
    print(f"{n_canon} kỹ năng chuẩn, {len(rows)} alias → {args.out}")
    print(f"Tag kỹ năng được từ điển phủ: {cov_dict:.1%}")
    print(f"Tag xuất hiện nguyên văn trong mô tả/yêu cầu: {cov_text:.1%} (giới hạn trên của nhãn yếu dạng span)")


if __name__ == "__main__":
    main()
