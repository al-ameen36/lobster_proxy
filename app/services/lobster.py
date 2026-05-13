async def evaluate_policy(request):

    text = " ".join(msg["content"] for msg in request.messages if msg["role"] == "user")

    banned = ["hack", "exploit", "malware"]

    for word in banned:
        if word in text.lower():
            return {
                "allowed": False,
                "policy": "restricted_content",
                "reason": f"Detected banned keyword: {word}",
            }

    return {"allowed": True}
