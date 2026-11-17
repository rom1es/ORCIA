# Multi-role Python 3.12 non-root image for ORCIA (OpenShift SCC `restricted` ready).
FROM python:3.12-slim AS runtime

ARG WORKER_EXTRA=""

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY packages/ ./packages/
COPY apps/ ./apps/
COPY infra/sandbox/ ./infra/sandbox/
COPY scripts/ ./scripts/

RUN uv sync --no-dev \
    && if [ -n "$WORKER_EXTRA" ]; then uv pip install --python /app/.venv/bin/python --no-cache "$WORKER_EXTRA"; fi \
    && chgrp -R 0 /app \
    && chmod -R g=u /app \
    && mkdir -p /tmp \
    && chmod 1777 /tmp

ENV HOME=/tmp \
    TMPDIR=/tmp \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:0

EXPOSE 8000

CMD ["uvicorn", "orcia_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
