"""API routes for study session management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import StudySession, BrowsingEvent
from api.models.schemas import SessionCreate, SessionResponse, SessionEndRequest

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start", response_model=SessionResponse)
def start_session(session: SessionCreate, db: Session = Depends(get_db)):
    """Start a new study session."""
    # End any currently active sessions
    active = (
        db.query(StudySession)
        .filter(StudySession.is_active == True)
        .all()
    )
    for s in active:
        s.is_active = False
        s.ended_at = datetime.utcnow()

    new_session = StudySession(
        study_topic=session.study_topic,
        planned_duration_minutes=session.planned_duration_minutes,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.post("/end", response_model=SessionResponse)
def end_session(request: SessionEndRequest, db: Session = Depends(get_db)):
    """End an active study session and compute summary stats."""
    session = db.query(StudySession).get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    session.ended_at = datetime.utcnow()

    # Compute actual focus/distraction from events
    events = (
        db.query(BrowsingEvent)
        .filter(BrowsingEvent.session_id == session.id)
        .all()
    )
    session.actual_focus_seconds = sum(
        e.duration_seconds for e in events if not e.is_distraction
    )
    session.actual_distraction_seconds = sum(
        e.duration_seconds for e in events if e.is_distraction
    )

    db.commit()
    db.refresh(session)
    return session


@router.get("/active", response_model=SessionResponse | None)
def get_active_session(db: Session = Depends(get_db)):
    """Get the currently active study session, if any."""
    session = (
        db.query(StudySession)
        .filter(StudySession.is_active == True)
        .first()
    )
    return session


@router.get("/history", response_model=list[SessionResponse])
def list_sessions(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List recent study sessions."""
    return (
        db.query(StudySession)
        .order_by(StudySession.started_at.desc())
        .limit(limit)
        .all()
    )
