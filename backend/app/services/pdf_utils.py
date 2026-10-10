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


def extract_and_clean(pdf_path, progress=None):
    passages, sparse = [], []
    with fitz.open(pdf_path) as doc:
        if doc.needs_pass:
            raise ValueError("Password-protected PDFs are not supported. Unlock a copy first.")
        if not 0 < len(doc) <= config.MAX_PAGES:
            raise ValueError(f"Use a PDF with 1–{config.MAX_PAGES} pages.")
        for n, page in enumerate(doc, 1):
            if progress:
                progress(n, len(doc))
            blocks = page.get_text("dict", sort=True)["blocks"]
            text = page.get_text(sort=True)
            headings = []
            sizes = [span["size"] for block in blocks for line in block.get("lines", []) for span in line["spans"]]
            normal = sorted(sizes)[len(sizes) // 2] if sizes else 12
            for block in blocks:
                for line in block.get("lines", []):
                    if any(span["size"] > normal * 1.2 for span in line["spans"]):
                        headings.append("".join(span["text"] for span in line["spans"]))
            tables = page.find_tables().tables
            if len(text.strip()) < 30:
                sparse.append(n)
            base = {
                "headings": headings,
                "heading_origin": "font-size heuristic",
                "page_size": [page.rect.width, page.rect.height],
            }
            groups = []
            for block in blocks:
                if not block.get("lines"):
                    continue
                bbox = fitz.Rect(block["bbox"])
                if any(fitz.Rect(table.bbox).contains(bbox.tl + (bbox.br - bbox.tl) * 0.5) for table in tables):
                    continue
                spans = [span for line in block["lines"] for span in line["spans"]]
                paragraph = " ".join(span["text"] for span in spans)
                size = max(span["size"] for span in spans)
                heading = size > normal * 1.2
                raw = {"bbox": list(bbox), "text": paragraph}
                previous = groups[-1] if groups else None
                # PDFs may encode each visual line as a separate block. Join
                # aligned neighbouring body lines, keeping their raw coordinates.
                if (
                    previous
                    and not heading
                    and previous["kind"] != "heading"
                    and abs(previous["bbox"].x0 - bbox.x0) < 4
                    and abs(previous["size"] - size) < 1
                    and 0 <= bbox.y0 - previous["bbox"].y1 <= size * 0.8
                ):
                    previous["text"] += " " + paragraph
                    previous["bbox"] |= bbox
                    previous["blocks"].append(raw)
                else:
                    groups.append(
                        {
                            "text": paragraph,
                            "bbox": bbox,
                            "blocks": [raw],
                            "size": size,
                            "kind": "heading" if heading else "paragraph",
                        }
                    )
            for group in groups:
                structure = {
                    **base,
                    "kind": group["kind"],
                    "blocks": group["blocks"],
                    "tables": [],
                    "outline": doc.get_toc() if not passages else [],
                }
                passages.extend(
                    {"page": n, "text": chunk, "structure": structure} for chunk in chunk_text(group["text"])
                )
            for table in tables:
                rows = table.extract()
                table_text = "\n".join(" | ".join(cell or "" for cell in row) for row in rows)
                structure = {
                    **base,
                    "kind": "table",
                    "blocks": [{"bbox": list(table.bbox), "text": table_text}],
                    "tables": rows,
                    "outline": doc.get_toc() if not passages else [],
                }
                passages.extend({"page": n, "text": chunk, "structure": structure} for chunk in chunk_text(table_text))
            if len(passages) > 12000:
                raise ValueError("This PDF contains too much text. Split it into smaller documents.")
        metadata = {"title": (doc.metadata or {}).get("title", ""), "pages": len(doc), "sparse_pages": sparse}
    if not passages:
        raise ValueError("No readable text found. Scanned PDFs need OCR before upload.")
    return passages, metadata
