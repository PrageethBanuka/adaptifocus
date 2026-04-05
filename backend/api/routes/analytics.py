"""API routes for analytics dashboard data (with caching)."""

from datetime import datetime, timedelta
from collections import defaultdict
import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, delete

from database.db import get_db
from database.models import BrowsingEvent, Intervention, StudySession, UserPattern, User
from api.models.schemas import FocusSummary, PatternResponse
from api.auth import require_user
from services.pattern_service import update_user_patterns
from agents.pattern_agent import PatternAgent
from cache import cache

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/focus-summary", response_model=FocusSummary)
async def get_focus_summary(
    days: int = 1,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Summary of focus vs distraction for the last N days."""
    cache_key = f"analytics:user:{user.id}:summary:{days}"
    cached = await cache.get(cache_key)
    if cached:
        return FocusSummary(**cached)

    since = datetime.utcnow() - timedelta(days=days)

    query = (
        select(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user.id)
        .filter(BrowsingEvent.timestamp >= since)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    total_seconds = sum(e.duration_seconds for e in events)
    distraction_seconds = sum(e.duration_seconds for e in events if e.is_distraction)
    neutral_seconds = sum(e.duration_seconds for e in events if not e.is_distraction and e.category == "neutral")
    focus_seconds = total_seconds - distraction_seconds - neutral_seconds

    # Top distracting domains
    domain_distraction: dict[str, int] = defaultdict(int)
    domain_productive: dict[str, int] = defaultdict(int)
    for e in events:
        if not e.domain:
            continue
        if e.is_distraction:
            domain_distraction[e.domain] += e.duration_seconds
        elif e.category != "neutral":
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
    interv_query = (
        select(Intervention)
        .filter(Intervention.user_id == user.id)
        .filter(Intervention.timestamp >= since)
    )
    interv_result = await db.execute(interv_query)
    interventions = interv_result.scalars().all()
    success_count = sum(1 for i in interventions if i.was_effective)
    success_rate = (
        (success_count / len(interventions) * 100) if interventions else 0.0
    )

    distraction_events = sum(1 for e in events if e.is_distraction)

    result = FocusSummary(
        total_events=len(events),
        distraction_events=distraction_events,
        total_seconds=total_seconds,
        focus_seconds=focus_seconds,
        distraction_seconds=distraction_seconds,
        neutral_seconds=neutral_seconds,
        focus_percentage=round(
            (focus_seconds / total_seconds * 100) if total_seconds > 0 else 0, 1
        ),
        top_distracting_domains=top_distracting,
        top_productive_domains=top_productive,
        interventions_today=len(interventions),
        intervention_success_rate=round(success_rate, 1),
    )
    await cache.set(cache_key, result.model_dump(), ttl=60)
    return result


@router.get("/hourly-breakdown")
async def get_hourly_breakdown(
    days: int = 7,
    tz_offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Hourly focus/distraction breakdown for pattern visualization."""
    cache_key = f"analytics:user:{user.id}:hourly:{days}:{tz_offset}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    since = datetime.utcnow() - timedelta(days=days)

    query = (
        select(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user.id)
        .filter(BrowsingEvent.timestamp >= since)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    hourly: dict[int, dict] = {
        h: {"hour": h, "focus": 0, "distraction": 0, "total": 0}
        for h in range(24)
    }

    for e in events:
        if e.timestamp:
            # tz_offset is in minutes (UTC - Local). e.g., -330 for UTC+5:30
            # So local_time = utc_time - tz_offset
            local_dt = e.timestamp - timedelta(minutes=tz_offset)
            h = local_dt.hour
            hourly[h]["total"] += e.duration_seconds
            if e.is_distraction:
                hourly[h]["distraction"] += e.duration_seconds
            else:
                hourly[h]["focus"] += e.duration_seconds

    data = list(hourly.values())
    await cache.set(cache_key, data, ttl=60)
    return data


@router.get("/patterns", response_model=list[PatternResponse])
async def get_patterns(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Get discovered user patterns.
    
    Dynamically analyzes the user's last 14 days of events,
    persists the findings, and returns the models.
    """
    cache_key = f"analytics:user:{user.id}:patterns"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # Compute and persist patterns
    await update_user_patterns(user.id, db)

    query = (
        select(UserPattern)
        .filter(UserPattern.user_id == user.id)
        .order_by(UserPattern.confidence.desc())
        .limit(20)
    )
    res = await db.execute(query)
    patterns = res.scalars().all()
    
    await cache.set(cache_key, [
        {"id": p.id, "user_id": p.user_id, "pattern_type": p.pattern_type,
         "description": p.description, "confidence": p.confidence,
         "data_json": p.data_json, "discovered_at": str(p.discovered_at)}
        for p in patterns
    ], ttl=300)
    
    return patterns


@router.get("/intervention-history")
async def get_intervention_history(
    days: int = 7,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Get recent intervention history with outcomes."""
    since = datetime.utcnow() - timedelta(days=days)

    query = (
        select(Intervention)
        .filter(Intervention.user_id == user.id)
        .filter(Intervention.timestamp >= since)
        .order_by(Intervention.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    interventions = result.scalars().all()

    return [
        {
            "id": i.id,
            "timestamp": i.timestamp.isoformat() + "Z",
            "level": i.level,
            "trigger_domain": i.trigger_domain,
            "duration_on_distraction": i.duration_on_distraction_seconds,
            "user_response": i.user_response,
            "was_effective": i.was_effective,
        }
        for i in interventions
    ]
