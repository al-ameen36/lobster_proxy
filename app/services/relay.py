import traceback
import uuid

import litellm

from app.services.lobster import evaluate_policy
from app.services.llm import generate_response
from app.services.persistence import log_interaction
from app.utils.logging import logger


def normalize_response(response):
    choice = response["choices"][0]
    message = choice["message"]
    return {
        "id": response["id"],
        "model": response["model"],
        "content": message["content"],
        "finish_reason": choice["finish_reason"],
        "usage": response.get("usage", {}),
    }


async def explain_rejection(
    user_message: str, verdict: str, reason: str, model: str
) -> str:
    """Ask the LLM to produce a human-friendly explanation of a policy block."""
    prompt = f"""Policy violation detected.

Verdict: {verdict}
Reason: {reason}
Input: {user_message}

Write a 3-sentence explanation:
- Sentence 1: what was blocked
- Sentence 2: why it was blocked
- Sentence 3: required compliant behavior

No extra text."""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await generate_response(model=model, messages=messages)
        return response["choices"][0]["message"]["content"]
    except litellm.Timeout:
        # LLM is slow — return a static fallback instead of hanging
        logger.warning("explain_rejection timed out — using static fallback")
        return (
            f"Your request was blocked by policy ({verdict}). "
            f"Reason: {reason}. "
            "Please revise your request to comply with usage policies."
        )
    except Exception as e:
        logger.error(f"explain_rejection failed: {e}")
        return f"[POLICY BLOCK] Your request was intercepted. Reason: {reason}"


async def relay_chat(request):
    request_id = str(uuid.uuid4())
    user_msg_text = request.messages[-1]["content"] if request.messages else ""

    logger.info(f"Chat request | request_id={request_id} | model={request.model}")

    # ── 1. Policy check ───────────────────────────────────────────────────────
    try:
        decision = await evaluate_policy(request)
    except Exception as e:
        logger.error(f"evaluate_policy raised unexpectedly: {e}")
        decision = {"allowed": True, "verdict": "ALLOW", "reason": "", "data": {}}

    verdict = decision["verdict"]
    reason = decision.get("reason", "")
    lt_meta = decision.get("data", {}).get("_lobstertrap", {})

    # ── 2. Policy denied ──────────────────────────────────────────────────────
    if not decision["allowed"]:
        logger.warning(f"Policy block | request_id={request_id} | verdict={verdict}")

        explanation = await explain_rejection(
            user_message=user_msg_text,
            verdict=verdict,
            reason=reason,
            model=request.model,
        )

        await log_interaction(
            request_id=request_id,
            model=request.model,
            user_message=user_msg_text,
            verdict=verdict,
            policy_reason=reason,
            final_response=explanation,
            metadata=lt_meta,
        )

        return {
            "status": "policy_intercepted",
            "verdict": verdict,
            "data": {
                "request_id": request_id,
                "id": f"lobstertrap-{request_id}",
                "model": request.model,
                "content": explanation,
                "finish_reason": "stop",
                "usage": {},
            },
        }

    # ── 3. Forward to LLM ─────────────────────────────────────────────────────
    logger.info(f"Forwarding to LLM | request_id={request_id}")

    try:
        response = await generate_response(
            model=request.model, messages=request.messages
        )
        normalized_resp = normalize_response(response)

    except litellm.Timeout as e:
        logger.error(f"LLM timeout | request_id={request_id} | {e}")
        await log_interaction(
            request_id=request_id,
            model=request.model,
            user_message=user_msg_text,
            verdict="LLM_TIMEOUT",
            policy_reason="LLM did not respond in time",
            final_response=str(e),
            metadata=lt_meta,
        )
        return {
            "status": "error",
            "message": "The upstream LLM service did not respond in time. Please try again.",
        }

    except Exception as e:
        logger.error(
            f"LLM error | request_id={request_id} | {e}\n{traceback.format_exc()}"
        )
        await log_interaction(
            request_id=request_id,
            model=request.model,
            user_message=user_msg_text,
            verdict="LLM_ERROR",
            policy_reason=str(e),
            final_response=str(e),
            metadata=lt_meta,
        )
        return {
            "status": "error",
            "message": "The upstream LLM service is currently unavailable or returned an error.",
        }

    # ── 4. Success ────────────────────────────────────────────────────────────
    logger.info(
        f"LLM success | request_id={request_id} | usage={normalized_resp.get('usage')}"
    )

    lt_meta["usage"] = normalized_resp.get("usage")

    await log_interaction(
        request_id=request_id,
        model=request.model,
        user_message=user_msg_text,
        verdict="ALLOW",
        policy_reason=reason,
        final_response=normalized_resp["content"],
        metadata=lt_meta,
    )

    return {
        "status": "success",
        "data": {"request_id": request_id, **normalized_resp},
    }
