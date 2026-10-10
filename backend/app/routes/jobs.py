from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.services import jobs, store

router = APIRouter()


@router.post("/jobs/index/{book_id}", status_code=202)
def index(book_id: UUID):
    if not store.get_book(str(book_id)):
        raise HTTPException(404, "Document not found.")
    try:
        return {"id": jobs.enqueue(str(book_id)), "status": "queued"}
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.get("/jobs/{identity}")
def status(identity: UUID):
    result = jobs.get(str(identity))
    if not result:
        raise HTTPException(404, "Job not found.")
    return result


@router.post("/jobs/{identity}/cancel")
def cancel(identity: UUID):
    if not jobs.get(str(identity)):
        raise HTTPException(404, "Job not found.")
    jobs.cancel(str(identity))
    return jobs.get(str(identity))


@router.get("/textbooks/{book_id}/outline")
def outline(book_id: UUID):
    if not store.get_book(str(book_id)):
        raise HTTPException(404, "Document not found.")
    import json

    passages = store.page_passages(str(book_id), limit=12000)
    return {"pages": [{"page": p["page"], **json.loads(p["structure"])} for p in passages]}


@router.get("/textbooks/{book_id}/hierarchy")
def hierarchy(book_id: UUID):
    if not store.get_book(str(book_id)):
        raise HTTPException(404, "Document not found.")
    from app.services.hierarchy import tree

    return tree(str(book_id))


@router.get("/textbooks/{book_id}/digest")
def digest(book_id: UUID):
    book = store.get_book(str(book_id))
    if not book or book["status"] != "ready":
        raise HTTPException(409, "Index this document first.")
    from app.services.hierarchy import summarize

    return summarize(str(book_id))


@router.post("/jobs/summary/{book_id}", status_code=202)
def summary_job(book_id: UUID):
    book = store.get_book(str(book_id))
    if not book or book["status"] != "ready":
        raise HTTPException(409, "Index this document first.")
    try:
        return {"id": jobs.enqueue(str(book_id), kind="summary"), "status": "queued"}
    except ValueError as exc:
        raise HTTPException(409, str(exc))
