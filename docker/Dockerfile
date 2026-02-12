FROM python:3.11-slim-bullseye AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

FROM python:3.11-slim-bullseye AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY backend /app/backend
COPY docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint

RUN mkdir -p staticfiles media logs

EXPOSE 8010

ENTRYPOINT ["/usr/local/bin/backend-entrypoint"]
CMD ["gunicorn", "--chdir", "/app/backend", "config.wsgi:application", "--bind", "0.0.0.0:8010"]
