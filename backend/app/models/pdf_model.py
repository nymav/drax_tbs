from pydantic import BaseModel
from typing import Optional

class PDFMetadata(BaseModel):
    id: str
    title: str
    filename: str
    subject: Optional[str] = None
    tags: Optional[list[str]] = []