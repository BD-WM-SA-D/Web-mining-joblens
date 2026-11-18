"""WM2 – Cohen's κ giữa hai người gán span kỹ năng (mức token BIO) và F1 span strict giữa hai người.

    uv run python -m annotation.kappa_skill --project 5

Project κ (người thứ hai) có trường `src_task` trỏ về task gốc của người thứ nhất trong project TEST, nên
ghép hai bản nhãn theo `src_task`. Đọc thẳng CSDL SQLite của Label Studio ở chế độ chỉ đọc (không cần token,
không ghi gì).

Số chính thức (2026-11-12, guideline 0.4, project 5): κ 0,650 trên 953 token, F1 0,781, 18/50 câu lệch,
tính bằng một script tạm cùng cách tính này. **Chạy lại bây giờ ra κ 0,675, F1 0,800, 16/50**, vì sau khi
đo κ đã sửa 4 nhãn sai của người thứ nhất (task 1726, 1814, 1906, 2051) và Label Studio không giữ bản cũ.
Số trước khi sửa (0,650) mới là đồng thuận thật; số sau khi sửa lạc quan vì đã sửa đúng chỗ lệch.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

from seqeval.metrics import f1_score
from seqeval.scheme import IOB2
from sklearn.metrics import cohen_kappa_score

from annotation.export_bio import to_bio

DEFAULT_DB = Path(os.environ.get("LOCALAPPDATA", "")) / "label-studio" / "label-studio" / "label_studio.sqlite3"


def latest(db: sqlite3.Connection, task_id: int) -> tuple[list[tuple[int, int]], list[str]] | None:
    """Bản gán mới nhất (không bị huỷ) của một task: danh sách (start, end) và chữ của từng span."""
    row = db.execute(
        "select result from task_completion where task_id=? and was_cancelled=0 order by updated_at desc limit 1",
        (task_id,),
    ).fetchone()
    if row is None:
        return None
    res = [x for x in json.loads(row[0]) if x.get("type") == "labels"]
    return [(x["value"]["start"], x["value"]["end"]) for x in res], [x["value"]["text"] for x in res]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, default=5, help="project của người thứ hai")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--show", action="store_true", help="in từng câu lệch")
    args = ap.parse_args()

    db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    a_tok: list[str] = []
    b_tok: list[str] = []
    a_sent: list[list[str]] = []
    b_sent: list[list[str]] = []
    diff = []
    miss = 0
    for tid, data in db.execute("select id, data from task where project_id=? order by id", (args.project,)):
        d = json.loads(data)
        a, b = latest(db, d["src_task"]), latest(db, tid)
        if a is None or b is None:
            miss += 1
            continue
        _, ta, _ = to_bio(d["text"], a[0])
        _, tb, _ = to_bio(d["text"], b[0])
        a_tok += ta
        b_tok += tb
        a_sent.append(ta)
        b_sent.append(tb)
        if ta != tb:
            diff.append((d["src_task"], d["text"], a[1], b[1]))
    print(f"{len(a_sent)} câu (thiếu nhãn {miss}), {len(a_tok)} token")
    print(f"κ token BIO = {cohen_kappa_score(a_tok, b_tok):.3f}")
    print(f"F1 span strict giữa hai người = {f1_score(a_sent, b_sent, mode='strict', scheme=IOB2):.3f}")
    print(f"câu lệch: {len(diff)}/{len(a_sent)}")
    if args.show:
        for src, text, a, b in diff:
            print(f"\n{src} | {text}\n  người 1: {a}\n  người 2: {b}")


if __name__ == "__main__":
    main()
