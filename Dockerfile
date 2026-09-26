# Shared multi-stage image for all Luna Python services.
# Build context is the repository root so the shared library is available.
#
#   docker build --build-arg SERVICE=search-api --build-arg PORT=8001 -t luna/search-api .
#
FROM python:3.13-slim AS base

ARG SERVICE
ARG PORT=8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/shared/python

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install the shared library first (best layer caching).
COPY shared/python /app/shared/python
RUN pip install /app/shared/python psycopg2-binary

# Install the selected service.
COPY services/${SERVICE} /app/service
RUN pip install /app/service

# Migration tooling (used by the migrate gate; harmless for other services).
COPY migrations /app/migrations
COPY scripts /app/scripts

# Make the service package importable at runtime.
ENV PYTHONPATH=/app/shared/python:/app/service/src

EXPOSE ${PORT}

# The concrete run command is provided per-service in docker-compose.
CMD ["python", "-c", "print('override CMD in compose')"]
