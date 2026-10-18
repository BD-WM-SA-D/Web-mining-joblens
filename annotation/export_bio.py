"""Tải nhãn từ Label Studio và đổi sang BIO (token = âm tiết/từ) để train và chấm WM2 bằng seqeval.

    uv run python -m annotation.export_bio --project 1 --batch skill_batch1    # DEV (VietJobs)
    uv run python -m annotation.export_bio --project 3 --batch skill_test1     # TEST (TopCV)

Ghi ra data/annotation/ (không commit):
    <batch>.export.<ngày>.json   bản export gốc của Label Studio (giữ lại để tái lập)
    <batch>.bio.jsonl            mỗi dòng {id, job_uid, double, tokens, tags}
Span được cắt khoảng trắng/dấu câu ở mép (Label Studio hay kéo theo dấu cách). Câu bị bỏ qua (cancelled) không ghi.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from annotation.preannotate_dict import TOKEN_FILE, LabelStudio

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "annotation"
TOKEN_RE = re.compile(r"\w+[+#]*|[^\w\s]")
EDGE = " \t\n.,;:!?()[]{}\"'…–-"


def trim(text: str, start: int, end: int) -> tuple[int, int]:
    """Cắt khoảng trắng/dấu câu ở mép span; giữ "." đầu tên như ".NET" và "+"/"#" cuối như "C++", "C#"."""
    while start < end and text[start] in EDGE and not (text[start] == "." and text[start + 1 : start + 2].isalnum()):
        start += 1
    while end > start and text[end - 1] in EDGE:
        end -= 1
    while end < len(text) and text[end] in "+#" and end > start:
        end += 1
    return start, end


def to_bio(text: str, spans: list[tuple[int, int]]) -> tuple[list[str], list[str], int]:
    """Trả về tokens, tags và số span không khớp ranh giới token (span vẫn được gán cho các token nằm trong nó)."""
    toks = [(m.start(), m.end(), m.group()) for m in TOKEN_RE.finditer(text)]
    tags = ["O"] * len(toks)
    misaligned = 0
    for a, b in sorted(spans):
        idx = [i for i, (s, e, _) in enumerate(toks) if s < b and e > a]
        if not idx:
            misaligned += 1
            continue
        if toks[idx[0]][0] != a or toks[idx[-1]][1] != b:
            misaligned += 1
        if any(tags[i] != "O" for i in idx):
            misaligned += 1  # chồng lấn span khác
            continue
        tags[idx[0]] = "B-SKILL"
        for i in idx[1:]:
            tags[i] = "I-SKILL"
    return [t for _, _, t in toks], tags, misaligned


def convert(export: list[dict]) -> tuple[list[dict], Counter]:
    rows, stats = [], Counter()
    for task in export:
        anns = [a for a in task.get("annotations", []) if not a.get("was_cancelled")]
        if not anns:
            continue
        ann = max(anns, key=lambda a: a.get("updated_at") or "")
        text = task["data"]["text"]
        spans = set()
        for r in ann["result"]:
            if r.get("type") != "labels":
                continue
            a, b = trim(text, r["value"]["start"], r["value"]["end"])
            if a < b:
                spans.add((a, b))
            stats["trimmed"] += (a, b) != (r["value"]["start"], r["value"]["end"])
        flagged = any(r.get("from_name") == "flag" and r["value"].get("choices") for r in ann["result"])
        tokens, tags, bad = to_bio(text, list(spans))
        stats["sentences"] += 1
        stats["spans"] += len(spans)
        stats["empty"] += not spans
        stats["misaligned"] += bad
        stats["flagged"] += flagged
        rows.append(
            {
                "id": task["data"]["id"],
                "job_uid": task["data"]["job_uid"],
                "double": bool(task["data"].get("double")),
                "flagged": flagged,
                "tokens": tokens,
                "tags": tags,
            }
        )
    return rows, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--batch", required=True, help="tên đợt, ví dụ skill_batch1 / skill_test1")
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--from-file", help="dùng file export có sẵn thay vì gọi Label Studio")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.from_file:
        export = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
    else:
        ls = LabelStudio(args.url, TOKEN_FILE.read_text().strip())
        export = ls._call("GET", f"/api/projects/{args.project}/export?exportType=JSON")
        raw = OUT_DIR / f"{args.batch}.export.{date.today().isoformat()}.json"
        raw.write_text(json.dumps(export, ensure_ascii=False), encoding="utf-8")
        print(f"đã lưu {raw.relative_to(ROOT)}")
    rows, stats = convert(export)
    out = OUT_DIR / f"{args.batch}.bio.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: {dict(stats)}")


if __name__ == "__main__":
    main()
