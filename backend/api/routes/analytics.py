"""API routes for analytics dashboard data."""

from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.db import get_db
from database.models import BrowsingEvent, Intervention, StudySession, UserPattern, User
from api.models.schemas import FocusSummary, PatternResponse
from api.auth import require_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/focus-summary", response_model=FocusSummary)
def get_focus_summary(
    days: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Summary of focus vs distraction for the last N days."""
    since = datetime.utcnow() - timedelta(days=days)

    events = (
        db.query(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user.id)
        .filter(BrowsingEvent.timestamp >= since)
        .all()
    )

    total_seconds = sum(e.duration_seconds for e in events)
    distraction_seconds = sum(e.duration_seconds for e in events if e.is_distraction)
    focus_seconds = total_seconds - distraction_seconds

    # Top distracting domains
    domain_distraction: dict[str, int] = defaultdict(int)
    domain_productive: dict[str, int] = defaultdict(int)
    for e in events:
        if not e.domain:
            continue
        if e.is_distraction:
            domain_distraction[e.domain] += e.duration_seconds
        else:
            domain_productive[e.domain] += e.duration_seconds

    top_distracting = sorted(
        [{"domain": d, "seconds": s} for d, s in domain_distraction.items()],
        key=lambda x: x["seconds"],
        reverse=True,
    )[:5]

    top_productive = sorted(
        [{"domain": d, "seconds": s} for d, s in domain_productive.items()],
        key=lambda x: x["seconds"],
        reverse=True,
    )[:5]

    # Interventions
    interventions = (
        db.query(Intervention)
        .filter(Intervention.user_id == user.id)
        .filter(Intervention.timestamp >= since)
        .all()
    )
    success_count = sum(1 for i in interventions if i.was_effective)
    success_rate = (
        (success_count / len(interventions) * 100) if interventions else 0.0
    )

    distraction_events = sum(1 for e in events if e.is_distraction)

    return FocusSummary(
        total_events=len(events),
        distraction_events=distraction_events,
        total_seconds=total_seconds,
        focus_seconds=focus_seconds,
        distraction_seconds=distraction_seconds,
        focus_percentage=round(
            (focus_seconds / total_seconds * 100) if total_seconds > 0 else 0, 1
        ),
        top_distracting_domains=top_distracting,
        top_productive_domains=top_productive,
        interventions_today=len(interventions),
        intervention_success_rate=round(success_rate, 1),
    )


@router.get("/hourly-breakdown")
def get_hourly_breakdown(
    days: int = 7,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Hourly focus/distraction breakdown for pattern visualization."""
    since = datetime.utcnow() - timedelta(days=days)

    events = (
        db.query(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user.id)
        .filter(BrowsingEvent.timestamp >= since)
        .all()
    )

    hourly: dict[int, dict] = {
        h: {"hour": h, "focus": 0, "distraction": 0, "total": 0}
        for h in range(24)
    }

    for e in events:
        if e.timestamp:
            h = e.timestamp.hour
            hourly[h]["total"] += e.duration_seconds
            if e.is_distraction:
                hourly[h]["distraction"] += e.duration_seconds
            else:
                hourly[h]["focus"] += e.duration_seconds

    return list(hourly.values())


@router.get("/patterns", response_model=list[PatternResponse])
def get_patterns(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Get discovered user patterns."""
    return (
        db.query(UserPattern)
        .filter(UserPattern.user_id == user.id)
        .order_by(UserPattern.confidence.desc())
        .limit(20)
        .all()
    )


@router.get("/intervention-history")
def get_intervention_history(
    days: int = 7,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Get recent intervention history with outcomes."""
    since = datetime.utcnow() - timedelta(days=days)

    interventions = (
        db.query(Intervention)
        .filter(Intervention.user_id == user.id)
        .filter(Intervention.timestamp >= since)
        .order_by(Intervention.timestamp.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": i.id,
            "timestamp": i.timestamp.isoformat(),
            "level": i.level,
            "trigger_domain": i.trigger_domain,
            "duration_on_distraction": i.duration_on_distraction_seconds,
            "user_response": i.user_response,
            "was_effective": i.was_effective,
        }
        for i in interventions
    ]
