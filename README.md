# SIPRTC MCP Server

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the
[SIPRTC](https://siprtc.io) CPaaS API as tools an LLM agent can call. Your agent decides to
place a call or send a message; this server makes the API request against your own SIPRTC
account.

It authenticates with HTTP Basic Auth using your SIPRTC `auth_id` and `auth_secret`, and
speaks both stdio and Streamable HTTP.

- **API reference:** https://siprtc.io/docs/
- **About this server:** https://siprtc.io/mcp/

> **Status: v0.1.0, first release.** The tool surface will change. If a call you need is
> missing, open an issue describing what you were trying to do.

## Quick start

### stdio — local clients

For Claude Desktop, Claude Code, or anything that launches the server as a subprocess.

```bash
python -m pip install -e .

export SIPRTC_AUTH_ID="your_auth_id"
export SIPRTC_AUTH_SECRET="your_auth_secret"

python -m siprtc_mcp
```

The installed console script `siprtc-mcp` is equivalent to `python -m siprtc_mcp`.

### Streamable HTTP — hosted agents

Run it once and point a fleet of agents at the endpoint.

```bash
export MCP_TRANSPORT="http"
export MCP_HOST="0.0.0.0"
export MCP_PORT="8000"
export MCP_PATH="/mcp"

python -m siprtc_mcp
```

## Connecting a client

### Claude Desktop

Add this to `claude_desktop_config.json` — on macOS at
`~/Library/Application Support/Claude/claude_desktop_config.json`, on Windows at
`%APPDATA%\Claude\claude_desktop_config.json` — then restart Claude Desktop.

```json
{
  "mcpServers": {
    "siprtc": {
      "command": "python",
      "args": ["-m", "siprtc_mcp"],
      "env": {
        "SIPRTC_AUTH_ID": "your_auth_id",
        "SIPRTC_AUTH_SECRET": "your_auth_secret"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add siprtc \
  --env SIPRTC_AUTH_ID=your_auth_id \
  --env SIPRTC_AUTH_SECRET=your_auth_secret \
  -- python -m siprtc_mcp
```

### Any HTTP client

Point it at `http://your-host:8000/mcp` and send the bearer token described under
[Authentication](#authentication).

## Tools

23 tools, all namespaced `siprtc.`. That prefix is part of the name the model calls.

### Voice

| Tool | Does |
| --- | --- |
| `siprtc.make_call` | Place an outbound call. Returns `request_id` and status. |
| `siprtc.get_call` | Fetch a call detail record (CDR) by call SID. |
| `siprtc.hangup_call` | Hang up an in-progress call by call SID. |

### Messaging

| Tool | Does |
| --- | --- |
| `siprtc.send_sms` | Send an outbound SMS. Supports status callbacks. |

### Phone numbers

| Tool | Does |
| --- | --- |
| `siprtc.list_phone_numbers` | List numbers on the account. |
| `siprtc.list_available_phone_numbers` | Search numbers available to buy. |
| `siprtc.buy_phone_number` | Purchase a number. |
| `siprtc.get_phone_number` | Fetch one number by ID. |
| `siprtc.associate_application_to_phone_number` | Attach an application to a number. |
| `siprtc.release_phone_number` | Release a number from the account. |

### SIP users

| Tool | Does |
| --- | --- |
| `siprtc.list_sip_users` | List SIP users / endpoints. |
| `siprtc.create_sip_user` | Create a SIP user. |
| `siprtc.update_sip_user` | ⚠️ **Deletes** a SIP user — see the note below. |
| `siprtc.associate_sip_user_application` | Associate or de-associate an application. |

> ⚠️ **`siprtc.update_sip_user` deletes the endpoint.** It is named for the HTTP verb
> (SIPRTC uses `PUT` to delete this resource) rather than for its effect. A model choosing
> tools by name will read it as "modify a SIP user" and destroy one instead. Treat the name
> as misleading until it is corrected; there is no separate delete tool.

### Domains

| Tool | Does |
| --- | --- |
| `siprtc.list_domains` | List domains. |
| `siprtc.create_domain` | Create a domain. |
| `siprtc.get_domain` | Fetch one domain. |
| `siprtc.update_domain` | Update a domain. |
| `siprtc.delete_domain` | Delete a domain. |

### Applications

| Tool | Does |
| --- | --- |
| `siprtc.list_applications` | List applications. |
| `siprtc.create_application` | Create an application. |
| `siprtc.update_application` | Update an application. |
| `siprtc.delete_application` | Delete an application. |

## Authentication

Credentials are resolved in this order:

1. **Bearer token on the current HTTP request.** The token is the URL-safe base64 encoding
   of `auth_id:auth_secret`. Checked first, so one running server can act for whichever
   account made the request.
2. **Environment variables** `SIPRTC_AUTH_ID` and `SIPRTC_AUTH_SECRET`. The usual choice for
   stdio, where the server belongs to one user.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `SIPRTC_AUTH_ID` | — | Account auth ID |
| `SIPRTC_AUTH_SECRET` | — | Account auth secret |
| `SIPRTC_BASE_URL` | `https://api.siprtc.io/v1` | API base. Point this at a private or on-premise deployment. |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `MCP_HOST` | `127.0.0.1` | Bind address, HTTP transport only |
| `MCP_PORT` | `8000` | Port, HTTP transport only |
| `MCP_PATH` | `/mcp` | Endpoint path, HTTP transport only |

### Endpoint overrides

Default paths follow the public SIPRTC API. If your deployment uses different routes, each
can be overridden without a code change. Paths are relative to `SIPRTC_BASE_URL` and may
contain `{auth_id}` and other placeholders.

`SIPRTC_PHONE_NUMBERS_LIST_PATH` · `SIPRTC_PHONE_NUMBERS_GET_PATH` ·
`SIPRTC_PHONE_NUMBERS_BUY_PATH` · `SIPRTC_PHONE_NUMBERS_RELEASE_PATH` ·
`SIPRTC_PHONE_NUMBERS_AVAILABLE_PATH` · `SIPRTC_PHONE_NUMBERS_ASSOCIATE_PATH` ·
`SIPRTC_SIP_USERS_PATH` · `SIPRTC_SIP_USER_PATH` · `SIPRTC_DOMAINS_PATH` ·
`SIPRTC_DOMAIN_PATH` · `SIPRTC_APPLICATIONS_PATH` · `SIPRTC_APPLICATION_PATH`

## Docker

```bash
docker build -t siprtc-mcp:latest .

docker run --rm -p 8000:8000 \
  -e SIPRTC_AUTH_ID=your_auth_id \
  -e SIPRTC_AUTH_SECRET=your_auth_secret \
  -e MCP_TRANSPORT=http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e MCP_PATH=/mcp \
  siprtc-mcp:latest
```

### Compose — server plus test UI

With a `test_app/.env` containing `SIPRTC_AUTH_ID`, `SIPRTC_AUTH_SECRET` and
`OPENAI_API_KEY`:

```bash
docker compose up --build -d
```

- Chainlit UI: `http://localhost:8501`
- MCP endpoint: `http://localhost:8000/mcp`

The UI does not prompt for keys; it reads them from the backend environment.

<img width="1464" alt="Chainlit test UI calling SIPRTC tools" src="https://github.com/user-attachments/assets/f8561a54-3c5d-4ce0-a400-b775c7e74a6b" />

Run the CLI test app inside the container:

```bash
docker compose run --rm test-app python -m test_app.run_agent
```

## Billing

The server is free. Calls and messages it places are billed on your SIPRTC account at your
existing rates — an agent in a retry loop spends real money, so scope its credentials
accordingly.

## Contributing

Issues and pull requests are welcome. The most useful issue describes the call you were
trying to make and what the agent did instead.

## Licence

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
