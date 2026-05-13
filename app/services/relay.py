from app.services.lobster import evaluate_policy
from app.services.llm import generate_response
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


async def relay_chat(request):
    decision = await evaluate_policy(request)
    normalized = {"request_id": str(uuid.uuid4())}

    if not decision["allowed"]:
        normalized.update(
            {
                "status": "rejected",
                "violation": {
                    "policy": decision["policy"],
                    "reason": decision["reason"],
                },
            }
        )
        return normalized

    response = await generate_response(model=request.model, messages=request.messages)
    normalized.update(normalize_response(response))

    return {"status": "success", "data": normalized}
