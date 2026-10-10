from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.services import store

router = APIRouter(prefix="/sessions")


@router.get("")
def list_sessions(book_id: UUID):
    return store.list_sessions(str(book_id))


@router.get("/{session_id}")
def get_history(session_id: UUID):
    if not store.get_session(str(session_id)):
        raise HTTPException(404, "Session not found.")
    return store.history(str(session_id))


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: UUID):
    store.delete_session(str(session_id))
