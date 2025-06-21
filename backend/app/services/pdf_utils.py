import fitz  # PyMuPDF
import re
import emoji
from pathlib import Path

def normalize_text(text: str) -> str:
    """Remove URLs, emojis, control chars, collapse whitespace."""
    text = re.sub(r"http\S+|www\S+", "", text)
    text = emoji.replace_emoji(text, replace="")
    text = re.sub(r"[\x00-\x1F]+", "", text)
    return re.sub(r"\s+", " ", text).strip()

def split_into_sentences(text: str) -> list[str]:
    """Break on . ? ! followed by whitespace."""
    parts = re.split(r'(?<=[\.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]

def chunk_text(text: str, max_len: int = 500) -> list[str]:
    """Accumulate sentences into ~500-char chunks."""
    sentences = split_into_sentences(text)
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_len:
            current += sent + " "
        else:
            chunks.append(current.strip())
            current = sent + " "
    if current:
        chunks.append(current.strip())
    return chunks

def extract_and_clean(pdf_path: Path):
    """
    Returns:
      chunks: list[str]
      metadata: {
        title: str,
        author: str,
        chapters: [{ title: str, page: int }, …]
      }
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    seen = set()
    chapters = []

    # build raw text + chapter TOC
    for page_no, page in enumerate(doc, start=1):
        txt = page.get_text()
        full_text += txt + "\n"
        for line in txt.split("\n"):
            # match “Chapter 1: Intro” or “1.2 Section title”
            m = re.match(r'^(Chapter\s+\d+(?:\.\d+)*\b.*)', line.strip(), re.I) \
             or re.match(r'^(\d+\.\d+\s+.+)', line.strip())
            if m:
                title = m.group(1).strip()
                if title not in seen:
                    seen.add(title)
                    chapters.append({"title": title, "page": page_no})

    # normalize & chunk
    cleaned = normalize_text(full_text)
    chunks = chunk_text(cleaned)

    # collect doc-level metadata
    metadata = {
        "title": doc.metadata.get("title", "").strip(),
        "author": doc.metadata.get("author", "").strip(),
        "chapters": chapters
    }

    return chunks, metadata