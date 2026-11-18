# Image mô hình của WM chạy theo hợp đồng ADR 0001 D3: skill-extractor, job-dedup, absa-scorer.
# Một Dockerfile cho cả ba (JOB chọn module), hai bản (target):
#   stub – không torch, không model; skill-extractor dùng từ điển, absa-scorer dùng từ điển, job-dedup dùng khóa
#          tiêu đề + công ty chính xác. Nhỏ, chạy vài giây – để Big Data dựng DAG trước khi có image thật.
#   full – PhoBERT v3 (torch CPU) cho skill-extractor, mô hình lai cho absa-scorer, dedup v2 cho job-dedup.
#          Cần có sẵn trong data/: data/models/wm2-phobert-v3-s1/, data/annotation/absa_trial|absa_dev2.absa.jsonl,
#          data/absa/sentences.jsonl (build trên máy của WM, không có trong git).
#
# Build từ gốc repo, tag x.y.z-gitsha (không dùng latest):
#   V=0.1.0-$(git rev-parse --short HEAD)
#   docker build -f images/batch/Dockerfile --target stub --build-arg JOB=job_dedup --build-arg VERSION=$V \
#       -t joblens/job-dedup:$V-stub .
#   docker build -f images/batch/Dockerfile --target full --build-arg JOB=skill_extractor --build-arg VERSION=$V \
#       -t joblens/skill-extractor:$V .
# Chạy (Airflow KubernetesPodOperator truyền đúng các tham số này; biến JOBLENS_* lấy từ Secret của Big Data):
#   docker run --rm --env-file .env joblens/job-dedup:$V-stub \
#       --input-table silver.job_postings --output-table silver.job_dedup --run-id manual-1
#
# CHƯA build thử (2026-11-18: Docker Desktop trên máy WM chưa bật). Lần build đầu cần kiểm tra lại.

FROM ghcr.io/astral-sh/uv:0.12.0 AS uv

FROM python:3.12-slim AS deps-stub
COPY --from=uv /uv /usr/local/bin/uv
# git: joblens-contracts cài từ git (pyproject, tool.uv.sources)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-default-groups --group lakehouse --no-hashes -o /tmp/req.txt \
 && uv pip install --system --no-cache -r /tmp/req.txt

FROM deps-stub AS deps-full
# torch bản CPU (uv.lock trỏ bản CUDA cho máy dev có GPU – quá nặng và vô ích trong pod CPU)
ARG TORCH_VERSION=2.11.0
RUN uv export --frozen --only-group ml --no-emit-package torch --no-hashes -o /tmp/ml.txt \
 && uv pip install --system --no-cache torch==${TORCH_VERSION} --index-url https://download.pytorch.org/whl/cpu \
 && uv pip install --system --no-cache -r /tmp/ml.txt

FROM deps-stub AS stub
ARG JOB
ARG VERSION
WORKDIR /app
COPY absa/ absa/
COPY annotation/ annotation/
COPY batch/ batch/
COPY crawler/ crawler/
COPY experiments/ experiments/
COPY ie/ ie/
COPY service/ service/
ENV JOBLENS_JOB=batch.${JOB} JOBLENS_IMAGE_VERSION=${VERSION} JOBLENS_STUB=1 PYTHONUNBUFFERED=1
USER nobody
ENTRYPOINT ["sh", "-c", "exec python -m \"$JOBLENS_JOB\" \"$@\"", "--"]

FROM deps-full AS full
ARG JOB
ARG VERSION
WORKDIR /app
COPY absa/ absa/
COPY annotation/ annotation/
COPY batch/ batch/
COPY crawler/ crawler/
COPY experiments/ experiments/
COPY ie/ ie/
COPY service/ service/
COPY data/models/wm2-phobert-v3-s1/ data/models/wm2-phobert-v3-s1/
COPY data/annotation/absa_trial.absa.jsonl data/annotation/absa_dev2.absa.jsonl data/annotation/
COPY data/absa/sentences.jsonl data/absa/
ENV JOBLENS_JOB=batch.${JOB} JOBLENS_IMAGE_VERSION=${VERSION} JOBLENS_STUB=0 PYTHONUNBUFFERED=1 \
    HF_HOME=/tmp/hf
USER nobody
ENTRYPOINT ["sh", "-c", "exec python -m \"$JOBLENS_JOB\" \"$@\"", "--"]
