# SIPRTC MCP Server

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the
[SIPRTC](https://siprtc.io) CPaaS API as tools an LLM agent can call. Your agent decides to
place a call, send a message or route a contact-centre task; this server makes the API
request against your own SIPRTC account.

It authenticates with HTTP Basic Auth using your SIPRTC `auth_id` and `auth_secret`, and
speaks both stdio and Streamable HTTP.

- **API reference:** https://siprtc.io/docs/
- **About this server:** https://siprtc.io/mcp/

> **Status: v0.2.0.** Covers every API that accepts an account's Auth ID and secret:
> voice, conferences, recordings and privacy controls, messaging and channels, fax and email,
> numbers, SIP, carrier trunks, applications, the account, TaskRouter, campaigns, reports,
> flows, AI agents and workforce scheduling. If a call you need is missing, open an issue
> describing what you were trying to do.

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

Run it once and point a fleet of agents at the endpoint. Each request carries its own
account's credentials as a bearer token (see [Authentication](#authentication)).

```bash
export MCP_TRANSPORT="http"
export MCP_HOST="0.0.0.0"
export MCP_PORT="8000"
export MCP_PATH="/mcp"

python -m siprtc_mcp
```

`GET /healthz` answers `{"status": "ok", ...}` for load balancers and orchestrators.

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
        "SIPRTC_AUTH_SECRET": "your_auth_secret",
        "SIPRTC_TOOLSETS": "voice,messaging,phone_numbers"
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

## Safety controls

The server acts on a real account. Calls, messages, number purchases and campaigns cost
money and reach real people, so it gives you several ways to narrow what a model can do:

- **Tool annotations.** Every tool carries the MCP hints `readOnlyHint`, `destructiveHint`
  and `idempotentHint`. Clients that honour them (Claude does) ask before running a
  destructive tool. Tools that are billed or contact people say so in their description.
- **Read-only mode.** `SIPRTC_READ_ONLY=true` registers only the tools that read. Nothing
  can be created, changed, sent or deleted.
- **Toolsets.** `SIPRTC_TOOLSETS=voice,messaging` loads only those groups. Fewer tools also
  means a model picks the right one more often. The groups are listed in the
  [tool reference](#tools).
- **No arbitrary paths.** Tools build their own API paths; a model cannot point a tool at
  another endpoint. Path values are URL-encoded and kept to one path segment.
- **Secrets stay out of the conversation.** Responses are scrubbed of fields such as
  `auth_secret`, `password`, `auth_token`, `access_token`, `api_secret` before the model sees
  them, and error messages are scrubbed the same way. The API secret itself is never
  returned; `siprtc.get_api_credentials` shows only a hint.
- **Scoped credentials.** Prefer a sub-account or a dedicated test account for agents, so a
  retry loop cannot spend more than that account holds.

## Tools

All tools are namespaced `siprtc.`; that prefix is part of the name the model calls.
This reference is generated from the server (`python scripts/tool_reference.py`).

<!-- tools:start -->

189 tools in 17 toolsets. ✏️ changes something, ⚠️ deletes or ends something, 💲 is billed or reaches people.

### Voice calls — `voice`

| Tool | Does |
| --- | --- |
| `siprtc.make_call` ✏️ 💲 | Place an outbound voice call (billed). |
| `siprtc.list_calls`  | List call detail records (CDRs). |
| `siprtc.get_call`  | Fetch one call detail record (CDR) by call SID. |
| `siprtc.update_call` ✏️ | Change a live call: redirect it to new TinyML (url or tinyml), end it with status='completed', or put it on hold / take it off hold. |
| `siprtc.hangup_call` ⚠️ | Hang up a ringing or in-progress call by call SID. |
| `siprtc.start_call_recording` ✏️ | Start recording a live call. |
| `siprtc.update_call_recording` ✏️ | Pause, resume (status in-progress) or stop a recording on a live call. |

### Conferences — `conferences`

| Tool | Does |
| --- | --- |
| `siprtc.list_conferences`  | List conferences, optionally by status (init, in-progress, completed) or friendly name. |
| `siprtc.get_conference`  | Fetch one conference by SID. |
| `siprtc.update_conference` ✏️ | Update a conference. |
| `siprtc.list_conference_participants`  | List the participants of a conference. |
| `siprtc.get_conference_participant`  | Fetch one conference participant by call SID. |
| `siprtc.update_conference_participant` ✏️ | Mute/unmute, hold/unhold a participant, or play an announcement to them. |
| `siprtc.remove_conference_participant` ⚠️ | Remove a participant from a conference, hanging up their leg. |

### Recordings, transcripts and privacy — `recordings`

| Tool | Does |
| --- | --- |
| `siprtc.list_recordings`  | List call recordings, optionally for one call or conference. |
| `siprtc.get_recording`  | Fetch a recording's metadata. |
| `siprtc.delete_recording` ⚠️ | Permanently delete a recording's audio (a tombstone record stays). |
| `siprtc.get_recording_settings`  | Show the account's recording, transcript-storage, encryption, retention and playback-access settings. |
| `siprtc.update_recording_settings` ✏️ | Change recording settings. |
| `siprtc.list_transcripts`  | List stored conversation transcripts (voice, webchat, whatsapp, ...). |
| `siprtc.get_transcript`  | Fetch a transcript's metadata, or with include_content=true its text (needs playback rights; audited). |
| `siprtc.delete_transcript` ⚠️ | Permanently delete a transcript. |
| `siprtc.list_public_keys`  | List the RSA public keys registered for customer-key recording encryption. |
| `siprtc.create_public_key` ✏️ | Register an RSA public key (PEM 'PUBLIC KEY', 2048-4096 bit) for customer-key recording encryption. |
| `siprtc.get_public_key`  | Fetch one registered public key by SID (CR...). |
| `siprtc.update_public_key` ✏️ | Rename a registered public key (the key itself cannot change). |
| `siprtc.delete_public_key` ⚠️ | Delete a registered public key. |
| `siprtc.list_legal_holds`  | List legal holds, optionally only active or released ones. |
| `siprtc.create_legal_hold` ✏️ | Put recordings/transcripts on legal hold so retention and deletes skip them. |
| `siprtc.get_legal_hold`  | Fetch one legal hold by SID (LH...). |
| `siprtc.release_legal_hold` ⚠️ | Release a legal hold (its scope cannot change). |
| `siprtc.list_audit_events`  | List privacy audit events (e.g. |

### Messaging — `messaging`

| Tool | Does |
| --- | --- |
| `siprtc.send_sms` ✏️ 💲 | Send an outbound SMS (billed). |
| `siprtc.send_message` ✏️ 💲 | Send an outbound message on sms, whatsapp, facebook or viber (billed). |
| `siprtc.list_messages`  | List message detail records (SMS, WhatsApp, ...), newest first. |
| `siprtc.get_message`  | Fetch one message record by its sid, including status and error code. |
| `siprtc.list_conversations`  | Search the conversation history across channels (sms, whatsapp, webchat, email, ...): filter by conversation_id, contact, to/from, channel, direction or dates (yyyy-mm-dd). |
| `siprtc.get_conversation_transcript`  | Return one conversation as a plain-text transcript. |

### Messaging channels and Meta — `channels`

| Tool | Does |
| --- | --- |
| `siprtc.list_channel_connections`  | List connected messaging channels (sms providers, whatsapp, viber), optionally for one channel. |
| `siprtc.get_channel_connection`  | Fetch one channel connection by id. |
| `siprtc.connect_channel` ✏️ | Connect a messaging channel with your own provider credentials. |
| `siprtc.update_channel_connection` ✏️ | Rename a channel connection, point it at another application, or change its countries. |
| `siprtc.update_channel_credentials` ✏️ | Replace a channel connection's provider credentials (same keys as connect_channel). |
| `siprtc.verify_channel_connection` ✏️ | Check a channel connection's credentials against the provider and report the result. |
| `siprtc.disconnect_channel` ⚠️ | Disconnect (delete) a channel connection. |
| `siprtc.get_meta_integration`  | Show the account's Facebook/Meta integration and its connected pages (404 when none is connected). |
| `siprtc.send_messenger_message` ✏️ 💲 | Send a Facebook Messenger message from a connected page to a user (recipient_id is their page-scoped id). |

### Fax and email — `fax_email`

| Tool | Does |
| --- | --- |
| `siprtc.list_faxes`  | List sent faxes, optionally filtered by to, from, status or title. |
| `siprtc.list_received_faxes`  | List received (inbound) faxes. |
| `siprtc.send_fax` ✏️ 💲 | Send a fax (billed). |
| `siprtc.delete_fax` ⚠️ | Delete a fax record. |
| `siprtc.list_fax_documents`  | List documents uploaded for faxing. |
| `siprtc.upload_fax_document` ✏️ | Upload a document (PDF, TIFF, ...) to fax later. |
| `siprtc.delete_fax_document` ⚠️ | Delete an uploaded fax document. |
| `siprtc.send_email` ✏️ 💲 | Send an email (HTML body) through the account's configured SMTP sender. |

### Phone numbers — `phone_numbers`

| Tool | Does |
| --- | --- |
| `siprtc.list_phone_numbers`  | List the phone numbers on the account. |
| `siprtc.list_available_phone_numbers`  | Search numbers available to buy. |
| `siprtc.get_phone_number`  | Fetch one number on the account, with its rates, capability and application. |
| `siprtc.buy_phone_number` ✏️ 💲 | Buy a number from the available list (billed: setup plus monthly charge; 402 when the balance is too low). |
| `siprtc.release_phone_number` ⚠️ | Release a number from the account. |
| `siprtc.associate_application_to_phone_number` ✏️ | Attach an application to a number (it then handles the number's inbound calls/messages), or detach it with associate=false. |
| `siprtc.update_phone_number_routing` ✏️ | Set how a number's inbound traffic is routed in the contact centre: an AI agent (ai_enabled + ai_agent), an IVR, or a taskrouter workspace/workflow/task queue. |
| `siprtc.check_caller_id`  | Check whether a number may be used as caller ID (From) on outbound calls. |
| `siprtc.list_verified_phone_numbers`  | List outside numbers verified for use as caller ID (404 when there are none). |
| `siprtc.get_verified_phone_number`  | Fetch one verified caller-ID number. |
| `siprtc.delete_verified_phone_number` ⚠️ | Remove a verified caller-ID number. |

### SIP users and SIP domains — `sip`

| Tool | Does |
| --- | --- |
| `siprtc.list_sip_users`  | List SIP users (endpoints), optionally filtered by name, SIP username or status. |
| `siprtc.list_available_sip_users`  | List SIP users in a taskrouter workspace that are not yet bound to an agent (worker). |
| `siprtc.create_sip_user` ✏️ | Create a SIP user. |
| `siprtc.update_sip_user` ✏️ | Update a SIP user: its name and password (both required by the API), codecs, status or presence. |
| `siprtc.delete_sip_user` ⚠️ | Delete a SIP user. |
| `siprtc.associate_sip_user_application` ✏️ | Attach an application to a SIP user (it handles the user's outbound calls), or detach it with associate=false. |
| `siprtc.list_sip_domains`  | List SIP domains (where PBXs and SIP trunks send calls in). |
| `siprtc.get_sip_domain`  | Fetch one SIP domain by numeric id. |
| `siprtc.create_sip_domain` ✏️ | Create a SIP domain <domain_prefix>.sip.<platform>. |
| `siprtc.update_sip_domain` ✏️ | Update a SIP domain's name, IP or user auth, or status. |
| `siprtc.associate_sip_domain_application` ✏️ | Attach an application to a SIP domain (it handles calls arriving there), or detach it with associate=false. |
| `siprtc.delete_sip_domain` ⚠️ | Delete a SIP domain. |

### Carrier trunks and rates — `trunks`

| Tool | Does |
| --- | --- |
| `siprtc.list_termination_trunks`  | List outbound (termination) carrier trunks. |
| `siprtc.get_termination_trunk`  | Fetch one outbound carrier trunk by id. |
| `siprtc.create_termination_trunk` ✏️ | Add an outbound carrier trunk. |
| `siprtc.update_termination_trunk` ✏️ | Replace an outbound carrier trunk's settings (name, primary_ip and supported_cc are required). |
| `siprtc.delete_termination_trunk` ⚠️ | Delete an outbound carrier trunk. |
| `siprtc.list_origination_trunks`  | List inbound (origination) trunks, and the SIP domain carriers send calls to (auth_domain). |
| `siprtc.get_origination_trunk`  | Fetch one inbound trunk by id. |
| `siprtc.create_origination_trunk` ✏️ | Add an inbound trunk: calls are accepted from the listed cidrs (IP or CIDR), or with a username (letters/digits) and password (8+ chars). |
| `siprtc.update_origination_trunk` ✏️ | Replace an inbound trunk's settings (name is required). |
| `siprtc.delete_origination_trunk` ⚠️ | Delete an inbound trunk; its carrier's calls are refused. |
| `siprtc.list_rates`  | List the outbound voice rates that apply to the account, optionally for one dial prefix. |

### Applications — `applications`

| Tool | Does |
| --- | --- |
| `siprtc.list_applications`  | List applications, optionally filtered by friendly name or status. |
| `siprtc.get_application`  | Fetch one application by SID. |
| `siprtc.create_application` ✏️ | Create an application: the webhooks SIPRTC calls for inbound voice (voice_url returns TinyML) and messages (sms_url). |
| `siprtc.update_application` ✏️ | Update an application. |
| `siprtc.delete_application` ⚠️ | Delete an application. |

### Account — `account`

| Tool | Does |
| --- | --- |
| `siprtc.get_balance`  | Show the account's prepaid balance (USD). |
| `siprtc.get_profile`  | Show the account owner's profile (name, email, phone, address). |
| `siprtc.update_profile` ✏️ | Update the account owner's profile details. |
| `siprtc.get_account_settings`  | Show account settings: theme, language, email domains for fax-to-email, default fax number. |
| `siprtc.get_api_credentials`  | Show the account's API credentials status: the Auth ID and only a hint of each secret, with when it was last rotated. |
| `siprtc.list_client_tokens`  | List client tokens issued for SDK / WebRTC clients. |
| `siprtc.create_client_token` ✏️ | Issue a client token (valid 7 days) for an SDK or WebRTC client. |
| `siprtc.delete_client_token` ⚠️ | Revoke a client token by id. |
| `siprtc.list_sub_accounts`  | List the users under this account (agents, supervisors, members), filterable by name, email, type or status. |
| `siprtc.get_sub_account`  | Fetch one user under this account by Auth ID. |
| `siprtc.create_sub_account` ✏️ | Create a user under this account (e.g. |
| `siprtc.set_sub_account_status` ✏️ | Disable (disabled=true) or re-enable a user under this account. |
| `siprtc.delete_sub_account` ⚠️ | Schedule a user under this account for deletion (removes their sign-in and data). |
| `siprtc.get_customer_balance`  | Vendor accounts only: show a customer account's balance. |
| `siprtc.recharge_customer_balance` ✏️ | Vendor accounts only: add credit to (or, with a negative amount, debit) a customer account's balance. |
| `siprtc.list_inventory_numbers`  | Vendor accounts only: list the vendor's phone number inventory. |
| `siprtc.add_inventory_number` ✏️ | Vendor accounts only: add a number to the inventory customers can buy from. |

### TaskRouter (contact centre routing) — `taskrouter`

| Tool | Does |
| --- | --- |
| `siprtc.list_workspaces`  | List TaskRouter workspaces (one per contact centre). |
| `siprtc.get_workspace`  | Fetch one workspace by sid (WS...). |
| `siprtc.create_workspace` ✏️ | Create a workspace. |
| `siprtc.update_workspace` ✏️ | Update a workspace (friendly_name and status are required by the API). |
| `siprtc.list_activities`  | List the activities (agent states such as Available, Break, Offline) in a workspace. |
| `siprtc.get_activity`  | Fetch one of a workspace's activities (agent states such as Available, Break, Offline) by sid. |
| `siprtc.delete_activity` ⚠️ | Delete one of a workspace's activities (agent states such as Available, Break, Offline) by sid. |
| `siprtc.create_activity` ✏️ | Create an agent activity (state). |
| `siprtc.list_task_queues`  | List the task queues in a workspace. |
| `siprtc.get_task_queue`  | Fetch one of a workspace's task queues by sid. |
| `siprtc.delete_task_queue` ⚠️ | Delete one of a workspace's task queues by sid. |
| `siprtc.create_task_queue` ✏️ | Create a task queue. |
| `siprtc.update_task_queue` ✏️ | Update a task queue (friendly_name, status and waiting_time are required by the API). |
| `siprtc.list_workflows`  | List the workflows (routing rules from tasks to queues) in a workspace. |
| `siprtc.get_workflow`  | Fetch one of a workspace's workflows (routing rules from tasks to queues) by sid. |
| `siprtc.delete_workflow` ⚠️ | Delete one of a workspace's workflows (routing rules from tasks to queues) by sid. |
| `siprtc.create_workflow` ✏️ | Create a workflow. |
| `siprtc.update_workflow` ✏️ | Replace a workflow (send every field; the API overwrites the whole workflow). |
| `siprtc.list_task_channels`  | List a workspace's task channels (voice, chat, sms, ...). |
| `siprtc.list_workers`  | List the workers (agents) in a workspace. |
| `siprtc.get_worker`  | Fetch one of a workspace's workers (agents) by sid. |
| `siprtc.delete_worker` ⚠️ | Delete one of a workspace's workers (agents) by sid. |
| `siprtc.create_worker` ✏️ | Create a worker (agent) in a workspace. |
| `siprtc.update_worker` ✏️ | Update a worker's name, routing attributes or status (friendly_name, attributes and status are required). |
| `siprtc.set_worker_activity` ✏️ | Change an agent's live state (e.g. |
| `siprtc.list_tasks`  | List tasks (calls, chats, . |
| `siprtc.get_task`  | Fetch one task by sid (WT...), with its status, queue and attributes. |
| `siprtc.create_task` ✏️ 💲 | Create a task: the workflow routes it to a queue and reserves an agent, who is alerted. |
| `siprtc.update_task_status` ✏️ | Move a task on: complete, cancel or wrap it up, optionally with a reason and a disposition. |

### Campaigns — `campaigns`

| Tool | Does |
| --- | --- |
| `siprtc.list_campaigns`  | List campaigns, filterable by name, status, channel or dial type. |
| `siprtc.create_campaign` ✏️ | Create a campaign as a draft. |
| `siprtc.update_campaign` ✏️ | Change a campaign's settings. |
| `siprtc.set_campaign_status` ✏️ 💲 | Start (running), pause, resume (running), finish or cancel a campaign. |
| `siprtc.delete_campaign` ⚠️ | Delete a campaign. |
| `siprtc.list_campaign_progress`  | Per-contact progress of one campaign (who was reached, pending or failed). |
| `siprtc.list_contact_groups`  | List campaign contact lists (groups). |
| `siprtc.create_contact_group` ✏️ | Create a campaign contact list (group). |
| `siprtc.delete_contact_group` ⚠️ | Delete a campaign contact list (group). |
| `siprtc.list_contacts`  | List campaign contacts, filterable by name, email, number or contact list (group_id). |
| `siprtc.create_contact` ✏️ | Add a campaign contact and put it in contact lists (group ids). |
| `siprtc.update_contact` ✏️ | Change a campaign contact. |
| `siprtc.delete_contact` ⚠️ | Delete a campaign contact. |
| `siprtc.list_campaign_templates`  | List message templates used by messaging campaigns. |
| `siprtc.create_campaign_template` ✏️ | Create a campaign message template. |
| `siprtc.delete_campaign_template` ⚠️ | Delete a campaign message template. |

### Reports — `reports`

| Tool | Does |
| --- | --- |
| `siprtc.run_report`  | Run a contact-centre report and return its rows. |
| `siprtc.export_report` ✏️ | Start a CSV export of a report. |
| `siprtc.list_report_exports`  | List generated report exports. |
| `siprtc.get_report_export`  | Get a finished report export's download link (a short-lived signed URL). |
| `siprtc.delete_report_export` ⚠️ | Delete a generated report export. |

### Flows — `flows`

| Tool | Does |
| --- | --- |
| `siprtc.list_flows`  | List the account's flows. |
| `siprtc.get_flow`  | Fetch one flow, including its URL. |
| `siprtc.get_flow_status`  | Show whether a flow's container is running (status, phase, replicas). |
| `siprtc.create_flow` ✏️ | Create a flow; its container starts and the response carries the flow URL and secret. |
| `siprtc.update_flow` ✏️ | Rename a flow, change its time zone or status callback, or attach it to an application. |
| `siprtc.restart_flow` ✏️ | Start or restart a flow's container. |
| `siprtc.stop_flow` ⚠️ | Stop a flow's container; calls and messages routed to it fail until it starts again. |
| `siprtc.delete_flow` ⚠️ | Delete a flow, its container and its voice application. |

### AI agents — `ai_agents`

| Tool | Does |
| --- | --- |
| `siprtc.list_ai_agents`  | List AI agents. |
| `siprtc.get_ai_agent`  | Fetch one AI agent, including its prompt, tools and runtime settings. |
| `siprtc.create_ai_agent` ✏️ | Create an AI agent. |
| `siprtc.update_ai_agent` ✏️ | Change an AI agent. |
| `siprtc.delete_ai_agent` ⚠️ | Delete an AI agent. |
| `siprtc.list_ai_agent_categories`  | List the categories an AI agent can have. |
| `siprtc.list_ai_agent_sessions`  | List AI agent conversations (sessions), optionally for one agent. |
| `siprtc.create_ai_agent_session` ✏️ | Open a chat session with an AI agent; then talk to it with siprtc.send_agent_message. |
| `siprtc.get_ai_agent_session`  | Fetch one AI agent session. |
| `siprtc.send_agent_message` ✏️ 💲 | Send a user message into an AI agent session and get the agent's reply (and any tool calls it made). |
| `siprtc.list_ai_agent_session_messages`  | List the messages exchanged in an AI agent session. |
| `siprtc.delete_ai_agent_session` ⚠️ | Delete an AI agent session and its messages. |
| `siprtc.list_voices`  | List text-to-speech voices: the account's saved voices, or the full catalogue with catalog=true. |

### Workforce management — `workforce`

| Tool | Does |
| --- | --- |
| `siprtc.list_shift_templates`  | List shift templates (named working hours on given weekdays). |
| `siprtc.create_shift_template` ✏️ | Create a shift template. |
| `siprtc.delete_shift_template` ⚠️ | Delete a shift template. |
| `siprtc.list_shift_assignments`  | List which agents are assigned to which shift templates. |
| `siprtc.create_shift_assignment` ✏️ | Assign agents (Auth IDs) to a shift template from start_date (YYYY-MM-DD), optionally until end_date. |
| `siprtc.delete_shift_assignment` ⚠️ | Remove a shift assignment. |
| `siprtc.list_scheduled_shifts`  | List concrete scheduled shifts, filterable by agent, template, status and date range (YYYY-MM-DD). |

<!-- tools:end -->

## Authentication

Credentials are resolved in this order:

1. **Bearer token on the current HTTP request.** The token is the URL-safe base64 encoding
   of `auth_id:auth_secret`. With `SIPRTC_VERIFY_BEARER=true` (the default) a new token is
   checked against SIPRTC once and the answer cached for five minutes, so a wrong token is
   refused when the client connects. One running server can act for whichever account made
   the request.
2. **Environment variables** `SIPRTC_AUTH_ID` and `SIPRTC_AUTH_SECRET`. The usual choice for
   stdio, where the server belongs to one user.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `SIPRTC_AUTH_ID` | — | Account Auth ID (stdio) |
| `SIPRTC_AUTH_SECRET` | — | Account Auth secret (stdio) |
| `SIPRTC_BASE_URL` | `https://api.siprtc.io/v1` | API base. Point this at a private or on-premise deployment. Plain `http` is refused except for localhost. |
| `SIPRTC_ALLOW_INSECURE_HTTP` | `false` | Allow a plain-`http` base URL on a private network. |
| `SIPRTC_READ_ONLY` | `false` | Register read tools only. |
| `SIPRTC_TOOLSETS` | all | Comma-separated toolsets to load, e.g. `voice,messaging`. |
| `SIPRTC_TIMEOUT` | `30` | Seconds per API request (1-300). |
| `SIPRTC_MAX_RETRIES` | `2` | Retries for reads on 429/502/503/504 and for any request that never reached the API (0-5). Writes are not retried after the API received them, so nothing is sent twice. |
| `SIPRTC_VERIFY_BEARER` | `true` | Check HTTP bearer tokens against SIPRTC before accepting them. |
| `SIPRTC_LOG_LEVEL` | `INFO` | Log level. Logs go to stderr and never include secrets or request bodies. |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `MCP_HOST` | `127.0.0.1` | Bind address, HTTP transport only |
| `MCP_PORT` | `8000` | Port, HTTP transport only |
| `MCP_PATH` | `/mcp` | Endpoint path, HTTP transport only |

A bad value stops the server at start-up with a message naming the variable.

### Endpoint overrides

If your deployment uses different routes for these resources, each can be overridden
without a code change. Paths are relative to `SIPRTC_BASE_URL` and may contain `{auth_id}`
and the resource's own placeholders.

`SIPRTC_PHONE_NUMBERS_LIST_PATH` · `SIPRTC_PHONE_NUMBERS_GET_PATH` ·
`SIPRTC_PHONE_NUMBERS_BUY_PATH` · `SIPRTC_PHONE_NUMBERS_RELEASE_PATH` ·
`SIPRTC_PHONE_NUMBERS_AVAILABLE_PATH` · `SIPRTC_PHONE_NUMBERS_ASSOCIATE_PATH` ·
`SIPRTC_SIP_USERS_PATH` · `SIPRTC_SIP_USER_PATH` · `SIPRTC_APPLICATIONS_PATH` ·
`SIPRTC_APPLICATION_PATH`

## Docker

The image builds a wheel, installs it into a slim Python 3.13 image, runs as an
unprivileged user, defaults to the HTTP transport and has a health check.

```bash
docker build -t siprtc-mcp:latest .

docker run --rm -p 8000:8000 siprtc-mcp:latest
```

Clients then send their own bearer token. For a single-account deployment, pass
`-e SIPRTC_AUTH_ID=... -e SIPRTC_AUTH_SECRET=...` instead.

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

## Development and tests

```bash
python -m pip install -e '.[dev]'
ruff check siprtc_mcp tests && ruff format --check siprtc_mcp tests
pytest                     # unit tests, no network
```

The live suite drives every toolset through a real MCP client against a real deployment.
Run it only against a **test** account: each test creates what it needs under an
`mcpe2e…` name and removes it again.

```bash
SIPRTC_AUTH_ID=... SIPRTC_AUTH_SECRET=... SIPRTC_BASE_URL=https://api.<test-host>/v1 \
  pytest -m live tests/live
```

Tests that place calls or send messages also need `SIPRTC_E2E_BILLABLE=1` and targets that
reach simulators or numbers you own: `SIPRTC_E2E_CALL_FROM`, `SIPRTC_E2E_CALL_TO`,
`SIPRTC_E2E_ANSWER_TO` (a destination that answers at once), `SIPRTC_E2E_SMS_TO`, and
`SIPRTC_E2E_PLIVO_NUMBER` / `SIPRTC_E2E_PLIVO_AUTH_ID` / `SIPRTC_E2E_PLIVO_TOKEN` for an SMS
channel to connect.

After adding or renaming a tool, regenerate the reference above with
`python scripts/tool_reference.py` (CI fails if it is stale).

## Billing

The server is free. Calls and messages it places are billed on your SIPRTC account at your
existing rates. An agent in a retry loop spends real money, so scope its credentials and
toolsets accordingly.

## Contributing

Issues and pull requests are welcome. The most useful issue describes the call you were
trying to make and what the agent did instead.

## Licence

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
