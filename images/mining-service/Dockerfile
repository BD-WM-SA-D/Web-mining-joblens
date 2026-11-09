# mining-service bản stub (ADR 0002, hợp đồng service/contract/mining.v1.yaml). Build từ gốc repo:
#   uv run python -m service.index            # tạo data/index/job_skills.json (chỉ job_uid + skill_id)
#   TAG=0.1.0-$(git rev-parse --short HEAD)   # tag x.y.z-gitsha, không dùng latest
#   docker build -f images/mining-service/Dockerfile -t joblens/mining-service:$TAG .
#   docker run --rm -p 8091:8091 joblens/mining-service:$TAG
# Không có chỉ mục thì service vẫn chạy, /health báo "degraded" và /v1/recommend trả danh sách rỗng.
FROM ghcr.io/astral-sh/uv:0.12.0 AS uv

FROM python:3.12-slim AS deps
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /src
COPY pyproject.toml uv.lock ./
# Chỉ cài nhóm "service" (FastAPI, uvicorn), không kéo scrapy/pandas/underthesea của các bài khác
RUN uv export --frozen --only-group service --no-hashes -o /tmp/req.txt \
 && uv pip install --system --no-cache -r /tmp/req.txt

FROM deps
WORKDIR /app
COPY annotation/__init__.py annotation/preannotate_dict.py annotation/
COPY ie/resources/skill_alias.csv ie/resources/
COPY service/ service/
COPY data/inde[x]/ data/index/
ENV JOBLENS_MINING_INDEX=/app/data/index/job_skills.json
EXPOSE 8091
USER nobody
# --no-access-log: không ghi log request (ADR 0002 – không log nội dung người dùng)
CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8091", "--no-access-log"]
