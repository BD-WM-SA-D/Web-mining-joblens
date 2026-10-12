"""Hàm dùng chung cho mọi crawler: lọc PII, HTML → văn bản, đóng gói message theo hợp đồng joblens."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from functools import cache

from jsonschema import Draft202012Validator
from lxml import html as lxml_html

from joblens_contracts import load_schema

# Thông tin cá nhân hay gặp trong mô tả tin (người liên hệ để lại email/SĐT) – che trước khi ra khỏi crawler (ADR 0001 D1)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+84|0)(?:[\s.-]?\d){8,10}(?!\d)")
BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"}


def mask_pii(text: str | None) -> str | None:
    if text is None:
        return None
    return PHONE_RE.sub("<PHONE>", EMAIL_RE.sub("<EMAIL>", text))


def html_to_text(fragment: str | None) -> str | None:
    """HTML mô tả → văn bản thuần, mỗi <li> thành một dòng "- ...", giữ ngắt đoạn."""
    if not fragment or not fragment.strip():
        return None
    root = lxml_html.fragment_fromstring(fragment, create_parent="div")
    for li in root.iter("li"):
        li.text = "- " + (li.text or "")
    for el in root.iter():
        if el.tag in BLOCK_TAGS:
            el.tail = "\n" + (el.tail or "")
    text = root.text_content().replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    out = "\n".join(ln for ln in lines if ln)
    return out or None


def content_hash(payload: dict) -> str:
    """SHA-256 của payload đã chuẩn hóa (khóa sắp xếp) – đổi nội dung thì đổi hash."""
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def job_message(
    source: str,
    source_job_id: str,
    url: str | None,
    payload: dict,
    lastmod: str | None = None,
    crawl_ts: str | None = None,
) -> dict:
    """Đóng gói một tin theo job_posting.v1 (schema ở repo joblens)."""
    return {
        "schema_version": "job_posting.v1",
        "source": source,
        "source_job_id": source_job_id,
        "url": url,
        "crawl_ts": crawl_ts or utc_now(),
        "lastmod": lastmod,
        "content_hash": content_hash(payload),
        "payload": payload,
    }


def parse_error_message(
    source: str,
    error_type: str,
    error_message: str,
    url: str | None = None,
    source_record_id: str | None = None,
    component_version: str | None = None,
) -> dict:
    """Bản ghi lỗi theo parse_error.v1 (topic dlq.parse_errors.v1)."""
    return {
        "schema_version": "parse_error.v1",
        "source": source,
        "url": url,
        "source_record_id": source_record_id,
        "error_type": error_type,
        "error_message": error_message[:2000],
        "error_ts": utc_now(),
        "component_version": component_version,
    }


@cache
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(load_schema(name), format_checker=Draft202012Validator.FORMAT_CHECKER)


def schema_errors(message: dict, schema: str = "job_posting.v1") -> list[str]:
    """Danh sách lỗi so với schema (rỗng = hợp lệ)."""
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in _validator(schema).iter_errors(message)]
