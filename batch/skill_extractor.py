"""Image `skill-extractor` (WM2): silver.job_postings → silver.job_skills (overwrite_partition).

    # chạy một mình trên file cục bộ (snapshot TopCV), bản stub từ điển
    uv run python -m batch.skill_extractor --input-file data/crawl/topcv/topcv_20261115.parquet \\
        --output-file data/batch/job_skills.parquet --run-id local-1 --stub
    # như Airflow gọi (ADR 0001 D3)
    python -m batch.skill_extractor --input-table silver.job_postings --input-snapshot <id> \\
        --output-table silver.job_skills --run-id <airflow-run-id>

Hai chế độ:
- `--stub`: từ điển alias (`ie/resources/skill_alias.csv`, baseline WM2, F1 0,442 trên `skill_test1`). Không cần
  torch, vài giây cho vài nghìn tin.
- mặc định: PhoBERT fine-tune trên nhãn yếu (F1 0,730 trên `skill_test1`), thư mục model ở `JOBLENS_SKILL_MODEL`
  (mặc định `data/models/skill-extractor`). Cần nhóm `ml`. Trên CPU chậm hơn nhiều – nhóm BD cần đo
  thời gian cho 50k tin trước khi đưa vào DAG hằng ngày.

Mỗi tin lấy kỹ năng từ ba trường: `description`, `requirements` (span ký tự trong trường đó) và `skill_tags`
(tag nhà tuyển dụng, span = chỉ số tag, theo contract). `skill_id` là ESCO URI nếu từ điển có, không thì
`joblens:<slug>`. Confidence: từ điển 0,9, tag nhà tuyển dụng 1,0, PhoBERT 0,8 – đều là mức cố định để app lọc
được, **không** phải xác suất đã hiệu chỉnh.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from batch.tables import ROOT, add_io_args, load_input, save_output, version
from service.skills import DICT_CONFIDENCE, SkillCatalog, slug

TEXT_FIELDS = ("description", "requirements")
TAG_CONFIDENCE = 1.0
MODEL_CONFIDENCE = 0.8
TOKEN_RE = re.compile(r"\w+[+#]*|[^\w\s]")  # cùng cách tách token với annotation/export_bio.py
SENT_RE = re.compile(r"[^\n]+")  # tập test WM2 là các dòng của mô tả; mô hình train trên đúng đơn vị đó
INPUT_COLUMNS = ("job_uid", "description", "requirements", "skill_tags")


def row(job_uid: str, skill_id: str, surface: str, field: str, start: int, end: int, conf: float, ver: str, run: str):
    return {
        "job_uid": job_uid,
        "skill_id": skill_id,
        "surface_form": surface,
        "field": field,
        "span_start": start,
        "span_end": end,
        "confidence": conf,
        "extractor_version": ver,
        "run_id": run,
    }


def tag_rows(job: dict, catalog: SkillCatalog, ver: str, run: str) -> list[dict]:
    out = []
    tags = job.get("skill_tags")
    for i, tag in enumerate([] if tags is None else list(tags)):
        tag = str(tag).strip()
        if not tag:
            continue
        skill = catalog.lookup(tag)
        sid = skill.skill_id if skill else f"joblens:{slug(tag)}"
        out.append(row(job["job_uid"], sid, tag, "skill_tags", i, i + 1, TAG_CONFIDENCE, ver, run))
    return out


def dict_rows(job: dict, catalog: SkillCatalog, ver: str, run: str) -> list[dict]:
    out = []
    for field in TEXT_FIELDS:
        text = job.get(field) or ""
        for start, end, surface, skill in catalog.extract(text):
            out.append(row(job["job_uid"], skill.skill_id, surface, field, start, end, DICT_CONFIDENCE, ver, run))
    return out


def bio_spans(tokens: list[tuple[int, int]], tags: list[str]) -> list[tuple[int, int]]:
    """Tag BIO trên token → (start, end) ký tự."""
    spans, cur = [], None
    for (s, e), t in zip(tokens, tags, strict=True):
        if t == "B-SKILL" or (t == "I-SKILL" and cur is None):
            if cur:
                spans.append(cur)
            cur = [s, e]
        elif t == "I-SKILL":
            cur[1] = e
        else:
            if cur:
                spans.append(cur)
            cur = None
    if cur:
        spans.append(cur)
    return [tuple(x) for x in spans]


class PhoBERT:
    def __init__(self, model_dir: Path, max_len: int = 256) -> None:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForTokenClassification.from_pretrained(model_dir).to(self.device)
        self.max_len = max_len

    def spans(self, texts: list[str]) -> list[list[tuple[int, int]]]:
        """Mỗi văn bản → các span kỹ năng (ký tự). Tách dòng, tách token như lúc train, rồi ghép lại."""
        from ie.phobert import predict, prepare

        units, where = [], []  # where: (văn bản thứ i, offset dòng, token offsets)
        for i, text in enumerate(texts):
            for m in SENT_RE.finditer(text or ""):
                toks = [(t.start(), t.end()) for t in TOKEN_RE.finditer(m.group())]
                if toks:
                    units.append({"id": f"{i}:{m.start()}", "tokens": [m.group()[s:e] for s, e in toks]})
                    where.append((i, m.start(), toks))
        out: list[list[tuple[int, int]]] = [[] for _ in texts]
        if not units:
            return out
        tags = predict(self.model, self.tok, prepare(units), self.max_len, self.device)
        for (i, base, toks), t in zip(where, tags, strict=True):
            out[i] += [(base + s, base + e) for s, e in bio_spans(toks, t)]
        return out


def model_rows(jobs: list[dict], model: PhoBERT, catalog: SkillCatalog, ver: str, run: str) -> list[dict]:
    out = []
    for field in TEXT_FIELDS:
        texts = [j.get(field) or "" for j in jobs]
        for job, text, spans in zip(jobs, texts, model.spans(texts), strict=True):
            for s, e in spans:
                surface = text[s:e]
                skill = catalog.lookup(surface)
                sid = skill.skill_id if skill else f"joblens:{slug(surface)}"
                out.append(row(job["job_uid"], sid, surface, field, s, e, MODEL_CONFIDENCE, ver, run))
    return out


def extract(jobs: list[dict], stub: bool, run_id: str, model: PhoBERT | None = None) -> list[dict]:
    catalog = SkillCatalog()
    ver = version(stub)
    out = []
    for job in jobs:
        out += tag_rows(job, catalog, ver, run_id)
    if stub:
        for job in jobs:
            out += dict_rows(job, catalog, ver, run_id)
    else:
        out += model_rows(jobs, model, catalog, ver, run_id)
    # khóa chính (job_uid, field, span_start, span_end): bỏ bản trùng nếu có
    seen, uniq = set(), []
    for r in out:
        k = (r["job_uid"], r["field"], r["span_start"], r["span_end"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_io_args(ap, "silver.job_skills")
    args = ap.parse_args()
    jobs = load_input(args, INPUT_COLUMNS)
    model = None
    if not args.stub:
        model_dir = Path(os.environ.get("JOBLENS_SKILL_MODEL", ROOT / "data" / "models" / "skill-extractor"))
        model = PhoBERT(model_dir)
    rows = extract(jobs, args.stub, args.run_id, model)
    print(f"{len(jobs)} tin → {len(rows)} kỹ năng ({version(args.stub)})", flush=True)
    save_output(rows, args, key="job_uid")


if __name__ == "__main__":
    main()
