# syntax=docker/dockerfile:1.7
# ----------------------------------------------------------------------
# Lateralus compiler container image
# Tags: ghcr.io/bad-antics/lateralus-lang:{latest,3.2.0,3.2,3}
# Use:
#   docker run --rm -v "$PWD:/src" -w /src ghcr.io/bad-antics/lateralus-lang:latest \
#       lateralus run hello.ltl
# ----------------------------------------------------------------------
ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md LICENSE ./
COPY lateralus_lang/ ./lateralus_lang/
COPY stdlib/ ./stdlib/
COPY std/ ./std/
RUN pip install --no-cache-dir build && python -m build --wheel

FROM python:${PYTHON_VERSION}-slim AS runtime
LABEL org.opencontainers.image.title="Lateralus"
LABEL org.opencontainers.image.description="Lateralus pipeline-native programming language compiler & runtime"
LABEL org.opencontainers.image.source="https://github.com/bad-antics/lateralus-lang"
LABEL org.opencontainers.image.url="https://lateralus.dev"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.authors="bad-antics"

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

WORKDIR /src
ENTRYPOINT ["lateralus"]
CMD ["--help"]
