import traceback
from app.services.lobster import evaluate_policy
from app.services.llm import generate_response
from app.utils.logging import logger
import uuid


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
    """Uses the LLM to explain why a request was rejected by the policy engine."""

    prompt = f"""
    Policy violation detected.

    Verdict: {verdict}
    Reason: {reason}
    Input: {user_message}

    Write a 3-sentence explanation:
    - Sentence 1: what was blocked
    - Sentence 2: why it was blocked
    - Sentence 3: required compliant behavior

    No extra text.
    """

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await generate_response(model=model, messages=messages)
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Failed to generate rejection explanation: {e}")
        return f"[POLICY BLOCK] Your request was intercepted: {reason}"


async def relay_chat(request):
    try:
        request_id = str(uuid.uuid4())
        logger.info(
            f"Received chat request | request_id: {request_id} | model: {request.model}"
        )

        decision = await evaluate_policy(request)
        normalized = {"request_id": request_id}

        if not decision["allowed"]:
            verdict = decision.get("verdict", "DENY")
            reason = decision.get("reason", "Policy violation")
            logger.warning(
                f"Policy action triggered | request_id: {request_id} | verdict: {verdict}"
            )

            # Use the LLM to explain the rejection
            user_msg_text = request.messages[-1]["content"] if request.messages else ""
            explanation = await explain_rejection(
                user_message=user_msg_text,
                verdict=verdict,
                reason=reason,
                model=request.model,
            )

            # Return the explanation as if it were an LLM response
            normalized.update(
                {
                    "id": f"lobstertrap-{request_id}",
                    "model": request.model,
                    "content": explanation,
                    "finish_reason": "stop",
                    "usage": {},
                }
            )
            return {
                "status": "policy_intercepted",
                "verdict": verdict,
                "data": normalized,
            }

        logger.info(f"Request allowed | request_id: {request_id} | calling LLM")
        response = await generate_response(
            model=request.model, messages=request.messages
        )

        normalized_resp = normalize_response(response)
        logger.info(
            f"LLM response received | request_id: {request_id} | usage: {normalized_resp.get('usage')}"
        )

        normalized.update(normalized_resp)

        return {"status": "success", "data": normalized}
    except Exception as e:
        logger.error(f"Error in relay_chat: {e}")
        logger.error(traceback.format_exc())
        raise e
