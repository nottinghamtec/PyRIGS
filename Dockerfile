# Stage 1: Base build stage
FROM combos/python_node:3.12_22 AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
FROM base AS builder

WORKDIR /app

# Set up node environment
COPY package.json package-lock.json ./
RUN npm ci

COPY gulpfile.js ./
COPY pipeline/source_assets ./pipeline/source_assets

RUN npm run build \
    && rm -rf node_modules

# Set up py environment
ENV PYTHONDONTWRITEBYTECODE=1 \
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
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN uv run python manage.py collectstatic --noinput

FROM python:3.12-slim-trixie
RUN addgroup --system app \
    && adduser --system --group --home /home/app app \
    && mkdir -p /home/app \
    && chown app:app /home/app
COPY --from=builder --chown=app:app /app /app
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

USER app
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "PyRIGS.wsgi"]