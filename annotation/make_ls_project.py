"""Tạo một project Label Studio và nhập task vào, qua API.

    uv run python -m annotation.make_ls_project \
        --title "WM3 ABSA - κ (người 2)" \
        --config annotation/label_studio_absa.xml \
        --tasks data/annotation/absa_kappa1.labelstudio.json

Dùng để dựng project cho người gán thứ hai (đo Cohen's κ): người đó phải gán trên project **riêng**,
không thấy nhãn người thứ nhất. Làm bằng API thay vì bấm trong UI để lần sau tái lập được.

Token: Label Studio → Account & Settings → Personal Access Token → lưu vào data/.ls_token (gitignore).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from annotation.preannotate_dict import TOKEN_FILE, LabelStudio

ROOT = Path(__file__).resolve().parents[1]
IMPORT_CHUNK = 200


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--config", type=Path, required=True, help="file XML cấu hình nhãn")
    ap.add_argument("--tasks", type=Path, required=True, help="file .labelstudio.json do script rút mẫu sinh ra")
    ap.add_argument("--description", default="")
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))
    config = args.config.read_text(encoding="utf-8")
    if args.dry_run:
        print(f"(dry-run) sẽ tạo '{args.title}' với {len(tasks)} task, cấu hình {args.config.name}")
        return

    token = os.environ.get("LABEL_STUDIO_TOKEN") or (TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else "")
    if not token:
        raise SystemExit(f"Thiếu token: tạo Personal Access Token trong Label Studio rồi lưu vào {TOKEN_FILE}")
    ls = LabelStudio(args.url, token)

    titles = {p["title"] for p in ls._call("GET", "/api/projects?page_size=200").get("results", [])}
    if args.title in titles:
        raise SystemExit(f"Đã có project tên '{args.title}' – đổi tên hoặc xóa project cũ trước")

    body = json.dumps(
        {"title": args.title, "description": args.description, "label_config": config},
        ensure_ascii=False,
    ).encode()
    pid = ls._call("POST", "/api/projects/", body)["id"]

    n = 0
    for i in range(0, len(tasks), IMPORT_CHUNK):
        chunk = tasks[i : i + IMPORT_CHUNK]
        res = ls._call(
            "POST",
            f"/api/projects/{pid}/import",
            json.dumps(chunk, ensure_ascii=False).encode(),
        )
        n += res.get("task_count", len(chunk))
    print(f"project {pid} '{args.title}': {n} task – {args.url}/projects/{pid}")


if __name__ == "__main__":
    main()
