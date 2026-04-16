"""
Session endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.session import Session
from app.schemas.session import SessionOut
from app.services.session_manager import session_manager

router = APIRouter()


@router.get("/", response_model=list[SessionOut])
def list_sessions(
    limit: int = Query(50, ge=1, le=500),
    db: DBSession = Depends(get_db),
):
    sessions = (
        db.query(Session)
        .order_by(Session.start_time.desc())
        .limit(limit)
        .all()
    )
    return sessions


@router.get("/latest", response_model=SessionOut)
def latest_session(db: DBSession = Depends(get_db)):
    session = db.query(Session).order_by(Session.start_time.desc()).first()
    if not session:
        raise HTTPException(status_code=404, detail="No sessions yet")
    return session


@router.get("/current")
def current_session():
    return {
        "session_id": session_manager.current_session_id,
        "camera_active": session_manager.camera_active,
    }


@router.post("/take-break")
def take_break():
    """Called from the frontend when the user completes a 20-20-20 break."""
    return session_manager.acknowledge_break()


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: DBSession = Depends(get_db)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session