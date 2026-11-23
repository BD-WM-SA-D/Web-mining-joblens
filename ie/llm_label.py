"""Nhãn yếu WM2 bằng LLM (OpenAI) theo guideline – chỉ cho câu VietJobs.

    uv run python -m ie.llm_label --model gpt-6-luna --bio data/annotation/skill_batch1.bio.jsonl --name dev_luna --eval
    uv run python -m ie.llm_label --model gpt-6-luna --bio data/weak/wm2_weak_selftrain.bio.jsonl --name train_luna --budget 2

Theo mục đăng ký trước "Nhãn yếu bằng LLM theo guideline" trong `experiments/results.md`.

- Key đọc từ `.env` (OPENAI_API_KEY), không in ra. Kết quả ghi vào data/llm/ (gitignore), không commit.
- **Chỉ gửi câu VietJobs**: câu nào có job_uid không thuộc `vietjobs_it` (câu crawl TopCV/ITviec, câu TEST) bị bỏ, không
  bao giờ rời máy. Guideline gửi kèm đã bỏ phần quy trình và mọi dòng ví dụ là chuỗi con của một câu `skill_test1`.
- Mỗi lần gọi gửi --batch câu, LLM trả danh sách span chép nguyên văn; span được dò lại trên token (khớp dài nhất,
  không chồng nhau) để ra nhãn BIO. Span không dò được thì đếm và bỏ.
- Ghi số token và chi phí ước (giá theo trang tổng hợp 11/2026, xem PRICES) sau mỗi lần gọi; dừng khi vượt --budget.
  Chạy lại cùng --name thì làm tiếp phần chưa gán.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from common.io import read_jsonl

ROOT = Path(__file__).resolve().parents[1]
GUIDELINE = ROOT / "annotation" / "guideline_skill.md"
TEST_BIO = ROOT / "data" / "annotation" / "skill_test1.bio.jsonl"
VIETJOBS_IT = ROOT / "data" / "vietjobs" / "vietjobs_it.parquet"
OUT_DIR = ROOT / "data" / "llm"
URL = "https://api.openai.com/v1/chat/completions"
# USD / 1 triệu token: (vào, vào có cache, ra). Lấy từ trang tổng hợp giá 11/2026, chưa đối chiếu trang OpenAI.
PRICES = {
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "gpt-6.1-terra": (1.00, 0.05, 5.00),
    "gpt-6.1-sol": (2.00, 0.10, 10.00),
}

INSTRUCTIONS = """Bạn là người gán nhãn dữ liệu cho bài toán trích kỹ năng từ tin tuyển dụng tiếng Việt.
Làm đúng theo hướng dẫn gán nhãn dưới đây (bản 0.4). Với mỗi câu được đưa:
- Liệt kê mọi span SKILL theo thứ tự xuất hiện trong câu.
- Mỗi span phải chép NGUYÊN VĂN từ câu: đúng chữ hoa/thường, đúng dấu, không sửa chính tả, không thêm bớt chữ.
- Kỹ năng xuất hiện nhiều lần trong câu thì liệt kê mỗi lần.
- Câu không có kỹ năng thì trả mảng rỗng.
Trả về JSON đúng schema, đủ mọi id được đưa.

=== HƯỚNG DẪN GÁN NHÃN ===
"""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "skills"],
                "properties": {"id": {"type": "integer"}, "skills": {"type": "array", "items": {"type": "string"}}},
            },
        }
    },
}


def norm(tokens: list[str]) -> str:
    return " ".join(tokens).lower()


def guideline_text() -> tuple[str, int]:
    """Guideline mục 1–5, bỏ dòng ví dụ là chuỗi con của câu TEST. Trả (văn bản, số dòng đã bỏ)."""
    from annotation.export_bio import TOKEN_RE

    test = [norm(json.loads(x)["tokens"]) for x in TEST_BIO.read_text("utf-8").splitlines() if x.strip()]
    body = GUIDELINE.read_text("utf-8").split("## 6. Quy trình")[0]
    keep, dropped = [], 0
    for line in body.splitlines():
        if line.startswith("| ") and not line.startswith(("| Câu", "| Nhóm", "| Không gán")):
            ex = norm(TOKEN_RE.findall(line.split("|")[1])).rstrip(" .")
            if len(ex) > 15 and any(ex in t for t in test):
                dropped += 1
                continue
        keep.append(line)
    return "\n".join(keep), dropped


def allowed_uids() -> set[str]:
    import pandas as pd

    return set(pd.read_parquet(VIETJOBS_IT, columns=["job_uid"])["job_uid"])


def to_bio(tokens: list[str], skills: list[str]) -> tuple[list[str], int]:
    """Dò span (chuỗi) trên token, không phân biệt hoa thường, mọi lần xuất hiện; span dài trước, không chồng."""
    from annotation.export_bio import TOKEN_RE

    tags = ["O"] * len(tokens)
    low = [t.lower() for t in tokens]
    miss = 0
    for s in sorted({s for s in skills if s.strip()}, key=lambda s: -len(TOKEN_RE.findall(s))):
        st = TOKEN_RE.findall(s)
        n = len(st)
        pat = [t.lower() for t in st]
        found = False
        for i in range(len(tokens) - n + 1):
            if n and low[i : i + n] == pat and all(t == "O" for t in tags[i : i + n]):
                tags[i] = "B-SKILL"
                tags[i + 1 : i + n] = ["I-SKILL"] * (n - 1)
                found = True
        miss += not found
    return tags, miss


def call(key: str, model: str, system: str, items: list[dict], effort: str | None) -> tuple[dict, dict]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "skills", "strict": True, "schema": SCHEMA}},
    }
    if effort:
        body["reasoning_effort"] = effort
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    data = json.load(urllib.request.urlopen(req, timeout=300))
    out = json.loads(data["choices"][0]["message"]["content"])
    return {it["id"]: it["skills"] for it in out["items"]}, data.get("usage", {})


def cost(model: str, usage: dict) -> float:
    p_in, p_cache, p_out = PRICES[model]
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    fresh = usage.get("prompt_tokens", 0) - cached
    return (fresh * p_in + cached * p_cache + usage.get("completion_tokens", 0) * p_out) / 1e6


def evaluate(path: Path, gold_path: Path) -> None:
    from seqeval.metrics import f1_score, precision_score, recall_score
    from seqeval.scheme import IOB2

    pred = {r["id"]: r["tags"] for r in map(json.loads, path.read_text("utf-8").splitlines())}
    gold = read_jsonl(gold_path)
    gold = [g for g in gold if g["id"] in pred]
    y, p = [g["tags"] for g in gold], [pred[g["id"]] for g in gold]
    kw = {"mode": "strict", "scheme": IOB2}
    print(
        f"{path.stem} trên {len(gold)} câu: P={precision_score(y, p, **kw):.3f} "
        f"R={recall_score(y, p, **kw):.3f} F1={f1_score(y, p, **kw):.3f}"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(PRICES))
    ap.add_argument("--bio", type=Path, required=True, help="file BIO đầu vào (dùng tokens, id, job_uid)")
    ap.add_argument("--name", required=True, help="tên đầu ra → data/llm/<name>.bio.jsonl")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--effort", default="low", help="reasoning_effort; 'none' để không gửi")
    ap.add_argument("--budget", type=float, default=0.5, help="USD; dừng khi chi phí ước vượt mức này")
    ap.add_argument("--limit", type=int, help="chỉ gán N câu đầu (chạy thử)")
    ap.add_argument("--eval", action="store_true", help="chấm với nhãn trong --bio (chỉ dùng cho dev)")
    args = ap.parse_args()

    env = (ROOT / ".env").read_text("utf-8").splitlines()
    key = next(x.split("=", 1)[1].strip() for x in env if x.startswith("OPENAI_API_KEY="))
    guide, dropped = guideline_text()
    system = INSTRUCTIONS + guide

    ok = allowed_uids()
    rows = read_jsonl(args.bio)
    blocked = sum(r["job_uid"] not in ok for r in rows)
    rows = [r for r in rows if r["job_uid"] in ok][: args.limit]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.name}.bio.jsonl"
    log = OUT_DIR / f"{args.name}.usage.jsonl"
    done = {json.loads(x)["id"] for x in out.read_text("utf-8").splitlines()} if out.exists() else set()
    spent = sum(json.loads(x)["usd"] for x in log.read_text("utf-8").splitlines()) if log.exists() else 0.0
    todo = [r for r in rows if r["id"] not in done]
    print(
        f"{len(rows)} câu VietJobs (chặn {blocked} câu không thuộc vietjobs_it); còn {len(todo)} câu; "
        f"guideline bỏ {dropped} dòng ví dụ trùng TEST; đã tốn ~${spent:.3f}",
        flush=True,
    )
    effort = None if args.effort == "none" else args.effort
    miss_total = 0
    with out.open("a", encoding="utf-8", newline="\n") as f, log.open("a", encoding="utf-8", newline="\n") as lg:
        for s in range(0, len(todo), args.batch):
            if spent >= args.budget:
                print(f"DỪNG: chi phí ước ${spent:.3f} ≥ ngân sách ${args.budget}", flush=True)
                break
            chunk = todo[s : s + args.batch]
            items = [{"id": k, "text": " ".join(r["tokens"])} for k, r in enumerate(chunk)]
            try:
                skills, usage = call(key, args.model, system, items, effort)
            except urllib.error.HTTPError as e:
                print(f"HTTP {e.code}: {e.read().decode()[:400]}", flush=True)
                break
            usd = cost(args.model, usage)
            spent += usd
            lg.write(json.dumps({"t": time.time(), "model": args.model, "usage": usage, "usd": usd}) + "\n")
            for k, r in enumerate(chunk):
                tags, miss = to_bio(r["tokens"], skills.get(k, []))
                miss_total += miss
                rec = {
                    "id": r["id"],
                    "job_uid": r["job_uid"],
                    "source": "vietjobs",
                    "tokens": r["tokens"],
                    "tags": tags,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            n = s + len(chunk)
            if n % (args.batch * 10) == 0 or n == len(todo):
                print(f"  {n}/{len(todo)} câu, ~${spent:.3f}, span không dò được: {miss_total}", flush=True)
    if args.eval:
        evaluate(out, args.bio)


if __name__ == "__main__":
    main()
