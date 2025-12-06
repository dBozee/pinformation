#build stage
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder
COPY . /app
WORKDIR /app
ENV UV_LINK_MODE=copy

#install gcc for aiohttp
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN uv venv && uv sync

#runtime stage
FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY . .
CMD ["python", "-m", "pinformation_bot"]