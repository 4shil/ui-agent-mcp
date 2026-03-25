# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE} AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODELS_DIR=/app/models \
    HF_HOME=/app/models/.hf-cache \
    TRANSFORMERS_CACHE=/app/models/.hf-cache \
    ENABLE_REST_API=1 \
    REST_API_PORT=8080

# Install runtime libs needed by torch/transformers/PIL and GUI automation packages.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       curl \
       git \
    python3 \
    python3-pip \
       libglib2.0-0 \
       libsm6 \
       libxext6 \
       libxrender1 \
       libx11-6 \
       libxtst6 \
       libxrandr2 \
       libxinerama1 \
       libxi6 \
     && if ! command -v python >/dev/null 2>&1; then ln -sf /usr/bin/python3 /usr/local/bin/python; fi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-tui.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt -r requirements-tui.txt

COPY . .

RUN chmod +x /app/docker-entrypoint.sh

# Optional REST API endpoint.
EXPOSE 8080

ENTRYPOINT ["/app/docker-entrypoint.sh"]
