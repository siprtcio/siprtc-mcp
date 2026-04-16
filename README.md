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

1. HTTP bearer token for the current request
2. Environment variables `SIPRTC_AUTH_ID` and `SIPRTC_AUTH_SECRET`

For HTTP transport, the bearer token must be the URL-safe base64 encoding of `auth_id:auth_secret`.

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

If you have a `test_app/.env` with `SIPRTC_AUTH_ID`, `SIPRTC_AUTH_SECRET`, and `OPENAI_API_KEY`, you can run the MCP server and the Chainlit UI together:

```bash
docker compose up --build -d
```

The UI is available at:

- `http://localhost:8501` (Chainlit UI)
<img width="1464" height="740" alt="Screenshot 2026-04-08 at 8 50 50 AM" src="https://github.com/user-attachments/assets/f8561a54-3c5d-4ce0-a400-b775c7e74a6b" />
- `http://localhost:8000/mcp` (MCP HTTP endpoint)

Note: The Chainlit UI does not prompt for API keys. It uses backend environment variables.

## Test App (CLI)

You can run the test app directly inside the container:

```bash
docker compose run --rm test-app python -m test_app.run_agent
```

## Run MCP Server

```bash
siprtc-mcp
```
