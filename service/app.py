"""mining-service bản stub (ADR 0002) theo hợp đồng service/contract/mining.v1.yaml.

    uv sync --group service
    uv run uvicorn service.app:app --port 8091

- POST /v1/skills:extract – trích kỹ năng bằng từ điển alias (baseline WM2). Đặt `JOBLENS_MINING_SKILL_MODEL`
  (thư mục model PhoBERT, cùng model với image skill-extractor) thì dùng PhoBERT trên CPU; span được tra từ điển
  để ra skill_id, không có thì `joblens:<slug>`. Cần nhóm `ml`.
- POST /v1/recommend – đếm kỹ năng trùng với chỉ mục tin (service/index.py).
- GET /health – "degraded" khi chưa có chỉ mục gợi ý.

Không lưu và không ghi log văn bản đầu vào (ADR 0002, quyết định 3).
Chưa làm: lọc location_codes / level_code (chưa có ánh xạ tỉnh sang gold.dim_location), gộp theo dup_group_id (chờ WM1).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from service.skills import DICT_CONFIDENCE, SkillCatalog, slug

MODEL_CONFIDENCE = 0.8  # như image skill-extractor: mức cố định, không phải xác suất

STUB_VERSION = "stub-dict-alias"
MODEL_DIR = os.environ.get("JOBLENS_MINING_SKILL_MODEL")
INDEX_PATH = Path(os.environ.get("JOBLENS_MINING_INDEX", "data/index/job_skills.json"))

app = FastAPI(title="JobLens Mining API", version="0.1.0")
catalog = SkillCatalog()


def _load_model(model_dir: str | None):
    if not model_dir:
        return None, STUB_VERSION
    from batch.skill_extractor import PhoBERT

    return PhoBERT(Path(model_dir)), f"skill-extractor:{os.environ.get('JOBLENS_IMAGE_VERSION', 'local')}"


skill_model, MODEL_VERSION = _load_model(MODEL_DIR)


def _load_index(path: Path) -> tuple[dict[str, set[str]], str | None]:
    if not path.exists():
        return {}, None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {uid: set(ids) for uid, ids in data["jobs"].items()}, data.get("snapshot")


job_index, index_snapshot = _load_index(INDEX_PATH)


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=20000)
    min_confidence: float = Field(default=0.5, ge=0, le=1)


class RecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill_ids: list[str] = Field(min_length=1, max_length=50)
    k: int = Field(default=10, ge=1, le=50)
    location_codes: list[str] | None = None
    level_code: str | None = None


@app.exception_handler(RequestValidationError)
async def _bad_request(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Hợp đồng dùng 400 {error}; chỉ trả vị trí và loại lỗi, không lặp lại văn bản đầu vào
    msg = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['type']}" for e in exc.errors())
    return JSONResponse(status_code=400, content={"error": msg})


@app.exception_handler(HTTPException)
async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
    # Lỗi do FastAPI tự sinh (body không phải JSON, sai đường dẫn…) cũng trả đúng dạng {error}
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.get("/health")
def health() -> dict:
    out = {"status": "ok" if job_index else "degraded", "model_version": MODEL_VERSION}
    if index_snapshot:
        out["index_snapshot"] = index_snapshot
    return out


@app.post("/v1/skills:extract")
def extract(req: ExtractRequest) -> dict:
    skills = []
    if skill_model is not None:
        if MODEL_CONFIDENCE >= req.min_confidence:
            for start, end in skill_model.spans([req.text])[0]:
                surface = req.text[start:end]
                skill = catalog.lookup(surface)
                skills.append(
                    {
                        "skill_id": skill.skill_id if skill else f"joblens:{slug(surface)}",
                        "label": skill.label if skill else surface,
                        "surface_form": surface,
                        "start": start,
                        "end": end,
                        "confidence": MODEL_CONFIDENCE,
                    }
                )
    elif DICT_CONFIDENCE >= req.min_confidence:
        for start, end, surface, skill in catalog.extract(req.text):
            skills.append(
                {
                    "skill_id": skill.skill_id,
                    "label": skill.label,
                    "surface_form": surface,
                    "start": start,
                    "end": end,
                    "confidence": DICT_CONFIDENCE,
                }
            )
    return {"skills": skills, "model_version": MODEL_VERSION}


@app.post("/v1/recommend")
def recommend(req: RecommendRequest) -> dict:
    profile = set(req.skill_ids)
    scored = []
    for uid, job_skills in job_index.items():
        matched = profile & job_skills
        if matched:
            # điểm = số kỹ năng trùng, cộng phần nhỏ theo tỉ lệ tin được phủ để tin thiếu ít kỹ năng xếp trước
            score = len(matched) + len(matched) / len(job_skills) / 10
            scored.append((score, uid, matched, job_skills - profile))
    scored.sort(key=lambda x: (-x[0], x[1]))
    items = [
        {"job_uid": uid, "score": round(s, 4), "matched_skill_ids": sorted(m), "missing_skill_ids": sorted(miss)}
        for s, uid, m, miss in scored[: req.k]
    ]
    return {"items": items, "strategy": "stub", "model_version": MODEL_VERSION}
