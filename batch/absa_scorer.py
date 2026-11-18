"""Image `absa-scorer` (WM3): bronze.reviews_raw → silver.review_aspects (contract 0.2.0), mức câu.

    uv run python -m batch.absa_scorer --input-file data/crawl/itviec/reparse-2026-11-15/reviews.jsonl \\
        --output-file data/batch/review_aspects.parquet --run-id local-1 --stub
    python -m batch.absa_scorer --input-table bronze.reviews_raw --input-snapshot <id> \\
        --output-table silver.review_aspects --run-id <airflow-run-id>

Đầu vào là message `review.v1` (file JSONL của crawler) hoặc dòng `bronze.reviews_raw` (cột `payload_json`).
Tách câu bằng `absa/split.py` như lúc gán nhãn, rồi:
- `--stub`: từ điển `dict-v3` (macro pos/neg 0,518 trên TEST WM3).
- mặc định: mô hình lai (khía cạnh từ từ điển, cực tính bằng hồi quy logistic trên tín hiệu từ điển + TF-IDF +
  phần của review), 0,590 trên TEST. Train lúc khởi động trên 200 câu dev gán tay (~3 giây), file nhãn ở
  `JOBLENS_ABSA_GOLD_DIR` (mặc định `data/annotation/`). **Đọc kèm kết quả:** luật một dòng theo phần của review
  được 0,583 trên cùng tập – phần mô hình học thêm là nhỏ (xem `experiments/results.md`).

Mỗi khía cạnh nhận diện được trong câu là một dòng. Câu không có khía cạnh nào thì không ghi. `sentence_index`
đánh số liên tục theo thứ tự: "Điều tôi thích" → "Đề nghị cải thiện" → tiêu đề review. `sentence_text` qua lại bộ
lọc PII trước khi ghi. `company_key` theo quy tắc trong contract `gold.dim_company` (bỏ dấu, bỏ loại hình pháp
lý, nối bằng "-") – cần khớp cách Big Data tính, xem issue cross-repo. Confidence là mức cố định (từ điển 0,6,
mô hình lai 0,7), không phải xác suất đã hiệu chỉnh.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from datetime import date
from pathlib import Path

from absa.lexicon import predict as dict_predict
from absa.split import sentences_of
from batch.tables import ROOT, add_io_args, load_input, save_output, version
from crawler.common import mask_pii

DICT_CONFIDENCE = 0.6
MODEL_CONFIDENCE = 0.7
SECTION_ORDER = ("liked", "improvement", "title")
LEGAL_FORMS = re.compile(
    r"\b(cong ty|cty|co phan|tnhh|trach nhiem huu han|mot thanh vien|hai thanh vien tro len|mtv|jsc|"
    r"joint stock company|company|co ltd|co|ltd|limited|corp|corporation|inc|llc|plc)\b"
)


def fold(text: str | None) -> str:
    s = unicodedata.normalize("NFKD", (text or "").replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def company_key(name: str | None) -> str | None:
    f = fold(name)
    if not f:
        return None
    core = re.sub(r"\s+", " ", LEGAL_FORMS.sub(" ", f)).strip()
    return (core or f).replace(" ", "-")


def as_message(r: dict) -> dict:
    """Dòng bronze (`payload_json` là chuỗi) hoặc message review.v1 → message review.v1."""
    if "payload" not in r and "payload_json" in r:
        r = {**r, "payload": json.loads(r["payload_json"])}
    return r


def review_uid(source: str, source_review_id: str) -> str:
    return hashlib.sha1(f"{source}:{source_review_id}".encode()).hexdigest()


def month_start(review_month: str | None) -> date | None:
    m = re.match(r"^(\d{4})-(\d{2})", review_month or "")
    return date(int(m.group(1)), int(m.group(2)), 1) if m else None


def ordered_sentences(review: dict) -> list[dict]:
    sents = sentences_of(review)
    sents.sort(key=lambda s: (SECTION_ORDER.index(s["section"]), s["sent_idx"]))
    return sents


class Hybrid:
    """Mô hình lai đã chấm trên TEST WM3, train lại trên 200 câu dev mỗi lần khởi động."""

    def __init__(self, gold_dir: Path) -> None:
        from absa.eval_dev import SENTS, dev_set

        gold = [gold_dir / "absa_trial.absa.jsonl", gold_dir / "absa_dev2.absa.jsonl"]
        rows, sents, _ = dev_set(gold, SENTS)
        self.train = [{**s, "gold": r["gold"]} for r, s in zip(rows, sents, strict=True)]

    def predict(self, sents: list[dict]) -> list[dict[str, str]]:
        from absa.supervised import fit_predict_hybrid

        return fit_predict_hybrid(self.train, sents, seed=1) if sents else []


def score(messages: list[dict], stub: bool, run_id: str, model: Hybrid | None = None) -> list[dict]:
    ver = version(stub)
    items = []  # (message, sentence_index, sentence)
    for raw in messages:
        msg = as_message(raw)
        for i, s in enumerate(ordered_sentences(msg)):
            items.append((msg, i, s))
    sents = [s for _, _, s in items]
    if stub:
        preds = [{p["aspect"]: p["polarity"] for p in dict_predict(s["text"])} for s in sents]
        conf = DICT_CONFIDENCE
    else:
        preds = model.predict(sents)
        conf = MODEL_CONFIDENCE
    out = []
    for (msg, i, s), pred in zip(items, preds, strict=True):
        p = msg["payload"]
        for aspect, polarity in sorted(pred.items()):
            out.append(
                {
                    "review_uid": review_uid(msg["source"], msg["source_review_id"]),
                    "company_key": company_key(p.get("company_name")) or msg.get("company_id"),
                    "review_date": month_start(p.get("review_month")),
                    "sentence_index": i,
                    "sentence_text": mask_pii(s["text"]),
                    "aspect": aspect,
                    "polarity": polarity,
                    "confidence": conf,
                    "model_version": ver,
                    "run_id": run_id,
                }
            )
    return [r for r in out if r["review_date"] is not None]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_io_args(ap, "silver.review_aspects")
    args = ap.parse_args()
    messages = load_input(args)
    model = None if args.stub else Hybrid(Path(os.environ.get("JOBLENS_ABSA_GOLD_DIR", ROOT / "data" / "annotation")))
    rows = score(messages, args.stub, args.run_id, model)
    print(f"{len(messages)} review → {len(rows)} dòng khía cạnh ({version(args.stub)})", flush=True)
    save_output(rows, args, key="review_uid")


if __name__ == "__main__":
    main()
