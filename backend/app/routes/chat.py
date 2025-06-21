from fastapi import APIRouter
from app.models.chat_model import ChatQuery, ChatResponse
from app.services import rag_agent

router = APIRouter(prefix="/chat")

@router.post("/", response_model=ChatResponse)
def ask_question(payload: ChatQuery):  # ✅ renamed from 'query' to 'payload'
    print("📩 PDF ID:", payload.pdf_id)
    return rag_agent.get_rag_response(payload)