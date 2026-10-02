# syntax=docker/dockerfile:1
#
# Targets:
#   prod (default, last stage)  gunicorn image with assets and static files baked in
#   dev                          dependencies only; the source is bind-mounted by compose.override.yml
#
# Stages are ordered so that editing application code only invalidates the cheap final layers:
# apt packages, Python dependencies and node modules are all cached separately.

# ---- Frontend assets (multi-arch: official node image) ----
FROM node:24-slim AS assets
WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY gulpfile.js ./
COPY pipeline/source_assets ./pipeline/source_assets
RUN npm run build


# ---- Shared Python base: runtime system libraries only ----
FROM python:3.14-slim-trixie AS python-base

# Keep downloaded packages between builds (the default Docker config for Debian images deletes them)
RUN rm -f /etc/apt/apt.conf.d/docker-clean \
    && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends libcairo2

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"


# ---- Python dependencies (only rebuilt when pyproject.toml / uv.lock change) ----
FROM python-base AS deps-base
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /uvx /bin/

# pycairo (via z3c.rml) has no wheels and is compiled against cairo
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config libcairo2-dev

WORKDIR /app

FROM deps-base AS deps-prod
ENV UV_COMPILE_BYTECODE=1
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

FROM deps-base AS deps-dev
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project


# ---- Development: dependencies only, source and static assets are mounted at runtime ----
FROM python-base AS dev
COPY --from=deps-dev /opt/venv /opt/venv
WORKDIR /app
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


# ---- Static files: depends on the source, so this is the first stage that reruns on a code change ----
FROM python-base AS static
COPY --from=deps-prod /opt/venv /opt/venv
WORKDIR /app
COPY . /app
COPY --from=assets /app/pipeline/built_assets /app/pipeline/built_assets
# Placeholder values only satisfy settings that are mandatory when DEBUG is off; they are not kept in the image
RUN DEBUG=false EMAIL_HOST=build EMAIL_HOST_USER=build EMAIL_HOST_PASSWORD=build EMAIL_FROM=build@example.com \
    python manage.py collectstatic --noinput


# ---- Production image ----
FROM python-base AS prod
RUN addgroup --system app \
    && adduser --system --group --home /home/app app

COPY --from=deps-prod /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app . /app
COPY --from=static --chown=app:app /app/static /app/static
COPY --from=assets --chown=app:app /app/pipeline/built_assets /app/pipeline/built_assets

# DEBUG must never be on in a built image; enable it explicitly via the environment if needed
ENV DEBUG=false

USER app
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "PyRIGS.wsgi"]
