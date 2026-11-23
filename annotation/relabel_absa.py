"""Sửa nhãn WM3 đã gán trên Label Studio theo một file đặc tả (dùng khi guideline đổi).

    uv run python -m annotation.relabel_absa --spec data/annotation/relabel_0.2.2.json          # chỉ in kế hoạch
    uv run python -m annotation.relabel_absa --spec data/annotation/relabel_0.2.2.json --apply  # ghi thật

Vì sao cần: guideline sửa thì một số câu đã gán không còn đúng luật mới. Sửa tay trong giao diện vừa
lâu vừa dễ bỏ sót, nên để file đặc tả làm bằng chứng việc gì đã đổi (`experiments/results.md` dẫn lại).

File đặc tả là một danh sách, mỗi phần tử là một câu:

    [
      {"project": 6, "text": "Great environment, but unfair performance review",
       "set": {"culture_fun": "positive"}, "why": "guideline"},
      {"project": 7, "text": "Đây là một môi trường cân bằng giữa chuyên nghiệp",
       "flag": "không gán được (câu vô nghĩa, lẫn ngôn ngữ)", "clear": true, "why": "câu bị cắt dở"}
    ]

- `set`: đặt cực tính cho các khía cạnh này, giữ nguyên khía cạnh khác. `null` để xóa một khía cạnh.
- `flag`: đặt lại ô cờ (phải đúng một `Choice` trong `annotation/label_studio_absa.xml`).
- `clear`: xóa hết nhãn khía cạnh của câu đó (dùng với `flag` "không gán được").

Khớp câu theo **văn bản đầy đủ**, không theo id, vì id task Label Studio khác id câu trong corpus.
Không khớp hoặc khớp nhiều hơn một task thì dừng, không ghi gì.

Trước khi ghi, bản gốc của từng annotation được lưu vào `<spec>.backup.<ngày>.json`.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from absa.lexicon import ASPECTS, POLARITIES
from annotation.preannotate_dict import TOKEN_FILE, LabelStudio

ROOT = Path(__file__).resolve().parents[1]
FLAG_NAME = "flag"


def choice_item(from_name: str, value: str) -> dict:
    return {"from_name": from_name, "to_name": "text", "type": "choices", "value": {"choices": [value]}}


def new_result(old: list[dict], spec: dict) -> list[dict]:
    """Kết quả annotation mới. Giữ nguyên mọi mục không bị đặc tả nhắc tới (ví dụ `comment`)."""
    drop = set(spec.get("set", {}))
    if spec.get("clear"):
        drop |= set(ASPECTS)
    if "flag" in spec:
        drop.add(FLAG_NAME)
    out = [it for it in old if it.get("from_name") not in drop]
    for name, pol in spec.get("set", {}).items():
        if name not in ASPECTS:
            raise SystemExit(f"'{name}' không phải khía cạnh: {ASPECTS}")
        if pol is None:
            continue  # chỉ xóa
        if pol not in POLARITIES:
            raise SystemExit(f"'{pol}' không phải cực tính: {POLARITIES}")
        out.append(choice_item(name, pol))
    if spec.get("flag"):
        out.append(choice_item(FLAG_NAME, spec["flag"]))
    return out


def summary(result: list[dict]) -> str:
    g = {
        it["from_name"]: (it.get("value", {}).get("choices") or [None])[0]
        for it in result
        if it.get("from_name") in ASPECTS
    }
    flag = next((it for it in result if it.get("from_name") == FLAG_NAME), None)
    s = ", ".join(f"{k}={v}" for k, v in sorted(g.items())) or "để trống cả 6"
    if flag:
        s += f"  [cờ: {(flag.get('value', {}).get('choices') or [''])[0]}]"
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--apply", action="store_true", help="ghi thật; không có cờ này thì chỉ in kế hoạch")
    args = ap.parse_args()

    specs = json.loads(args.spec.read_text(encoding="utf-8"))
    token = os.environ.get("LABEL_STUDIO_TOKEN") or (TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else "")
    if not token:
        raise SystemExit(f"Thiếu token: tạo Personal Access Token trong Label Studio rồi lưu vào {TOKEN_FILE}")
    ls = LabelStudio(args.url, token)

    # Tải task một lần cho mỗi project rồi lập chỉ mục theo văn bản.
    by_project: dict[int, dict[str, list[dict]]] = {}
    for pid in sorted({s["project"] for s in specs}):
        idx: dict[str, list[dict]] = {}
        for t in ls.tasks(pid):
            idx.setdefault(t["data"]["text"], []).append(t)
        by_project[pid] = idx
        print(f"project {pid}: {ls.project_title(pid)} – {sum(len(v) for v in idx.values())} task")

    plan, backup = [], []
    for spec in specs:
        hits = by_project[spec["project"]].get(spec["text"], [])
        if len(hits) != 1:
            raise SystemExit(f"khớp {len(hits)} task (phải đúng 1) cho câu: {spec['text'][:90]}")
        task = hits[0]
        anns = [a for a in task.get("annotations", []) if not a.get("was_cancelled")]
        if not anns:
            raise SystemExit(f"task {task['id']} chưa gán, không có gì để sửa: {spec['text'][:90]}")
        ann = anns[0]
        plan.append((spec, ann, new_result(ann.get("result", []), spec)))
        backup.append({"annotation_id": ann["id"], "task_id": task["id"], "result": ann.get("result", [])})

    for spec, ann, res in plan:
        print(f"\nproject {spec['project']} · annotation {ann['id']} · {spec['text'][:90]}")
        print(f"  trước: {summary(ann.get('result', []))}")
        print(f"  sau  : {summary(res)}" + (f"   ({spec['why']})" if spec.get("why") else ""))

    if not args.apply:
        print(f"\n{len(plan)} câu sẽ sửa. Thêm --apply để ghi thật.")
        return

    bak = args.spec.with_suffix(f".backup.{date.today().isoformat()}.json")
    bak.write_text(json.dumps(backup, ensure_ascii=False, indent=1), "utf-8")
    for _, ann, res in plan:
        ls._call("PATCH", f"/api/annotations/{ann['id']}/", json.dumps({"result": res}).encode())
    print(f"\nđã sửa {len(plan)} câu. Bản gốc lưu ở {bak.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
