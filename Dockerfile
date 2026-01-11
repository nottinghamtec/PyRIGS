# Stage 1: Base build stage
FROM combos/python_node:3.10_22 AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
FROM base AS builder

# Set up environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Create non-root user
RUN addgroup --system app && adduser --system --group app

WORKDIR /app

# Copy uv project files first (for better caching)
COPY pyproject.toml uv.lock ./

WORKDIR /app

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --all-groups

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-groups

FROM base
COPY --from=builder /app /app
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "PyRIGS.wsgi"]
