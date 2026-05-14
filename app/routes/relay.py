from fastapi import APIRouter
from app.models.chat import ChatRequest
from app.services.relay import relay_chat
from app.services.persistence import get_interactions

router = APIRouter()

@router.get("/v1/history")
async def history(limit: int = 50, request_id: str = None):
    return await get_interactions(limit=limit, request_id=request_id)


@router.post("/v1/chat/completions")
async def chat(request: ChatRequest):

    return await relay_chat(request)
