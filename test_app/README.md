# Siprtc MCP Test App (Chainlit UI)

This is a small test agent using Deep Agents that connects to the `siprtc-mcp` server over HTTP (Streamable HTTP transport). It includes a Chainlit UI branded for Siprtc so you can test it from a browser.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r test_app/requirements.txt
pip install -e .
```

## Environment

Set the following environment variables (or put them in a `.env` file inside `test_app/`):

- `SIPRTC_AUTH_ID`
- `SIPRTC_AUTH_SECRET`
- `OPENAI_API_KEY`

Example `.env`:

```env
SIPRTC_AUTH_ID=your_auth_id
SIPRTC_AUTH_SECRET=your_auth_secret
OPENAI_API_KEY=your_openai_key
```

## Run

```bash
export MCP_SERVER_URL="http://localhost:8000/mcp"
python test_app/run_agent.py
```

## Chainlit UI

```bash
chainlit run test_app/chainlit_app.py --host 0.0.0.0 --port 8501
```

## Deep Agents

The agent is created via `deepagents.create_deep_agent` and uses a single tool `siprtc_tool` that forwards calls to the MCP server.
```

## Notes

- If you prefer a different model, change `DEEP_AGENT_MODEL`.
- The Chainlit UI welcomes users with Siprtc branding.
