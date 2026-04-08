FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build deps for editable installs (if needed)
RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md /app/
COPY siprtc_mcp /app/siprtc_mcp

RUN pip install --no-cache-dir -e .

# Default: run MCP server
CMD ["siprtc-mcp"]
