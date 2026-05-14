# 🦞 Lobster Proxy

A **transparent LLM security proxy** built with FastAPI. It sits between your application and any OpenAI-compatible LLM endpoint, inspecting every request through the [Lobstertrap](https://github.com/Lobstertrap/lobstertrap) policy engine before forwarding it to the real model.

```
Your App  ──►  Lobster Proxy (:8000)  ──►  Lobstertrap (:8080)
                      │                          │
                      │   ALLOW / DENY / LOG      │
                      ◄──────────────────────────
                      │
                 ──►  Upstream LLM
```

---

## Features

- **Drop-in OpenAI replacement** — exposes `POST /v1/chat/completions`, compatible with any OpenAI SDK
- **Policy enforcement** — every request is inspected by Lobstertrap for DPI signals: prompt injection, malware requests, PII, credential exfiltration, and more
- **LLM-generated rejections** — when a request is blocked, the proxy asks the LLM to explain *why* in plain language before returning the denial to the caller
- **Live Audit Log** — a real-time dashboard at `/dash/` streams all interactions over WebSocket with no polling or database
- **Full error handling** — LLM timeouts, policy errors, and upstream failures are caught, logged, and surfaced with meaningful verdicts (`LLM_TIMEOUT`, `LLM_ERROR`, `ERROR`)
- **Zero persistence** — all data is in-memory; ephemeral by design with a 200-event rolling window

---

## Quickstart

### Prerequisites

- Python 3.12+
- A running [Lobstertrap](https://github.com/Lobstertrap/lobstertrap) instance
- An OpenAI-compatible LLM endpoint (e.g. Ollama, vLLM, Together AI, OpenAI)

### Install

```bash
git clone https://github.com/your-org/lobster-proxy
cd lobster-proxy
uv sync
```

### Configure

Set environment variables before running:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOBSTER_TRAP_URL` | `http://localhost:8080` | URL of your Lobstertrap instance |
| `LOBSTER_PROXY_URL` | `http://localhost:8000` | URL of this proxy server |
| `LLM_API_BASE` | *(none)* | Base URL of your upstream LLM (e.g. `http://localhost:11434`) |

```bash
export LOBSTER_TRAP_URL=http://localhost:8080
export LOBSTER_PROXY_URL=http://localhost:8000
export LLM_API_BASE=http://localhost:11434
```

### Run

```bash
fastapi dev app/main.py          # development (auto-reload)
fastapi run app/main.py          # production
```

The server starts on **`http://localhost:8000`**.

---

## API Reference

### `POST /v1/chat/completions`

OpenAI-compatible chat endpoint. Send requests exactly as you would to the OpenAI API.

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.3-70B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

**Response (allowed):**
```json
{
  "status": "success",
  "data": {
    "request_id": "...",
    "model": "...",
    "content": "Hello! How can I help you?",
    "finish_reason": "stop",
    "usage": { ... }
  }
}
```

**Response (blocked):**
```json
{
  "status": "policy_intercepted",
  "verdict": "DENY",
  "data": {
    "content": "Your request was blocked because it contained prompt injection patterns..."
  }
}
```

---

### `GET /v1/history`

Returns recent interactions from the in-memory store.

| Query param | Default | Description |
|-------------|---------|-------------|
| `limit` | `50` | Max number of events to return |
| `request_id` | — | Filter to a specific request |

```bash
curl "http://localhost:8000/v1/history?limit=20"
```

---

### `WS /v1/ws`

WebSocket endpoint for real-time event streaming. Used by the dashboard.

**Message types received from server:**

| Type | Description |
|------|-------------|
| `initial_state` | Sent on connect — contains recent events |
| `event` | Fired for each new interaction |
| `stats_update` | Updated aggregate stats after each event |

---

### `GET /dash/`

The live **Audit Log** dashboard.

- Real-time feed showing every request as it happens
- Filter by action verdict (ALLOW / DENY / LOG / etc.)
- Click any row for a full detail panel: prompt, response, risk score, DPI signals, extracted entities
- Auto-scrolls to newest events; reconnects automatically on disconnect

---

## Request Lifecycle

```
1. Request arrives at POST /v1/chat/completions
       │
2. Policy Check (Lobstertrap)
   ├── ALLOW  ──► Forward to upstream LLM ──► Return response
   └── DENY   ──► Generate explanation via LLM ──► Return block message
       │
3. log_interaction() called in all cases
       │
4. Broadcast over WebSocket to dashboard
```

---

## Project Structure

```
app/
├── main.py                  # FastAPI app, CORS, WebSocket endpoint, static mount
├── routes/
│   └── relay.py             # Route handlers: /v1/chat/completions, /v1/history
├── services/
│   ├── relay.py             # Core request pipeline (policy → LLM → log)
│   ├── lobster.py           # Lobstertrap policy client
│   ├── llm.py               # LiteLLM wrapper for upstream LLM calls
│   └── persistence.py       # In-memory store + WebSocket connection manager
├── models/
│   └── chat.py              # Pydantic request models
├── static/
│   └── index.html           # Audit Log dashboard (single-file, no build step)
└── utils/
    └── logging.py           # Shared logger
```

---

## Testing

A quick smoke test script is included:

```bash
python app/test.py
```

This sends two requests through the proxy — one benign, one adversarial — and prints the responses. The malicious request should be intercepted and return a policy block message.

---

## Notes

- **Fail-open by default** — if Lobstertrap is unreachable, requests are allowed through and marked with an `ERROR` verdict. Change `allowed: True` in `lobster.py` to `False` to fail closed.
- **No authentication** — CORS is currently set to `allow_origins=["*"]`. Restrict this before deploying to production.
- **Ephemeral data** — interactions are stored in a `deque(maxlen=200)` and lost on restart. This is intentional for a lightweight observability layer.
