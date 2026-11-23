"""Đọc và ghi file JSON Lines (mỗi dòng một đối tượng JSON, bỏ qua dòng trống)."""

from __future__ import annotations

import json
from pathlib import Path


def read_jsonl(path: str | Path) -> list[dict]:
    """Đọc toàn bộ file JSONL, bỏ qua dòng trống."""
    text = Path(path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]
