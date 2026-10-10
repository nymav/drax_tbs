"""Original, deliberately small study material for a real first-use workflow."""

import pymupdf as fitz
from fastapi import APIRouter
from app import config
from app.services import store, pdf_utils

router = APIRouter()
SAMPLE_ID = "00000000-0000-4000-8000-000000000001"
PAGES = [
    (
        "Learning that lasts",
        "Active recall means trying to retrieve an idea from memory before checking your notes. A learner closes the book, answers a question, then compares their response with the source. The comparison reveals gaps and gives a specific target for the next study session. Rereading can make a passage feel familiar without testing whether it can be recalled. Practice questions are useful because they make the learner retrieve rather than merely recognise the answer.",
    ),
    (
        "Spacing and feedback",
        "Spaced practice distributes study across separate sessions instead of concentrating it into one sitting. A simple study routine is to revisit an idea the next day, several days later, and then again after a longer interval. The exact interval depends on difficulty and the learner. Feedback should identify the gap between an answer and the source, not merely label it wrong. After checking an answer, write a correction and attempt the question again without looking.",
    ),
    (
        "A small study loop",
        "First, read a short section and identify its key idea. Second, close the document and explain the idea in your own words. Third, check the explanation against the original passage. Fourth, write one question about the part you misunderstood. Finally, return to that question in a later study session. A summary can organise ideas, but creating or reading a summary is not by itself a test of recall. This sample is a demonstration of document-based learning, not a comprehensive educational research review.",
    ),
]


@router.post("/sample")
def sample():
    book = store.get_book(SAMPLE_ID)
    if book:
        return book
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = config.UPLOAD_DIR / f"{SAMPLE_ID}.pdf"
    with fitz.open() as doc:
        doc.set_metadata({"title": "A small guide to better studying", "author": "DRAX sample material"})
        for title, text in PAGES:
            page = doc.new_page()
            page.insert_text((54, 70), title, fontsize=22)
            page.insert_textbox(fitz.Rect(54, 110, 540, 750), text, fontsize=13, lineheight=1.7)
        doc.save(path)
    store.add_book(SAMPLE_ID, "A small guide to better studying", "DRAX sample material", len(PAGES))
    passages, _ = pdf_utils.extract_and_clean(path)
    vectors = None
    if config.RETRIEVAL_MODE in {"semantic", "hybrid"}:
        from app.services.embedding import get_embeddings

        vectors = get_embeddings([p["text"] for p in passages])
    store.replace_passages(SAMPLE_ID, passages, vectors)
    return store.get_book(SAMPLE_ID)
