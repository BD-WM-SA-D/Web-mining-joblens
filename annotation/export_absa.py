"""Tải nhãn WM3 từ Label Studio, ghi ra jsonl mức câu và chấm baseline từ điển + nhãn yếu.

    uv run python -m annotation.export_absa --project 6 --batch absa_trial

Ghi ra data/annotation/ (không commit):
    <batch>.export.<ngày>.json   export gốc của Label Studio, giữ lại để tái lập
    <batch>.absa.jsonl           mỗi dòng {sentence_id, text, section, lang, company_name,
                                            gold: {aspect: polarity}, flag, comment}

"Để trống" trong Label Studio được giữ nguyên là **không có khía cạnh đó**, không đổi thành
`neutral` (guideline mục 2). Câu bị người gán bỏ qua (cancelled) hoặc tick "không gán được" vẫn ghi
vào jsonl nhưng không tính điểm.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
from datetime import date
from pathlib import Path

from absa.lexicon import ASPECTS, POLARITIES, predict
from absa.score import as_dict, fmt, report
from absa.weak_labels import VERSION as WEAK_VERSION
from absa.weak_labels import weak_label
from annotation.preannotate_dict import TOKEN_FILE, LabelStudio

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "annotation"
UNUSABLE = "không gán được"


def parse_task(task: dict) -> dict | None:
    """Đổi một task Label Studio thành {..., gold, flag, comment}. None nếu chưa gán."""
    anns = [a for a in task.get("annotations", []) if not a.get("was_cancelled")]
    if not anns:
        return None
    gold: dict[str, str] = {}
    flag = comment = None
    for item in anns[0].get("result", []):
        name, value = item.get("from_name"), item.get("value", {})
        if name in ASPECTS:
            choices = value.get("choices") or []
            if choices and choices[0] in POLARITIES:
                gold[name] = choices[0]
        elif name == "flag":
            flag = (value.get("choices") or [None])[0]
        elif name == "comment":
            comment = " ".join(value.get("text") or []).strip() or None
    d = task["data"]
    return {
        "sentence_id": d["sentence_id"],
        "text": d["text"],
        "section": d["section"],
        "lang": d["lang"],
        "company_name": d.get("company_name"),
        "gold": gold,
        "flag": flag,
        "comment": comment,
        "n_annotations": len(anns),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True, help="id project (xem URL localhost:8080/projects/<id>)")
    ap.add_argument("--batch", default="absa_trial")
    ap.add_argument("--sentences", type=Path, default=ROOT / "data" / "absa" / "sentences.jsonl")
    ap.add_argument("--url", default="http://localhost:8080")
    args = ap.parse_args()

    token = os.environ.get("LABEL_STUDIO_TOKEN") or (TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else "")
    if not token:
        raise SystemExit(f"Thiếu token: tạo Personal Access Token trong Label Studio rồi lưu vào {TOKEN_FILE}")
    ls = LabelStudio(args.url, token)
    print(f"project {args.project}: {ls.project_title(args.project)}")

    tasks = list(ls.tasks(args.project))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = OUT_DIR / f"{args.batch}.export.{date.today().isoformat()}.json"
    raw.write_text(json.dumps(tasks, ensure_ascii=False, indent=1), "utf-8")

    rows = [r for r in (parse_task(t) for t in tasks) if r]
    out = OUT_DIR / f"{args.batch}.absa.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    print(f"{len(tasks)} task, {len(rows)} đã gán -> {out.relative_to(ROOT)} (export gốc: {raw.name})")

    scored = [r for r in rows if r["flag"] != UNUSABLE and not (r["flag"] or "").startswith(UNUSABLE)]
    n_empty = sum(1 for r in scored if not r["gold"])
    n_hard = sum(1 for r in scored if r["flag"])
    per_aspect = collections.Counter(a for r in scored for a in r["gold"])
    per_pol = collections.Counter(p for r in scored for p in r["gold"].values())
    n_asp = collections.Counter(len(r["gold"]) for r in scored)
    print(f"\nchấm trên {len(scored)} câu (bỏ {len(rows) - len(scored)} câu 'không gán được')")
    print(f"  không khía cạnh nào: {n_empty}   tick 'khó / cần bàn': {n_hard}")
    print(f"  số khía cạnh mỗi câu: {dict(sorted(n_asp.items()))}")
    print(f"  theo khía cạnh: {dict(per_aspect.most_common())}")
    print(f"  theo cảm xúc  : {dict(per_pol.most_common())}")

    gold = [r["gold"] for r in scored]
    print("\n" + fmt("baseline từ điển", report(gold, [as_dict(predict(r["text"])) for r in scored])))

    if args.sentences.exists():
        # Khớp theo VĂN BẢN trước, theo id sau. Sửa bộ tách câu (ví dụ bản 2026-11-15 giữ `<br>` làm
        # ranh giới) làm id đổi; khớp theo văn bản thì nhãn đã gán vẫn dùng được, còn câu nào bị tách
        # nhỏ hơn thì không khớp nữa và được báo ra để loại khỏi tập dev.
        by_id, by_text = {}, {}
        for line in args.sentences.read_text(encoding="utf-8").splitlines():
            if line.strip():
                s = json.loads(line)
                by_id[s["sentence_id"]] = s
                by_text.setdefault(s["text"], s)
        found = {r["sentence_id"]: by_text.get(r["text"]) or by_id.get(r["sentence_id"]) for r in scored}
        gone = [r for r in scored if not found[r["sentence_id"]]]
        if gone:
            print(f"\n{len(gone)}/{len(scored)} câu không còn trong {args.sentences.name} (đã bị tách nhỏ hơn):")
            for r in gone:
                print(f"  {r['text'][:100]}")
        pairs = [(r["gold"], found[r["sentence_id"]]) for r in scored if found[r["sentence_id"]]]
        weak = [as_dict(weak_label(s)) for _, s in pairs]
        print("\n" + fmt(f"nhãn yếu ({WEAK_VERSION})", report([g for g, _ in pairs], weak)))

    if n_hard:
        print("\nCâu tick 'khó / cần bàn':")
        for r in scored:
            if r["flag"]:
                print(f"  [{r['section']}/{r['lang']}] {r['text']}")
                print(
                    f"      gán: {r['gold'] or 'để trống cả 6'}"
                    + (f"   ghi chú: {r['comment']}" if r["comment"] else "")
                )


if __name__ == "__main__":
    main()
