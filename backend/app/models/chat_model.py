from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class ChatQuery(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    role: Literal["tutor", "explainer", "summarizer", "quizzer", "reviewer", "strict", "default"] = "tutor"
    pdf_id: UUID
    session_id: UUID | None = None
    section_id: str | None = Field(default=None, max_length=80)
    depth: Literal["overview", "standard", "deep"] = "standard"
    page_from: int | None = Field(default=None, ge=1)
    page_to: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_range(self):
        self.query = self.query.strip()
        if not self.query:
            raise ValueError("Enter a question.")
        if self.page_from and self.page_to and self.page_from > self.page_to:
            raise ValueError("Page range is reversed.")
        return self


class Source(BaseModel):
    id: str
    page: int
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[str] = []
    sources: list[Source] = []
    session_id: str
    mode: Literal["generated", "evidence", "no_match"]
    notice: str | None = None
    claims: list[dict] = []
    token_budget: dict | None = None
    role: str
    depth: str
