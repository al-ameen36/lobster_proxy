import os
import httpx
from app.utils.logging import logger

LOBSTER_TRAP_URL = os.environ.get("LOBSTER_TRAP_URL", "http://localhost:8080")


async def evaluate_policy(request):
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Calling Lobstertrap evaluation at {LOBSTER_TRAP_URL}")
            response = await client.post(
                f"{LOBSTER_TRAP_URL}/v1/chat/completions",
                json={
                    "model": request.model,
                    "messages": [
                        msg.dict() if hasattr(msg, "dict") else msg
                        for msg in request.messages
                    ],
                },
                timeout=8.0,
            )
            response.raise_for_status()
            data = response.json()

            lt_meta = data.get("_lobstertrap", {})
            verdict = lt_meta.get("verdict", "ALLOW")
            reason = lt_meta.get("reason", "")

            logger.info(f"Lobstertrap verdict: {verdict}")

            return {
                "allowed": verdict == "ALLOW",
                "verdict": verdict,
                "reason": reason,
                "data": data,
            }
        except Exception as e:
            logger.error(f"Error calling Lobstertrap: {e}")
            # Fail closed or open? Let's fail open for now but log it.
            return {"allowed": True, "verdict": "ERROR", "reason": str(e)}
