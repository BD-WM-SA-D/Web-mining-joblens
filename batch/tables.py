"""Đọc/ghi bảng cho các job mô hình của WM (ADR 0001 D3): cùng một giao diện, hai nơi chứa dữ liệu.

- **File cục bộ** (`--input-file`, `--output-file`, Parquet hoặc JSONL): chạy một mình, không cần cụm. Dùng để
  test và để WM tự kiểm tra trước khi giao image.
- **Bảng Iceberg** (`--input-table`, `--output-table`): khi Airflow của Big Data gọi image. Kết nối qua REST
  catalog bằng biến `JOBLENS_*` (D7), không hard-code địa chỉ hay khóa. Cần nhóm phụ thuộc `lakehouse`
  (`uv sync --group lakehouse`).

Ghi theo đúng `write_mode` trong contract (joblens/schemas/tables/silver/*.yaml):
`overwrite_partition` và `merge` đều làm bằng "xóa các dòng có khóa trong lô rồi ghi lại", nên chạy lại cùng một
lô không sinh bản trùng. `append` cũng xóa theo khóa trước (khóa chính có trong contract) vì lý do đó.

**Chưa chạy thử trên cụm** (2026-11-18): phần Iceberg viết theo API pyiceberg ≥ 0.9, đã kiểm bằng catalog SQL
cục bộ trong test; với Lakekeeper + SeaweedFS thật thì cần nhóm Big Data chạy thử lần đầu.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
from common.io import read_jsonl

ROOT = Path(__file__).resolve().parents[1]


def add_io_args(
    ap: argparse.ArgumentParser, default_output_table: str, changed_since_col: str | None = "updated_ts"
) -> None:
    """Tham số chung của mọi job, đúng hợp đồng chạy D3 cộng hai tham số file để chạy một mình.

    `changed_since_col` là cột mốc thời gian dùng cho `--changed-since`; để `None` ở job cần đọc toàn
    bộ kho tin (dedup) thì job đó không nhận tham số này.
    """
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--input-table", help="ví dụ silver.job_postings")
    src.add_argument("--input-file", type=Path, help="Parquet hoặc JSONL cục bộ")
    ap.add_argument("--input-snapshot", type=int, help="snapshot Iceberg của bảng đầu vào (tái lập được)")
    dst = ap.add_mutually_exclusive_group(required=True)
    dst.add_argument("--output-table", nargs="?", const=default_output_table, help=f"mặc định {default_output_table}")
    dst.add_argument("--output-file", type=Path, help="Parquet hoặc JSONL cục bộ")
    ap.add_argument("--run-id", required=True, help="ID lần chạy Airflow")
    ap.add_argument(
        "--stub",
        action="store_true",
        default=os.environ.get("JOBLENS_STUB") == "1",  # image bản stub đặt sẵn biến này
        help="bản stub: không cần model, chạy trong vài giây",
    )
    ap.add_argument("--limit", type=int, help="chỉ xử lý N dòng đầu (thử nhanh)")
    ap.add_argument(
        "--sources",
        help="chỉ xử lý các nguồn này, ngăn bằng dấu phẩy (ví dụ topcv,itviec). Không truyền thì xử lý "
        "mọi nguồn, gồm cả dữ liệu mô phỏng của nền tảng dữ liệu",
    )
    if changed_since_col:
        ap.add_argument(
            "--changed-since",
            help=f"chỉ xử lý dòng có {changed_since_col} từ mốc này trở đi, dạng ISO "
            "(2026-11-23 hoặc 2026-11-23T10:00:00). Airflow truyền đầu khoảng của lần chạy",
        )
    ap.set_defaults(changed_since_col=changed_since_col)


def version(stub: bool) -> str:
    """Version ghi vào từng dòng: biến JOBLENS_IMAGE_VERSION do Dockerfile đặt (x.y.z-gitsha), không thì theo git."""
    v = os.environ.get("JOBLENS_IMAGE_VERSION")
    if not v:
        try:
            sha = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            sha = "unknown"
        v = f"dev-{sha}"
    return f"{v}-stub" if stub else v


# ---------- file cục bộ ----------


def read_file(path: Path) -> list[dict]:
    if path.suffix == ".parquet":
        return pd.read_parquet(path).to_dict("records")
    return read_jsonl(path)


def write_file(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        pd.DataFrame(rows).to_parquet(path, index=False)
    else:
        path.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows), "utf-8")


# ---------- Iceberg ----------


def catalog():
    from pyiceberg.catalog import load_catalog

    env = os.environ
    props = {
        "type": "rest",
        "uri": env["JOBLENS_CATALOG_URI"],
        "warehouse": env.get("JOBLENS_CATALOG_WAREHOUSE", "joblens"),
        "s3.endpoint": env.get("JOBLENS_S3_ENDPOINT", ""),
        "s3.region": env.get("JOBLENS_S3_REGION", "us-east-1"),
        "s3.access-key-id": env.get("JOBLENS_S3_ACCESS_KEY_ID", ""),
        "s3.secret-access-key": env.get("JOBLENS_S3_SECRET_ACCESS_KEY", ""),
        "s3.path-style-access": "true",
    }
    return load_catalog("joblens", **{k: v for k, v in props.items() if v})


def read_table(
    name: str,
    snapshot: int | None,
    columns: tuple[str, ...] | None = None,
    cat=None,
    row_filter=None,
) -> list[dict]:
    from pyiceberg.expressions import AlwaysTrue

    t = (cat or catalog()).load_table(name)
    scan = t.scan(snapshot_id=snapshot, selected_fields=columns or ("*",), row_filter=row_filter or AlwaysTrue())
    return scan.to_arrow().to_pylist()


def table_filter(sources: tuple[str, ...], since, changed_col: str | None):
    """Điều kiện lọc đẩy xuống Iceberg: đọc ít dòng hơn chứ không lọc sau khi đã tải về."""
    from pyiceberg.expressions import AlwaysTrue, And, GreaterThanOrEqual, In

    parts = []
    if sources:
        parts.append(In("source", sources))
    if since is not None and changed_col:
        parts.append(GreaterThanOrEqual(changed_col, since))
    if not parts:
        return AlwaysTrue()
    out = parts[0]
    for p in parts[1:]:
        out = And(out, p)
    return out


def write_table(rows: list[dict], name: str, key: str, cat=None) -> None:
    """Xóa các dòng có `key` thuộc lô này rồi ghi lô mới, trong một giao dịch (overwrite có điều kiện)."""
    import pyarrow as pa
    from pyiceberg.expressions import In

    if not rows:
        return
    t = (cat or catalog()).load_table(name)
    schema = t.schema().as_arrow()
    data = pa.Table.from_pylist(rows, schema=schema)
    keys = sorted({r[key] for r in rows})
    t.overwrite(data, overwrite_filter=In(key, keys))


# ---------- dùng chung ----------


# Snapshot cục bộ của WM (crawler/snapshot.py) đặt tên cột theo message job_posting.v1, silver.job_postings đặt
# theo contract bảng. Hai bên chỉ khác tên ở vài cột; điền cả hai tên để code mô hình không phải phân biệt.
SAME_FIELD = (("requirements_text", "requirements"), ("date_posted", "posted_date"))


def harmonize(rows: list[dict]) -> list[dict]:
    for r in rows:
        for a, b in SAME_FIELD:
            if a in r and b not in r:
                r[b] = r[a]
            elif b in r and a not in r:
                r[a] = r[b]
    return rows


def parse_ts(value: str | None):
    """Mốc thời gian của --changed-since; ngày không giờ thì tính từ 00:00."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as e:
        raise SystemExit(f"--changed-since không đọc được: {value!r} (cần dạng ISO, ví dụ 2026-11-23)") from e


def _as_dt(value):
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return value if isinstance(value, datetime) else None


def filter_rows(rows: list[dict], sources: tuple[str, ...], since, changed_col: str | None) -> list[dict]:
    """Cùng điều kiện với `table_filter`, dùng cho đầu vào là file cục bộ."""
    if sources:
        rows = [r for r in rows if r.get("source") in sources]
    if since is not None and changed_col:
        if rows and changed_col not in rows[0]:
            raise SystemExit(f"--changed-since cần cột {changed_col}, file đầu vào không có cột này")
        kept = []
        for r in rows:
            ts = _as_dt(r.get(changed_col))
            if ts is None:
                continue  # không biết đổi lúc nào thì coi như ngoài lô tăng dần
            if ts.tzinfo and not since.tzinfo:
                ts = ts.replace(tzinfo=None)
            elif since.tzinfo and not ts.tzinfo:
                ts = ts.replace(tzinfo=since.tzinfo)
            if ts >= since:
                kept.append(r)
        rows = kept
    return rows


def load_input(args: argparse.Namespace, columns: tuple[str, ...] | None = None) -> list[dict]:
    sources = tuple(s.strip() for s in (args.sources or "").split(",") if s.strip())
    since = parse_ts(getattr(args, "changed_since", None))
    changed_col = getattr(args, "changed_since_col", None)
    if args.input_file:
        rows = filter_rows(read_file(args.input_file), sources, since, changed_col)
    else:
        if not sources:
            print(
                "chú ý: không có --sources nên xử lý mọi nguồn trong bảng, gồm cả dữ liệu mô phỏng; "
                "bản mô phỏng trùng tiêu đề và công ty với tin thật nên dedup sẽ gộp chúng",
                flush=True,
            )
        rows = read_table(
            args.input_table,
            args.input_snapshot,
            columns,
            row_filter=table_filter(sources, since, changed_col),
        )
    print(f"đọc {len(rows)} dòng" + (f" (nguồn {','.join(sources)})" if sources else ""), flush=True)
    return harmonize(rows[: args.limit] if args.limit else rows)


def nothing_to_do(rows: list[dict]) -> bool:
    """Lô rỗng là chuyện bình thường khi chạy tăng dần (lọc nguồn hoặc --changed-since không khớp dòng
    nào). Job in một dòng rồi kết thúc bình thường, không để Airflow báo hỏng."""
    if rows:
        return False
    print("không có dòng nào khớp bộ lọc đầu vào, không ghi gì", flush=True)
    return True


def save_output(rows: list[dict], args: argparse.Namespace, key: str) -> None:
    if args.output_file:
        write_file(rows, args.output_file)
        where = args.output_file
    else:
        write_table(rows, args.output_table, key)
        where = args.output_table
    print(f"ghi {len(rows)} dòng → {where}", flush=True)
