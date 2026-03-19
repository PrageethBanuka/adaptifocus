"""API routes for focus streaks and gamification."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from database.db import get_db
from database.models import User, StudySession, FocusStreak
from api.auth import require_user

router = APIRouter(prefix="/streaks", tags=["gamification"])


@router.get("/current")
async def get_current_streak(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Get the user's current focus streak data."""
    streak = await _get_or_create_streak(db, user.id)

    return {
        "current_streak": streak.current_streak,
        "best_streak": streak.best_streak,
        "total_focused_sessions": streak.total_focused_sessions,
        "last_focused_at": streak.last_focused_at.isoformat() + "Z" if streak.last_focused_at else None,
        "badge": _get_badge(streak.current_streak),
    }


@router.post("/check")
async def check_streak(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Called when a study session ends. Updates streak based on focus quality.

    A session counts as 'focused' if focus_seconds > distraction_seconds.
    Streaks are measured in calendar days — one focused session per day keeps it going.
    """
    streak = await _get_or_create_streak(db, user.id)

    # Find the most recently ended session
    result = await db.execute(
        select(StudySession)
        .filter(StudySession.user_id == user.id)
        .filter(StudySession.is_active == False)
        .order_by(StudySession.ended_at.desc())
        .limit(1)
    )
    session = result.scalars().first()

    if not session:
        return {"status": "no_session", "current_streak": streak.current_streak}

    # Check if session was focused (more focus than distraction)
    was_focused = session.actual_focus_seconds > session.actual_distraction_seconds

    if was_focused:
        today = datetime.utcnow().date()
        last_date = streak.last_focused_at.date() if streak.last_focused_at else None

        if last_date == today:
            # Already counted today — no change
            pass
        elif last_date == today - timedelta(days=1):
            # Consecutive day — extend streak!
            streak.current_streak += 1
            streak.best_streak = max(streak.best_streak, streak.current_streak)
        else:
            # Streak broken (gap > 1 day) — restart
            streak.current_streak = 1

        streak.total_focused_sessions += 1
        streak.last_focused_at = datetime.utcnow()

    else:
        # Distracted session — don't break streak, just don't extend it
        pass

    await db.commit()

    return {
        "status": "updated",
        "was_focused": was_focused,
        "current_streak": streak.current_streak,
        "best_streak": streak.best_streak,
        "badge": _get_badge(streak.current_streak),
    }


async def _get_or_create_streak(db: AsyncSession, user_id: int) -> FocusStreak:
    """Get existing streak record or create a new one."""
    result = await db.execute(
        select(FocusStreak).filter(FocusStreak.user_id == user_id)
    )
    streak = result.scalars().first()

    if not streak:
        streak = FocusStreak(user_id=user_id, current_streak=0, best_streak=0)
        db.add(streak)
        await db.commit()
        await db.refresh(streak)

    return streak


def _get_badge(streak: int) -> dict:
    """Return a badge based on the streak length."""
    if streak >= 30:
        return {"emoji": "💎", "title": "Diamond Focus", "level": 5}
    elif streak >= 14:
        return {"emoji": "🔥", "title": "On Fire", "level": 4}
    elif streak >= 7:
        return {"emoji": "⚡", "title": "Streak Master", "level": 3}
    elif streak >= 3:
        return {"emoji": "🌟", "title": "Rising Star", "level": 2}
    elif streak >= 1:
        return {"emoji": "✨", "title": "Getting Started", "level": 1}
    else:
        return {"emoji": "🎯", "title": "Start Your Journey", "level": 0}
