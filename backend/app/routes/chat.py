from fastapi import APIRouter
from app.models.chat_model import ChatQuery, ChatResponse
from app.services.rag_agent import get_rag_response

router = APIRouter(prefix="/chat")


@router.post("/", response_model=ChatResponse)
def ask_question(payload: ChatQuery):
    return get_rag_response(payload)
