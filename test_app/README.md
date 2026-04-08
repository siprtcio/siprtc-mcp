# Siprtc MCP Test App (LangChain)

This is a small test agent that connects to the `siprtc-mcp` server over HTTP (Streamable HTTP transport) and calls a tool.

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

## Notes

- The MCP server is launched by the script using the `siprtc-mcp` command via stdio transport.
- If you prefer a different model, change the model string in `test_app/run_agent.py`.
