from pydantic import BaseModel
from typing import List

class ChatQuery(BaseModel):
    query: str
    role: str
    pdf_id: str

class ChatResponse(BaseModel):
    answer: str
    citations: List[str]