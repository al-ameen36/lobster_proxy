# Copilot Guide: Lobster Proxy

A FastAPI-based proxy for intercepting and evaluating LLM requests against custom policies.

## Tech Stack
- **Framework**: FastAPI
- **LLM Library**: LiteLLM (supports various providers via a unified API)
- **Package Manager**: uv

## Core Architecture
- `app/main.py`: Entry point; includes the relay router.
- `app/routes/relay.py`: Defines the `/v1/chat/completions` endpoint.
- `app/services/relay.py`: Core logic for request interception, policy evaluation, and LLM communication.
- `app/services/llm.py`: LiteLLM integration for chat completions.
- `app/services/lobster.py`: Policy engine (currently performs basic keyword-based filtering).
- `app/models/`: Pydantic models for request/response validation.

## Workflow
1. Request arrives at `/v1/chat/completions`.
2. `relay_chat` (in `relay.py`) calls `evaluate_policy` (in `lobster.py`).
3. If the policy rejects (e.g., contains "hack", "exploit", "malware"), the request is blocked and a rejection status is returned.
4. If allowed, `generate_response` (in `llm.py`) is called using LiteLLM.
5. The response is normalized and returned to the client.

## Development
- Run server: `fastapi dev`
- Test client: `python app/test.py`
