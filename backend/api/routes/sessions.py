"""API routes for study session management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.db import get_db
from database.models import StudySession, BrowsingEvent, User
from api.models.schemas import SessionCreate, SessionResponse, SessionEndRequest
from api.auth import require_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start", response_model=SessionResponse)
async def start_session(session: SessionCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_user)):
    """Start a new study session."""
    # End any currently active sessions for this user
    query = (
        select(StudySession)
        .filter(StudySession.user_id == user.id)
        .filter(StudySession.is_active == True)
    )
    result = await db.execute(query)
    active = result.scalars().all()
    for s in active:
        s.is_active = False
        s.ended_at = datetime.utcnow()

    new_session = StudySession(
        user_id=user.id,
        study_topic=session.study_topic,
        planned_duration_minutes=session.planned_duration_minutes,
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session


@router.post("/end", response_model=SessionResponse)
async def end_session(request: SessionEndRequest, db: AsyncSession = Depends(get_db), user: User = Depends(require_user)):
    """End an active study session and compute summary stats."""
    query = (
        select(StudySession)
        .filter(StudySession.id == request.session_id)
        .filter(StudySession.user_id == user.id)
    )
    result = await db.execute(query)
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    session.ended_at = datetime.utcnow()

    # Compute actual focus/distraction from events
    events_query = (
        select(BrowsingEvent)
        .filter(BrowsingEvent.session_id == session.id)
    )
    events_result = await db.execute(events_query)
    events = events_result.scalars().all()
    session.actual_focus_seconds = sum(
        e.duration_seconds for e in events if not e.is_distraction
    )
    session.actual_distraction_seconds = sum(
        e.duration_seconds for e in events if e.is_distraction
    )

    await db.commit()
    await db.refresh(session)
    return session


@router.get("/active", response_model=SessionResponse | None)
async def get_active_session(db: AsyncSession = Depends(get_db), user: User = Depends(require_user)):
    """Get the currently active study session, if any."""
    query = (
        select(StudySession)
        .filter(StudySession.user_id == user.id)
        .filter(StudySession.is_active == True)
    )
    result = await db.execute(query)
    session = result.scalars().first()
    return session


@router.get("/history", response_model=list[SessionResponse])
async def list_sessions(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """List recent study sessions."""
    query = (
        select(StudySession)
        .filter(StudySession.user_id == user.id)
        .order_by(StudySession.started_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()
