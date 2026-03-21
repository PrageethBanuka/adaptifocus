"""Auto-Retraining Pipeline — closes the ML feedback loop.

Queries UserFeedback rows from the database, generates corrected
training samples, retrains the PatternClassifier, and auto-exports
a new ONNX model.

Run manually:  python -m ml.retrain
Runs automatically via the background scheduler every 24 hours.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict

from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import SessionLocal
from database.models import BrowsingEvent, UserFeedback
from ml.pattern_classifier import PatternClassifier


async def gather_training_data(db: AsyncSession) -> tuple[List[List[Dict]], List[str]]:
    """Build labeled session windows from real browsing data + user corrections.

    Strategy:
      1. Pull the last 30 days of BrowsingEvents.
      2. Chunk them into 30-minute windows.
      3. Label each window based on distraction ratio:
         - <20% distraction  → "focused"
         - 20-40%            → "drifting"
         - >60%              → "distracted"
         - High d2f transitions → "recovering"
      4. Apply corrections from UserFeedback (flip labels for false-positive domains).
    """

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # 1. Fetch events
    result = await db.execute(
        select(BrowsingEvent)
        .filter(BrowsingEvent.timestamp >= thirty_days_ago)
        .order_by(BrowsingEvent.timestamp.asc())
    )
    events = result.scalars().all()

    if len(events) < 20:
        return [], []

    # 2. Fetch false-positive domains for correction
    fp_result = await db.execute(
        select(UserFeedback.domain)
        .filter(UserFeedback.is_false_positive == True)
        .distinct()
    )
    false_positive_domains = {row[0] for row in fp_result.all() if row[0]}

    # 3. Chunk events into 30-minute windows
    sessions: List[List[Dict]] = []
    labels: List[str] = []

    window: List[Dict] = []
    window_start = events[0].timestamp if events else datetime.utcnow()

    for e in events:
        # Apply corrections: flip is_distraction for false-positive domains
        is_distraction = e.is_distraction
        if e.domain in false_positive_domains:
            is_distraction = False

        event_dict = {
            "url": e.url,
            "domain": e.domain,
            "title": e.title,
            "duration_seconds": e.duration_seconds,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "is_distraction": is_distraction,
            "category": e.category,
        }

        if e.timestamp and (e.timestamp - window_start).total_seconds() > 1800:
            # Close current window and start a new one
            if len(window) >= 3:
                label = _label_window(window)
                sessions.append(window)
                labels.append(label)
            window = [event_dict]
            window_start = e.timestamp
        else:
            window.append(event_dict)

    # Don't forget the last window
    if len(window) >= 3:
        sessions.append(window)
        labels.append(_label_window(window))

    return sessions, labels


def _label_window(events: List[Dict]) -> str:
    """Assign a behavioral label to a session window."""
    total = len(events)
    distractions = sum(1 for e in events if e.get("is_distraction"))
    ratio = distractions / max(1, total)

    # Count distraction-to-focus transitions
    d2f = sum(
        1 for i in range(1, len(events))
        if events[i - 1].get("is_distraction") and not events[i].get("is_distraction")
    )

    if ratio < 0.2:
        return "focused"
    elif ratio < 0.4:
        return "drifting"
    elif ratio >= 0.6:
        return "distracted"
    elif d2f > 2:
        return "recovering"
    else:
        return "drifting"


async def retrain():
    """Main retraining entrypoint."""
    print("[Retrain] Starting auto-retraining pipeline...")

    async with SessionLocal() as db:
        # Check if there's any new feedback to learn from
        count_result = await db.execute(select(func.count(UserFeedback.id)))
        feedback_count = count_result.scalar() or 0
        print(f"[Retrain] Found {feedback_count} feedback entries.")

        sessions, labels = await gather_training_data(db)

    if len(sessions) < 5:
        print(f"[Retrain] Not enough training data ({len(sessions)} sessions). Need at least 5. Skipping.")
        return {"status": "skipped", "reason": "insufficient_data", "sessions": len(sessions)}

    print(f"[Retrain] Training on {len(sessions)} session windows...")
    classifier = PatternClassifier()
    metrics = classifier.train(sessions, labels)

    print(f"[Retrain] Complete! Accuracy: {metrics.get('accuracy_cv_mean', 'N/A')}")
    return {"status": "success", "metrics": metrics}


if __name__ == "__main__":
    asyncio.run(retrain())
