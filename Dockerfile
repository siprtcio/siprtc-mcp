# syntax=docker/dockerfile:1.7
# Build a wheel in one stage, install it into a clean slim image in the next.
FROM python:3.13-slim AS build
WORKDIR /src
RUN pip install --no-cache-dir build==1.3.0
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY siprtc_mcp ./siprtc_mcp
RUN python -m build --wheel --outdir /dist

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_PATH=/mcp
COPY --from=build /dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm -f /tmp/*.whl \
    && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin siprtc
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"MCP_PORT\",\"8000\")}/healthz', timeout=4)" || exit 1
ENTRYPOINT ["siprtc-mcp"]
