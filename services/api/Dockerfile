FROM python:3.13-slim-bookworm AS build

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Dependencies first, so editing the source does not re-resolve the whole lock file.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-default-groups --group api --no-install-project

COPY src ./src
RUN uv sync --frozen --no-default-groups --group api

FROM python:3.13-slim-bookworm

COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/src /app/src

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN useradd --uid 10001 --no-create-home app
USER app

EXPOSE 8000

# No curl in a slim image, and adding one for this would be a strange trade.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]

CMD ["uvicorn", "payments.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
