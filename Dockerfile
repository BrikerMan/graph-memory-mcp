FROM ubuntu:24.04

ARG VERSION=latest

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHON_VERSION=3.12 \
    PYTHONPATH=/code/ \
    PYTHONIOENCODING=utf-8 \
    TERM=xterm-256color \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_INSTALL=1 \
    COLUMNS=120 \
    LINES=50 \
    MEMORY_FOLDER=/data

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# create and switch to the working directory
WORKDIR /code

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create Python virtual environment and install dependencies
# We cache dependencies installation to speed up builds
RUN UV_NO_INSTALL=0 uv sync --no-cache

# Copy application code
COPY ./src /code/src

## Healthcheck configuration
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

## Use start script
CMD fastapi run src/main.py
