# Image of the Compose service `web`: the FastAPI app (app/web.py) and the built SPA.
# Build context: the repository root (see deploy/compose.yaml).

FROM node:24-slim AS frontend
WORKDIR /frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.14-slim AS web
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --frozen --no-dev
COPY --from=frontend /frontend/build /app/frontend-build
RUN useradd --system --no-create-home atrade
USER atrade
# The root file system is read-only at run time. Only /tmp is writable.
ENV PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
EXPOSE 8000
CMD ["python", "-m", "atrade.app.web"]
