"""Gửi tin và review đã crawl (JSONL trong data/crawl/) vào Kafka của nền tảng Big Data (ADR 0001 D1).

    # kiểm thử: chỉ kiểm schema và đếm, không cần Kafka
    uv run python -m crawler.producer data/crawl/topcv/2026-11-18/jobs.jsonl --dry-run
    # gửi thật (cần `uv sync --group kafka` và biến JOBLENS_KAFKA_BOOTSTRAP, ví dụ sau port-forward của BD)
    uv run python -m crawler.producer data/crawl/topcv/*/jobs.jsonl data/crawl/itviec-jobs/*/jobs.jsonl \\
        data/crawl/itviec/reparse-2026-11-15/reviews.jsonl

Mỗi dòng là một message đã đóng gói bằng `crawler/common.py` (`job_posting.v1` hoặc `review.v1`). Chọn topic theo
`schema_version` và `source`: `jobs.raw.<nguồn>.v1`, `reviews.raw.<nguồn>.v1`; key là `source_job_id` /
`source_review_id` (cùng tin vào cùng partition, BD `MERGE` theo `job_uid`). Message sai schema **không gửi** vào
topic dữ liệu mà gửi một bản ghi `parse_error.v1` vào `dlq.parse_errors.v1`. File `parse_errors.jsonl` của
crawler (đã là `parse_error.v1`) thì gửi thẳng vào DLQ.

Không có `JOBLENS_KAFKA_BOOTSTRAP` thì tự chuyển sang `--dry-run` (repo này phải chạy được một mình). Producer bật
idempotence và `acks=all` để gửi lại không sinh bản trùng ở phía Kafka.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from crawler.common import parse_error_message, schema_errors

DLQ = "dlq.parse_errors.v1"
COMPONENT = "crawler.producer:0.1.0"


def route(msg: dict) -> tuple[str, str | None, dict]:
    """Message → (topic, key, message thật sự gửi). Sai schema thì đổi thành parse_error.v1 vào DLQ."""
    kind = msg.get("schema_version")
    if kind == "parse_error.v1":
        return DLQ, msg.get("source_record_id"), msg
    if kind not in ("job_posting.v1", "review.v1"):
        err = parse_error_message(
            msg.get("source") or "unknown", "schema", f"schema_version không hỗ trợ: {kind!r}", msg.get("url")
        )
        return DLQ, None, {**err, "component_version": COMPONENT}
    errors = schema_errors(msg, kind)
    key = msg.get("source_job_id") if kind == "job_posting.v1" else msg.get("source_review_id")
    if errors:
        err = parse_error_message(
            msg.get("source") or "unknown",
            "schema",
            "; ".join(errors),
            msg.get("url"),
            source_record_id=key,
            component_version=COMPONENT,
        )
        return DLQ, key, err
    topic = f"{'jobs' if kind == 'job_posting.v1' else 'reviews'}.raw.{msg['source']}.v1"
    return topic, key, msg


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def make_producer(bootstrap: str):
    from confluent_kafka import Producer

    return Producer(
        {
            "bootstrap.servers": bootstrap,
            "enable.idempotence": True,
            "acks": "all",
            "compression.type": "zstd",
            "client.id": "joblens-wm-crawler",
        }
    )


def send(paths: list[Path], producer=None) -> Counter:
    """Gửi mọi file; trả về số message theo topic. `producer=None` = dry-run."""
    count: Counter = Counter()
    failed: list[str] = []

    def on_delivery(err, msg) -> None:
        if err is not None:
            failed.append(str(err))

    for path in paths:
        for msg in read_jsonl(path):
            topic, key, value = route(msg)
            count[topic] += 1
            if producer is not None:
                producer.produce(
                    topic,
                    key=key.encode() if key else None,
                    value=json.dumps(value, ensure_ascii=False).encode("utf-8"),
                    on_delivery=on_delivery,
                )
                producer.poll(0)
    if producer is not None:
        left = producer.flush(60)
        if left or failed:
            raise SystemExit(f"gửi lỗi: {len(failed)} message lỗi, {left} message chưa gửi xong. Ví dụ: {failed[:3]}")
    return count


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", type=Path, nargs="+", help="file JSONL: jobs.jsonl, reviews.jsonl, parse_errors.jsonl")
    ap.add_argument("--dry-run", action="store_true", help="chỉ kiểm schema và đếm, không gửi")
    args = ap.parse_args()
    bootstrap = os.environ.get("JOBLENS_KAFKA_BOOTSTRAP")
    if not bootstrap and not args.dry_run:
        print("Không có JOBLENS_KAFKA_BOOTSTRAP → chạy dry-run (không gửi gì).")
    dry = args.dry_run or not bootstrap
    count = send(args.files, None if dry else make_producer(bootstrap))
    verb = "sẽ gửi" if dry else "đã gửi"
    for topic, n in sorted(count.items()):
        print(f"{verb} {n:5d} → {topic}")


if __name__ == "__main__":
    main()
