# Copilot Guide: Lobster Proxy

A FastAPI-based proxy for intercepting and evaluating LLM requests against custom policies.

## Tech Stack
- **Framework**: FastAPI
- **LLM Library**: LiteLLM (supports various providers via a unified API)
- **Package Manager**: uv

## Core Architecture
- `app/main.py`: Entry point; includes the relay router.
- `app/routes/relay.py`: Defines the `/v1/chat/completions` endpoint.
- `app/services/relay.py`: Core logic for request interception, policy evaluation (via Lobstertrap), and AI-powered rejection explanations.
- `app/services/llm.py`: LiteLLM integration supporting self-hosted providers (vLLM) via `LLM_API_BASE`.
- `app/services/lobster.py`: Policy engine client that communicates with the Lobstertrap server (`LOBSTER_TRAP_URL`).
- `app/models/`: Pydantic models for request/response validation.

## Environment Variables
- `LOBSTER_TRAP_URL`: URL of the Lobstertrap policy server (e.g., `http://localhost:8080`).
- `LLM_API_BASE`: API base for the self-hosted LLM server (e.g., vLLM).

## Workflow
1. Request arrives at `/v1/chat/completions`.
2. `relay_chat` calls `evaluate_policy` (Lobstertrap).
3. If blocked: `explain_rejection` uses the LLM to generate a concise, 3-sentence policy explanation for the agent.
4. If allowed: Request is forwarded directly to the self-hosted LLM via `generate_response`.
5. The response is normalized and returned.

## Development
- Run server: `fastapi dev`
- Test client: `python app/test.py`
