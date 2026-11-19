"""Gợi ý sẵn span SKILL bằng từ điển alias (ie/resources/skill_alias.csv) cho project Label Studio – CHỈ dùng cho DEV.

Người gán vẫn phải xem từng câu, xóa span sai, bôi thêm span thiếu rồi Submit. Không dùng cho project TEST: người
gán dễ giữ nguyên gợi ý, làm tập test nghiêng về baseline từ điển (xem guideline_skill.md).

    # Ghi gợi ý vào các task chưa gán của project DEV trên Label Studio đang chạy
    # Token: Label Studio → Account & Settings → Personal Access Token → lưu vào data/.ls_token (đã gitignore)
    uv run python -m annotation.preannotate_dict --project 1 --limit 300
    uv run python -m annotation.preannotate_dict --project 1 --dry-run   # chỉ thống kê, không ghi
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIAS_CSV = ROOT / "ie" / "resources" / "skill_alias.csv"
TOKEN_FILE = ROOT / "data" / ".ls_token"
MODEL_VERSION = "dict-alias"
TEST_PROJECT_HINT = "TEST"

# Bỏ khi dò trong văn bản: quá chung, hoặc trùng từ thường ("Ai" = ai trong tiếng Việt)
SKIP_NOTE_PREFIX = "quá chung"
SKIP_ALIASES = {"Ai"}
BOUND_L = r"(?<![\w+#])"
BOUND_R = r"(?![\w+#])"


def load_aliases(path: Path = ALIAS_CSV) -> list[str]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    too_generic = {r["canonical"] for r in rows if (r.get("note") or "").startswith(SKIP_NOTE_PREFIX)}
    forms = set()
    for r in rows:
        if r["canonical"] not in too_generic:
            for s in (r["alias"], r["canonical"]):
                s = s.strip()
                if s and s not in SKIP_ALIASES:
                    forms.add(s)
    return sorted(forms, key=lambda s: (-len(s), s))


def build_matcher(forms: list[str]) -> re.Pattern:
    """Một regex duy nhất, alias dài khớp trước. Alias ≤ 3 ký tự (SQL, Go, C, R…) phân biệt hoa thường."""
    parts = []
    for s in forms:
        body = re.escape(s)
        parts.append(body if len(s) <= 3 else f"(?i:{body})")
    return re.compile(BOUND_L + "(?:" + "|".join(parts) + ")" + BOUND_R)


def find_spans(text: str, matcher: re.Pattern) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group()) for m in matcher.finditer(text)]


def to_result(spans: list[tuple[int, int, str]]) -> list[dict]:
    return [
        {
            "from_name": "label",
            "to_name": "text",
            "type": "labels",
            "value": {"start": a, "end": b, "text": t, "labels": ["SKILL"]},
        }
        for a, b, t in spans
    ]


class LabelStudio:
    def __init__(self, url: str, personal_token: str):
        self.url = url.rstrip("/")
        self.personal_token = personal_token
        self._refresh()

    def _refresh(self) -> None:
        """Access token chỉ sống ~5 phút – xin lại bằng Personal Access Token."""
        body = json.dumps({"refresh": self.personal_token}).encode()
        self.access = self._call("POST", "/api/token/refresh", body, auth=False)["access"]

    def _call(self, method: str, path: str, body: bytes | None = None, auth: bool = True, retry: bool = True):
        req = urllib.request.Request(self.url + path, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if auth:
            req.add_header("Authorization", f"Bearer {self.access}")
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            if e.code == 401 and auth and retry:
                self._refresh()
                return self._call(method, path, body, auth, retry=False)
            raise

    def project_title(self, pid: int) -> str:
        return self._call("GET", f"/api/projects/{pid}/")["title"]

    def tasks(self, pid: int):
        page = 1
        while True:
            try:
                data = self._call("GET", f"/api/tasks?project={pid}&page={page}&page_size=500&fields=all")
            except urllib.error.HTTPError as e:
                if e.code == 404:  # hết trang
                    return
                raise
            tasks = data["tasks"] if isinstance(data, dict) else data
            if not tasks:
                return
            yield from tasks
            page += 1

    def add_prediction(self, task_id: int, result: list[dict]) -> None:
        body = json.dumps({"task": task_id, "result": result, "model_version": MODEL_VERSION}).encode()
        self._call("POST", "/api/predictions/", body)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True, help="id project DEV (xem URL localhost:8080/projects/<id>)")
    ap.add_argument("--limit", type=int, default=300, help="số task chưa gán tối đa được gợi ý (theo thứ tự task)")
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("LABEL_STUDIO_TOKEN") or (TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else "")
    if not token:
        raise SystemExit(f"Thiếu token: tạo Personal Access Token trong Label Studio rồi lưu vào {TOKEN_FILE}")
    ls = LabelStudio(args.url, token)
    title = ls.project_title(args.project)
    if TEST_PROJECT_HINT in title.upper():
        raise SystemExit(f"Project '{title}' là tập TEST – không gợi ý sẵn cho tập test")

    matcher = build_matcher(load_aliases())
    done = with_skill = n_spans = 0
    for t in sorted(ls.tasks(args.project), key=lambda t: t["id"]):
        if done >= args.limit:
            break
        if t.get("total_annotations") or t.get("total_predictions"):
            continue
        spans = find_spans(t["data"]["text"], matcher)
        if not args.dry_run:
            ls.add_prediction(t["id"], to_result(spans))  # cả câu không khớp cũng ghi (kết quả rỗng)
        done += 1
        with_skill += bool(spans)
        n_spans += len(spans)
    print(
        f"{title}: {done} task được gợi ý, {with_skill} câu có span, {n_spans} span"
        + (" (dry-run)" if args.dry_run else "")
    )


if __name__ == "__main__":
    main()
