"""API routes for browsing event ingestion."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from database.db import get_db
from database.models import BrowsingEvent, User
from api.models.schemas import EventCreate, EventResponse
from api.auth import require_user
from cache import cache
from rate_limiter import limiter, RATE_WRITE
from agents.context_agent import ContextAgent, _extract_domain, DISTRACTION_DOMAINS, MIXED_DOMAINS

router = APIRouter(prefix="/events", tags=["events"])

_context_agent = ContextAgent()


@router.post("/", response_model=EventResponse)
@limiter.limit(RATE_WRITE)
async def create_event(
    request: Request,
    event: EventCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Ingest a browsing event from the extension."""
    domain = event.domain or _extract_domain(event.url)

    # Quick classification via context agent
    context = _context_agent.analyze({
        "current_url": event.url,
        "current_title": event.title,
        "current_domain": domain,
        "study_topic": None,
        "session_active": event.session_id is not None,
        "recent_domains": [],
    })

    is_distraction = context["classification"] == "distraction"
    distraction_score = max(0.0, -context["context_score"])

    # Fallback: check known distraction domains
    if not is_distraction and domain and domain in DISTRACTION_DOMAINS:
        is_distraction = True
        distraction_score = max(distraction_score, 0.7)

    # Strip timezone to avoid PostgreSQL Timezone insertion exceptions
    ts = event.timestamp or datetime.utcnow()
    if ts.tzinfo is not None:
        # Convert to UTC first, then strip tzinfo
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)

    db_event = BrowsingEvent(
        user_id=user.id,
        timestamp=ts,
        url=event.url,
        domain=domain,
        title=event.title,
        duration_seconds=event.duration_seconds,
        is_distraction=is_distraction,
        distraction_score=distraction_score,
        category=event.category or context["classification"],
        session_id=event.session_id,
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    # Invalidate cached analytics for this user
    await cache.invalidate_pattern(f"analytics:user:{user.id}:*")

    return db_event


@router.get("/", response_model=list[EventResponse])
async def list_events(
    limit: int = 50,
    offset: int = 0,
    since: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """List recent browsing events."""
    query = (
        select(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user.id)
        .order_by(BrowsingEvent.timestamp.desc())
    )
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            query = query.filter(BrowsingEvent.timestamp >= since_dt)
        except ValueError:
            pass
    result = await db.execute(query.offset(offset).limit(limit))
    return result.scalars().all()


@router.get("/today/summary")
async def today_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    """Get summary stats for today's browsing activity."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    query = (
        select(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user.id)
        .filter(BrowsingEvent.timestamp >= today_start)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    total_seconds = sum(e.duration_seconds for e in events)
    distraction_seconds = sum(
        e.duration_seconds for e in events if e.is_distraction
    )
    focus_seconds = total_seconds - distraction_seconds

    return {
        "total_events": len(events),
        "total_seconds": total_seconds,
        "focus_seconds": focus_seconds,
        "distraction_seconds": distraction_seconds,
        "focus_percentage": round(
            (focus_seconds / total_seconds * 100) if total_seconds > 0 else 0, 1
        ),
    }
