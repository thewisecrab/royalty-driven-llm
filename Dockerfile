FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RDLLM_SERVICE_CONFIG=/app/deploy/docker/service_config.container.json

WORKDIR /app

RUN groupadd --system rdllm \
    && useradd --system --gid rdllm --home-dir /app --shell /usr/sbin/nologin rdllm

COPY pyproject.toml README.md LICENSE MANIFEST.in ./
COPY src ./src
COPY examples ./examples
COPY artifacts ./artifacts
COPY docs ./docs
COPY deploy ./deploy

RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir . \
    && mkdir -p /var/lib/rdllm/audit \
    && chown -R rdllm:rdllm /app /var/lib/rdllm

USER rdllm

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import json,urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8765/readyz', timeout=3); raise SystemExit(0 if json.load(r).get('status') == 'ready' else 1)"

CMD ["sh", "-c", "rdllm-service --config ${RDLLM_SERVICE_CONFIG} --host 0.0.0.0 --port 8765"]
