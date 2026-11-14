# syntax=docker/dockerfile:1.7
# Install the locked, hash-checked dependencies and the server's wheel into a virtualenv in one
# stage; copy only that virtualenv into a clean slim image in the next.
#
# The base image is pinned by digest (python:3.13-slim, multi-arch index) and the dependencies
# by hash (requirements.txt, requirements-build.txt). Dependabot proposes updates to the
# digest and the pins; regenerate the hashes as the README describes.
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
COPY requirements.txt requirements-build.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --require-hashes --no-deps -r requirements.txt \
    && pip install --require-hashes --no-deps -r requirements-build.txt
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY siprtc_mcp ./siprtc_mcp
RUN python -m build --wheel --no-isolation --outdir /dist \
    && /opt/venv/bin/pip install --no-deps /dist/*.whl

FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_PATH=/mcp
COPY --from=build /opt/venv /opt/venv
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin siprtc
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"MCP_PORT\",\"8000\")}/healthz', timeout=4)" || exit 1
ENTRYPOINT ["siprtc-mcp"]
