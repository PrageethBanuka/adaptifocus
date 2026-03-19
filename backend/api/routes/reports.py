"""API routes for daily and weekly focus reports."""

from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from database.db import get_db
from database.models import User, BrowsingEvent, Intervention, StudySession
from api.auth import require_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily")
async def daily_report(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Get a structured daily productivity report for today."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Fetch today's events
    result = await db.execute(
        select(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user.id, BrowsingEvent.timestamp >= today_start)
    )
    events = result.scalars().all()

    total_seconds = sum(e.duration_seconds for e in events)
    focus_seconds = sum(e.duration_seconds for e in events if not e.is_distraction)
    distraction_seconds = total_seconds - focus_seconds

    # Top domains
    domain_time = defaultdict(int)
    for e in events:
        if e.domain:
            domain_time[e.domain] += e.duration_seconds
    top_domains = sorted(domain_time.items(), key=lambda x: x[1], reverse=True)[:5]

    # Interventions today
    interv_result = await db.execute(
        select(Intervention)
        .filter(Intervention.user_id == user.id, Intervention.timestamp >= today_start)
    )
    interventions = interv_result.scalars().all()
    complied = sum(1 for i in interventions if i.was_effective)

    # Sessions today
    sess_result = await db.execute(
        select(StudySession)
        .filter(StudySession.user_id == user.id, StudySession.started_at >= today_start)
    )
    sessions = sess_result.scalars().all()

    productivity_score = round((focus_seconds / max(1, total_seconds)) * 100, 1)

    return {
        "date": today_start.strftime("%Y-%m-%d"),
        "productivity_score": productivity_score,
        "total_seconds": total_seconds,
        "focus_seconds": focus_seconds,
        "distraction_seconds": distraction_seconds,
        "total_events": len(events),
        "study_sessions": len(sessions),
        "interventions": {
            "total": len(interventions),
            "complied": complied,
            "success_rate": round(complied / max(1, len(interventions)) * 100, 1),
        },
        "top_domains": [{"domain": d, "seconds": s} for d, s in top_domains],
        "grade": _grade(productivity_score),
    }


@router.get("/weekly")
async def weekly_report(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Get a weekly summary with day-by-day breakdown and trend analysis."""
    now = datetime.utcnow()
    week_start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    prev_week_start = week_start - timedelta(days=7)

    # This week's events
    result = await db.execute(
        select(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user.id, BrowsingEvent.timestamp >= week_start)
    )
    this_week_events = result.scalars().all()

    # Last week's events (for comparison)
    prev_result = await db.execute(
        select(BrowsingEvent)
        .filter(
            BrowsingEvent.user_id == user.id,
            BrowsingEvent.timestamp >= prev_week_start,
            BrowsingEvent.timestamp < week_start,
        )
    )
    last_week_events = prev_result.scalars().all()

    # Day-by-day breakdown
    daily_breakdown = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_end = day + timedelta(days=1)
        day_events = [e for e in this_week_events if day <= e.timestamp < day_end]
        focus = sum(e.duration_seconds for e in day_events if not e.is_distraction)
        distraction = sum(e.duration_seconds for e in day_events if e.is_distraction)
        total = focus + distraction
        daily_breakdown.append({
            "date": day.strftime("%Y-%m-%d"),
            "day": day.strftime("%A"),
            "focus_seconds": focus,
            "distraction_seconds": distraction,
            "productivity": round((focus / max(1, total)) * 100, 1),
        })

    # Weekly totals
    this_focus = sum(e.duration_seconds for e in this_week_events if not e.is_distraction)
    this_total = sum(e.duration_seconds for e in this_week_events)
    last_focus = sum(e.duration_seconds for e in last_week_events if not e.is_distraction)
    last_total = sum(e.duration_seconds for e in last_week_events)

    this_productivity = round((this_focus / max(1, this_total)) * 100, 1)
    last_productivity = round((last_focus / max(1, last_total)) * 100, 1)
    trend = round(this_productivity - last_productivity, 1)

    return {
        "period": f"{week_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}",
        "productivity_score": this_productivity,
        "previous_week_score": last_productivity,
        "trend": trend,
        "trend_direction": "up" if trend > 0 else "down" if trend < 0 else "stable",
        "total_focus_seconds": this_focus,
        "total_distraction_seconds": this_total - this_focus,
        "daily_breakdown": daily_breakdown,
        "best_day": max(daily_breakdown, key=lambda d: d["productivity"]) if daily_breakdown else None,
        "worst_day": min(daily_breakdown, key=lambda d: d["productivity"]) if daily_breakdown else None,
        "grade": _grade(this_productivity),
    }


def _grade(score: float) -> dict:
    """Assign a letter grade and emoji."""
    if score >= 90:
        return {"letter": "A+", "emoji": "🏆", "message": "Outstanding focus!"}
    elif score >= 80:
        return {"letter": "A", "emoji": "🌟", "message": "Excellent productivity!"}
    elif score >= 70:
        return {"letter": "B", "emoji": "👍", "message": "Good work, keep it up!"}
    elif score >= 60:
        return {"letter": "C", "emoji": "💪", "message": "Room for improvement."}
    elif score >= 50:
        return {"letter": "D", "emoji": "⚠️", "message": "Try to reduce distractions."}
    else:
        return {"letter": "F", "emoji": "🚨", "message": "Focus needs significant improvement."}
