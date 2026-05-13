from fastapi import APIRouter
from app.models.chat import ChatRequest
from app.services.relay import relay_chat

router = APIRouter()


@router.post("/v1/chat/completions")
async def chat(request: ChatRequest):

    return await relay_chat(request)
