from fastapi import APIRouter

from agent.core import MODEL

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL}
