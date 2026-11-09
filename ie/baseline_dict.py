"""Baseline WM2: dò từ điển alias (ie/resources/skill_alias.csv) trên token, chấm bằng seqeval (strict, IOB2).

    uv run python -m ie.baseline_dict --bio data/annotation/skill_batch1.bio.jsonl --eval-set skill_batch1 --split dev

Cùng luật với annotation/preannotate_dict.py: bỏ nhóm "quá chung", alias ≤ 3 ký tự phân biệt hoa thường,
khớp dài nhất trước. In P/R/F1 và các cụm bỏ sót / gán thừa thường gặp để bổ sung từ điển.
Có --eval-set thì ghi thêm experiments/runs/<run_id>.json (FORMAT-ket-qua.md), kèm khoảng tin cậy 95% bootstrap theo câu.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from seqeval.metrics import classification_report, f1_score, precision_score, recall_score
from seqeval.scheme import IOB2

from annotation.export_bio import TOKEN_RE
from annotation.preannotate_dict import MODEL_VERSION, load_aliases
from experiments.runlog import bootstrap_ci, save_run


def build_index(forms: list[str]) -> tuple[dict[tuple[str, ...], bool], int]:
    """Khóa = chuỗi token (chữ thường nếu không phân biệt hoa thường) → có phân biệt hoa thường không."""
    index: dict[tuple[str, ...], bool] = {}
    for f in forms:
        toks = tuple(TOKEN_RE.findall(f))
        cs = len(f) <= 3
        index[toks if cs else tuple(t.lower() for t in toks)] = cs
    return index, max(len(k) for k in index)


def tag(tokens: list[str], index: dict[tuple[str, ...], bool], max_len: int) -> list[str]:
    tags = ["O"] * len(tokens)
    i = 0
    while i < len(tokens):
        for n in range(min(max_len, len(tokens) - i), 0, -1):
            win = tuple(tokens[i : i + n])
            if index.get(win) is True or index.get(tuple(t.lower() for t in win)) is False:
                tags[i] = "B-SKILL"
                tags[i + 1 : i + n] = ["I-SKILL"] * (n - 1)
                i += n
                break
        else:
            i += 1
    return tags


def spans(tokens: list[str], tags: list[str]) -> list[tuple[int, int, str]]:
    out, start = [], None
    for i, t in enumerate(tags + ["O"]):
        if start is not None and t != "I-SKILL":
            out.append((start, i, " ".join(tokens[start:i])))
            start = None
        if t == "B-SKILL":
            start = i
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bio", required=True)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--eval-set", help="tên tập (vd skill_batch1); có thì ghi file kết quả JSON")
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--snapshot")
    args = ap.parse_args()

    rows = [json.loads(line) for line in Path(args.bio).read_text(encoding="utf-8").splitlines() if line]
    index, max_len = build_index(load_aliases())
    gold = [r["tags"] for r in rows]
    pred = [tag(r["tokens"], index, max_len) for r in rows]
    fn, fp = Counter(), Counter()
    for r, p in zip(rows, pred, strict=True):
        g_sp = {(a, b): s for a, b, s in spans(r["tokens"], r["tags"])}
        p_sp = {(a, b): s for a, b, s in spans(r["tokens"], p)}
        fn.update(s.lower() for k, s in g_sp.items() if k not in p_sp)
        fp.update(s.lower() for k, s in p_sp.items() if k not in g_sp)
    kw = {"mode": "strict", "scheme": IOB2}
    metrics = {
        "precision": precision_score(gold, pred, **kw),
        "recall": recall_score(gold, pred, **kw),
        "f1": f1_score(gold, pred, **kw),
    }
    print(f"{len(rows)} câu | P={metrics['precision']:.3f} R={metrics['recall']:.3f} F1={metrics['f1']:.3f}")
    print(classification_report(gold, pred, digits=3, **kw))
    print("Bỏ sót nhiều nhất:", fn.most_common(args.top))
    print("Gán thừa / lệch ranh giới:", fp.most_common(args.top))
    if args.eval_set:
        ci = bootstrap_ci(len(rows), lambda ix: f1_score([gold[i] for i in ix], [pred[i] for i in ix], **kw))
        path = save_run(
            task="WM2",
            rq="RQ3",
            method=MODEL_VERSION,
            eval_set=args.eval_set,
            split=args.split,
            snapshot=args.snapshot,
            metrics=metrics,
            ci95={"f1": ci},
            ids=[r["id"] for r in rows],
            n_gold=sum(t == "B-SKILL" for g in gold for t in g),
        )
        print(f"F1 CI95 = {ci} → {path}")


if __name__ == "__main__":
    main()
