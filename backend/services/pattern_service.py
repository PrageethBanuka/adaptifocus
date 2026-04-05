import json
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from database.models import BrowsingEvent, UserPattern
from agents.pattern_agent import PatternAgent
from database.db import SessionLocal


async def update_user_patterns(user_id: int, db: AsyncSession):
    """
    Dynamically analyzes the user's last 14 days of events,
    persists the findings. This is meant to be called in the background.
    """
    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    query = (
        select(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user_id)
        .filter(BrowsingEvent.timestamp >= two_weeks_ago)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    if not events:
        return

    event_dicts = [
        {
            "url": e.url,
            "domain": e.domain,
            "title": e.title,
            "duration_seconds": e.duration_seconds,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "is_distraction": e.is_distraction,
            "category": e.category,
        }
        for e in events
    ]

    agent = PatternAgent()
    analysis_result = agent.analyze({"events": event_dicts})
    patterns = analysis_result.get("patterns", [])

    # Clear old patterns and save new ones
    await db.execute(delete(UserPattern).filter(UserPattern.user_id == user_id))
    
    for p in patterns:
        db.add(UserPattern(
            user_id=user_id,
            pattern_type=p["type"],
            description=p["description"],
            confidence=p["confidence"],
            data_json=json.dumps(p["data"])
        ))
    
    await db.commit()

async def background_update_patterns(user_id: int):
    """Safe wrapper to run update_user_patterns in a FastAPI background task."""
    try:
        async with SessionLocal() as db:
            await update_user_patterns(user_id, db)
    except Exception as e:
        print(f"Error updating patterns in background for user {user_id}: {e}")
