"""Tạo tập tin IT cố định (snapshot) từ VietJobs để train và đánh giá WM2.

Cách chạy:
    uv run python -m ie.vietjobs                      # đọc data/vietjobs/VietJobs.csv
    uv run python -m ie.vietjobs --csv đường/dẫn.csv

Kết quả (trong data/, đã gitignore – KHÔNG commit):
    data/vietjobs/it_v1.parquet         tin thuộc nhóm công nghệ thông tin, có source_job_id và job_uid
    data/vietjobs/it_v1.manifest.json   nguồn, sha256 file CSV, số dòng – ghi vào báo cáo để tái lập

source_job_id = số thứ tự dòng trong file CSV gốc (VietJobs không có ID tin). Chỉ ổn định khi dùng
đúng file CSV có sha256 ghi trong manifest. Trích dẫn: Pham Dinh et al., LREC 2026.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from joblens_contracts import job_uid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "vietjobs" / "VietJobs.csv"
OUT_DIR = ROOT / "data" / "vietjobs"
SNAPSHOT = "it_v1"
IT_CATEGORY = "công_nghệ_thông_tin_kỹ_thuật_số"
HF_DATASET = "dinhieufam/VietJobs"
LIST_COLS = ["qualifications", "technical_skills", "soft_skills", "languages_required", "benefits"]


def to_list(v) -> list[str]:
    """Cột danh sách trong CSV lưu dạng chuỗi "['a', 'b']" → list thật."""
    if isinstance(v, list):
        return v
    if not isinstance(v, str) or not v.strip():
        return []
    try:
        out = ast.literal_eval(v)
    except (ValueError, SyntaxError):
        return [s.strip() for s in v.split(",") if s.strip()]
    return [str(x).strip() for x in out if str(x).strip()] if isinstance(out, (list, tuple)) else [str(out)]


def load(csv: Path) -> pd.DataFrame:
    df = pd.read_csv(csv)
    df.insert(0, "source_job_id", df.index.astype(str))
    df.insert(0, "job_uid", df["source_job_id"].map(lambda i: job_uid("vietjobs", i)))
    for c in LIST_COLS:
        if c in df.columns:
            df[c] = df[c].map(to_list)
    return df


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hf_revision(csv: Path) -> str | None:
    """Commit Hugging Face của file đã tải (huggingface_hub ghi trong .cache cạnh file)."""
    meta = csv.parent / ".cache" / "huggingface" / "download" / f"{csv.name}.metadata"
    return meta.read_text().splitlines()[0] if meta.exists() else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = ap.parse_args()

    df = load(args.csv)
    it = df[df["category"] == IT_CATEGORY].reset_index(drop=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    it.to_parquet(OUT_DIR / f"{SNAPSHOT}.parquet", index=False)

    manifest = {
        "snapshot": SNAPSHOT,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": HF_DATASET,
        "hf_revision": hf_revision(args.csv),
        "csv_sha256": sha256(args.csv),
        "rows_total": len(df),
        "rows_it": len(it),
        "filter": f"category == {IT_CATEGORY}",
    }
    (OUT_DIR / f"{SNAPSHOT}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
