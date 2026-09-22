from fastapi import APIRouter
from pydantic import BaseModel

from agent.core import run_conversation

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str
    messages: list


@router.post("/chat")
def chat(req: ChatRequest) -> dict:
    return run_conversation(req.user_id, req.messages)
