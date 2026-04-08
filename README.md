# Siprtc MCP Server

Production-grade MCP server for Siprtc CPaaS APIs. It uses HTTP Basic Auth with your Siprtc `auth_id` and `auth_secret`.

## Quick start (stdio)

```bash
python -m pip install -e .
export SIPRTC_AUTH_ID="your_auth_id"
export SIPRTC_AUTH_SECRET="your_auth_secret"
python -m siprtc_mcp
```

## Run over HTTP (Streamable HTTP)

```bash
export MCP_TRANSPORT="http"
export MCP_HOST="0.0.0.0"
export MCP_PORT="8000"
export MCP_PATH="/mcp"
python -m siprtc_mcp
```

## Auth

Credentials are resolved in this order:

1. Per-tool arguments `auth_id` and `auth_secret`
2. Session credentials set via `siprtc.set_credentials`
3. Environment variables `SIPRTC_AUTH_ID` and `SIPRTC_AUTH_SECRET`

## Configurable endpoints

This server ships with default paths based on the Swagger you provided. If your Siprtc deployment uses different paths, you can override them via environment variables.

- `SIPRTC_PHONE_NUMBERS_LIST_PATH`
- `SIPRTC_PHONE_NUMBERS_GET_PATH`
- `SIPRTC_PHONE_NUMBERS_BUY_PATH`
- `SIPRTC_PHONE_NUMBERS_RELEASE_PATH`
- `SIPRTC_PHONE_NUMBERS_AVAILABLE_PATH`
- `SIPRTC_PHONE_NUMBERS_ASSOCIATE_PATH`
- `SIPRTC_SIP_USERS_PATH`
- `SIPRTC_SIP_USER_PATH`
- `SIPRTC_DOMAINS_PATH`
- `SIPRTC_DOMAIN_PATH`
- `SIPRTC_APPLICATIONS_PATH`
- `SIPRTC_APPLICATION_PATH`

All paths are relative to the base URL (default: `https://api.siprtc.io/v1`) and can include `{auth_id}` and other placeholders.

## Docker

```bash
docker build -t siprtc-mcp:latest .
docker run --rm \\
  -e SIPRTC_AUTH_ID=your_auth_id \\
  -e SIPRTC_AUTH_SECRET=your_auth_secret \\
  -e MCP_TRANSPORT=http \\
  -e MCP_HOST=0.0.0.0 \\
  -e MCP_PORT=8000 \\
  -e MCP_PATH=/mcp \\
  -p 8000:8000 \\
  siprtc-mcp:latest
```

## Docker Compose (MCP + test app)

If you have a `test_app/.env` with `SIPRTC_AUTH_ID`, `SIPRTC_AUTH_SECRET`, and `OPENAI_API_KEY`:

```bash
docker compose up --build
```

## Run

```bash
siprtc-mcp
```
