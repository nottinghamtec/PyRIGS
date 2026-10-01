# Stage 1: build frontend assets (multi-arch: official node image)
FROM node:24-slim AS assets
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY gulpfile.js ./
COPY pipeline/source_assets ./pipeline/source_assets
RUN npm run build

# Stage 2: build the Python environment (multi-arch: official python image)
FROM python:3.14-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /uvx /bin/

# pycairo (via z3c.rml) has no wheels and is compiled against cairo
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set up py environment
# DEBUG must never be on in a built image; enable it explicitly via the environment if needed
ENV DEBUG=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy uv project files first (for better caching)
COPY pyproject.toml uv.lock ./

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
COPY --from=assets /app/pipeline/built_assets /app/pipeline/built_assets
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Placeholder values only satisfy settings that are mandatory when DEBUG is off; they are not kept in the image
RUN EMAIL_HOST=build EMAIL_HOST_USER=build EMAIL_HOST_PASSWORD=build EMAIL_FROM=build@example.com \
    uv run python manage.py collectstatic --noinput

FROM python:3.14-slim-trixie
RUN apt-get update \
    && apt-get install -y --no-install-recommends libcairo2 \
    && rm -rf /var/lib/apt/lists/*
RUN addgroup --system app \
    && adduser --system --group --home /home/app app \
    && mkdir -p /home/app \
    && chown app:app /home/app
COPY --from=builder --chown=app:app /app /app
WORKDIR /app
ENV DEBUG=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

USER app
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "PyRIGS.wsgi"]
