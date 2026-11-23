# Image mô hình của WM chạy theo hợp đồng ADR 0001 D3: skill-extractor, job-dedup, absa-scorer.
# Một Dockerfile cho cả ba (JOB chọn module), ba bản (target):
#   stub      – không torch, không model; skill-extractor dùng từ điển, absa-scorer dùng từ điển, job-dedup
#               dùng khóa tiêu đề + công ty chính xác. Nhỏ, chạy vài giây – để nhóm vận hành dựng DAG trước.
#   light     – bản thật của job-dedup (MinHash LSH) và absa-scorer (mô hình lai: từ điển + hồi quy logistic).
#               Hai job này **không dùng torch**, nên không cài nhóm ml: nhẹ hơn bản ml khoảng vài GB.
#               Cần có sẵn data/annotation/absa_trial|absa_dev2.absa.jsonl và data/absa/sentences.jsonl.
#   ml        – bản thật của skill-extractor: PhoBERT (torch CPU) + model trong data/models/skill-extractor/.
#               Chỉ build target này cho skill-extractor.
#
# Build từ gốc repo, tag x.y.z-gitsha (không dùng latest; phiên bản ghi ở models.yaml):
#   V=0.1.1-$(git rev-parse --short HEAD)
#   docker build -f images/batch/Dockerfile --target stub  --build-arg JOB=job_dedup --build-arg VERSION=$V \
#       -t joblens/job-dedup:$V-stub .
#   docker build -f images/batch/Dockerfile --target light --build-arg JOB=job_dedup --build-arg VERSION=$V \
#       -t joblens/job-dedup:$V .
#   docker build -f images/batch/Dockerfile --target ml    --build-arg JOB=skill_extractor --build-arg VERSION=0.2.1-$(git rev-parse --short HEAD) \
#       -t joblens/skill-extractor:0.2.1-$(git rev-parse --short HEAD) .
# Chạy (Airflow KubernetesPodOperator truyền đúng các tham số này; biến JOBLENS_* lấy từ Secret của nhóm vận hành):
#   docker run --rm --env-file .env joblens/job-dedup:$V \
#       --input-table silver.job_postings --output-table silver.job_dedup --run-id manual-1 --sources topcv,itviec
#
# Lịch sử kích thước: bản ml lần đầu 11,7 GB vì kéo theo gói CUDA (đã lọc bỏ), còn 3,4 GB. Bản light và stub
# không cài nhóm ml nên không có torch; lớp chạy chép thư viện sang python sạch, không mang theo uv, git và
# cache apt. Kích thước thật của từng bản đo lại khi build (`docker images`), chưa đo sau lần sửa này.

FROM ghcr.io/astral-sh/uv:0.12.0 AS uv

# ---------- thư viện ----------

FROM python:3.12-slim AS deps-light
COPY --from=uv /uv /usr/local/bin/uv
# git: joblens-contracts cài từ git (pyproject, tool.uv.sources)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-default-groups --group lakehouse --no-hashes -o /tmp/req.txt \
 && uv pip install --system --no-cache -r /tmp/req.txt \
 && find /usr/local/lib/python3.12/site-packages -name '__pycache__' -type d -prune -exec rm -rf {} +

FROM deps-light AS deps-ml
# torch bản CPU (uv.lock trỏ bản CUDA cho máy dev có GPU – quá nặng và vô ích trong pod CPU)
ARG TORCH_VERSION=2.11.0
# --no-emit-package torch vẫn để lại các gói CUDA mà torch kéo theo (nvidia-*, triton, cuda-*: ~5 GB) → lọc bỏ
RUN uv export --frozen --only-group ml --no-emit-package torch --no-hashes \
  | grep -v -i -E '^(nvidia|triton|cuda)' > /tmp/ml.txt \
 && uv pip install --system --no-cache torch==${TORCH_VERSION} --index-url https://download.pytorch.org/whl/cpu \
 && uv pip install --system --no-cache -r /tmp/ml.txt \
 # header C++ và test của torch chỉ cần khi biên dịch extension, pod chỉ chạy suy luận
 && rm -rf /usr/local/lib/python3.12/site-packages/torch/include \
           /usr/local/lib/python3.12/site-packages/torch/test \
 && find /usr/local/lib/python3.12/site-packages -name '__pycache__' -type d -prune -exec rm -rf {} +

# ---------- mã nguồn (chép một lần, dùng lại cho mọi bản) ----------

FROM scratch AS src
COPY absa/ absa/
COPY annotation/ annotation/
COPY batch/ batch/
COPY common/ common/
COPY crawler/ crawler/
COPY experiments/ experiments/
COPY ie/ ie/
COPY service/ service/

# ---------- lớp chạy: python sạch, chỉ mang thư viện đã cài (bỏ uv, git, cache apt) ----------

FROM python:3.12-slim AS app-light
COPY --from=deps-light /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
WORKDIR /app
COPY --from=src / /app/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

FROM python:3.12-slim AS app-ml
COPY --from=deps-ml /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
WORKDIR /app
COPY --from=src / /app/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# ---------- ba bản giao cho nhóm vận hành ----------

FROM app-light AS stub
ARG JOB
ARG VERSION
ENV JOBLENS_JOB=batch.${JOB} JOBLENS_IMAGE_VERSION=${VERSION} JOBLENS_STUB=1
USER nobody
ENTRYPOINT ["sh", "-c", "exec python -m \"$JOBLENS_JOB\" \"$@\"", "--"]

# job-dedup và absa-scorer bản thật: không torch, không model
FROM app-light AS light
ARG JOB
ARG VERSION
COPY data/annotation/absa_trial.absa.jsonl data/annotation/absa_dev2.absa.jsonl data/annotation/
COPY data/absa/sentences.jsonl data/absa/
ENV JOBLENS_JOB=batch.${JOB} JOBLENS_IMAGE_VERSION=${VERSION} JOBLENS_STUB=0
USER nobody
ENTRYPOINT ["sh", "-c", "exec python -m \"$JOBLENS_JOB\" \"$@\"", "--"]

# skill-extractor bản thật: PhoBERT
FROM app-ml AS ml
ARG JOB
ARG VERSION
COPY data/models/skill-extractor/ data/models/skill-extractor/
ENV JOBLENS_JOB=batch.${JOB} JOBLENS_IMAGE_VERSION=${VERSION} JOBLENS_STUB=0 HF_HOME=/tmp/hf
USER nobody
ENTRYPOINT ["sh", "-c", "exec python -m \"$JOBLENS_JOB\" \"$@\"", "--"]
