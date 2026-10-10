"""Extract bounded, page-aware passages without inventing page references."""

import re
import pymupdf as fitz
from app import config


def chunk_text(text, max_len=1000, overlap=150):
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        cut = text.rfind(" ", max_len // 2, max_len)
        if cut < 0:
            cut = max_len
        chunks.append(text[:cut])
        text = text[max(1, cut - overlap) :].lstrip()
    return chunks


def extract_and_clean(pdf_path):
    passages, sparse = [], []
    with fitz.open(pdf_path) as doc:
        if doc.needs_pass:
            raise ValueError("Password-protected PDFs are not supported. Unlock a copy first.")
        if not 0 < len(doc) <= config.MAX_PAGES:
            raise ValueError(f"Use a PDF with 1–{config.MAX_PAGES} pages.")
        for n, page in enumerate(doc, 1):
            text = page.get_text(sort=True)
            if len(text.strip()) < 30:
                sparse.append(n)
            passages.extend({"page": n, "text": t} for t in chunk_text(text) if t.strip())
            if len(passages) > 12000:
                raise ValueError("This PDF contains too much text. Split it into smaller documents.")
        metadata = {"title": (doc.metadata or {}).get("title", ""), "pages": len(doc), "sparse_pages": sparse}
    if not passages:
        raise ValueError("No readable text found. Scanned PDFs need OCR before upload.")
    return passages, metadata
