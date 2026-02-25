"""Admin analytics routes — aggregate data across all users."""

from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.db import get_db
from database.models import User, BrowsingEvent, StudySession, Intervention

router = APIRouter(prefix="/admin", tags=["admin"])

# Simple admin key check (set ADMIN_KEY env var on Render)
import os
ADMIN_KEY = os.getenv("ADMIN_KEY", "adaptifocus-admin-2024")


def verify_admin(key: str):
    """Verify admin access key."""
    if key != ADMIN_KEY:
        raise HTTPException(403, "Invalid admin key")


@router.get("/overview")
def admin_overview(key: str, db: Session = Depends(get_db)):
    """High-level overview of all users and activity."""
    verify_admin(key)

    total_users = db.query(User).count()
    active_users = (
        db.query(func.count(func.distinct(BrowsingEvent.user_id)))
        .filter(BrowsingEvent.timestamp >= datetime.utcnow() - timedelta(days=7))
        .scalar()
    )

    total_events = db.query(BrowsingEvent).count()
    total_sessions = db.query(StudySession).count()
    total_interventions = db.query(Intervention).count()

    # Group distribution
    groups = (
        db.query(User.experiment_group, func.count(User.id))
        .group_by(User.experiment_group)
        .all()
    )

    # Total time tracked
    total_seconds = db.query(func.sum(BrowsingEvent.duration_seconds)).scalar() or 0
    distraction_seconds = (
        db.query(func.sum(BrowsingEvent.duration_seconds))
        .filter(BrowsingEvent.is_distraction == True)
        .scalar() or 0
    )

    return {
        "total_users": total_users,
        "active_users_7d": active_users,
        "total_events": total_events,
        "total_sessions": total_sessions,
        "total_interventions": total_interventions,
        "total_hours_tracked": round(total_seconds / 3600, 1),
        "total_focus_hours": round((total_seconds - distraction_seconds) / 3600, 1),
        "total_distraction_hours": round(distraction_seconds / 3600, 1),
        "overall_focus_pct": round(
            ((total_seconds - distraction_seconds) / total_seconds * 100)
            if total_seconds > 0 else 0, 1
        ),
        "experiment_groups": {g: c for g, c in groups},
    }


@router.get("/users")
def admin_users(key: str, db: Session = Depends(get_db)):
    """Per-user breakdown with stats."""
    verify_admin(key)

    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []

    for user in users:
        # User's events
        event_count = db.query(BrowsingEvent).filter(
            BrowsingEvent.user_id == user.id
        ).count()

        total_sec = (
            db.query(func.sum(BrowsingEvent.duration_seconds))
            .filter(BrowsingEvent.user_id == user.id)
            .scalar() or 0
        )

        distraction_sec = (
            db.query(func.sum(BrowsingEvent.duration_seconds))
            .filter(
                BrowsingEvent.user_id == user.id,
                BrowsingEvent.is_distraction == True,
            )
            .scalar() or 0
        )

        session_count = db.query(StudySession).filter(
            StudySession.user_id == user.id
        ).count()

        intervention_count = db.query(Intervention).filter(
            Intervention.user_id == user.id
        ).count()

        # Last activity
        last_event = (
            db.query(BrowsingEvent)
            .filter(BrowsingEvent.user_id == user.id)
            .order_by(BrowsingEvent.timestamp.desc())
            .first()
        )

        result.append({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "experiment_group": user.experiment_group,
            "joined": user.created_at.isoformat() if user.created_at else None,
            "consent_given": user.consent_given,
            "total_events": event_count,
            "total_hours": round(total_sec / 3600, 1),
            "focus_hours": round((total_sec - distraction_sec) / 3600, 1),
            "distraction_hours": round(distraction_sec / 3600, 1),
            "focus_pct": round(
                ((total_sec - distraction_sec) / total_sec * 100)
                if total_sec > 0 else 0, 1
            ),
            "sessions": session_count,
            "interventions": intervention_count,
            "last_active": last_event.timestamp.isoformat() if last_event else None,
        })

    return result


@router.get("/experiment-comparison")
def experiment_comparison(key: str, db: Session = Depends(get_db)):
    """Compare metrics across experiment groups."""
    verify_admin(key)

    groups = ["adaptive", "static_block", "control"]
    result = {}

    for group in groups:
        group_users = db.query(User).filter(User.experiment_group == group).all()
        user_ids = [u.id for u in group_users]

        if not user_ids:
            result[group] = {
                "user_count": 0,
                "avg_focus_pct": 0,
                "avg_hours_tracked": 0,
                "avg_sessions": 0,
                "avg_interventions": 0,
            }
            continue

        total_sec = (
            db.query(func.sum(BrowsingEvent.duration_seconds))
            .filter(BrowsingEvent.user_id.in_(user_ids))
            .scalar() or 0
        )

        distraction_sec = (
            db.query(func.sum(BrowsingEvent.duration_seconds))
            .filter(
                BrowsingEvent.user_id.in_(user_ids),
                BrowsingEvent.is_distraction == True,
            )
            .scalar() or 0
        )

        session_count = (
            db.query(StudySession)
            .filter(StudySession.user_id.in_(user_ids))
            .count()
        )

        intervention_count = (
            db.query(Intervention)
            .filter(Intervention.user_id.in_(user_ids))
            .count()
        )

        result[group] = {
            "user_count": len(user_ids),
            "avg_focus_pct": round(
                ((total_sec - distraction_sec) / total_sec * 100)
                if total_sec > 0 else 0, 1
            ),
            "total_hours_tracked": round(total_sec / 3600, 1),
            "avg_hours_per_user": round(total_sec / 3600 / len(user_ids), 1),
            "avg_sessions_per_user": round(session_count / len(user_ids), 1),
            "total_interventions": intervention_count,
        }

    return result


@router.get("/top-domains")
def top_domains(key: str, limit: int = 20, db: Session = Depends(get_db)):
    """Top domains across all users by time spent."""
    verify_admin(key)

    domains = (
        db.query(
            BrowsingEvent.domain,
            BrowsingEvent.is_distraction,
            func.sum(BrowsingEvent.duration_seconds).label("total_seconds"),
            func.count(BrowsingEvent.id).label("visit_count"),
            func.count(func.distinct(BrowsingEvent.user_id)).label("unique_users"),
        )
        .filter(BrowsingEvent.domain.isnot(None))
        .group_by(BrowsingEvent.domain, BrowsingEvent.is_distraction)
        .order_by(func.sum(BrowsingEvent.duration_seconds).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "domain": d.domain,
            "is_distraction": d.is_distraction,
            "total_hours": round(d.total_seconds / 3600, 2),
            "visits": d.visit_count,
            "unique_users": d.unique_users,
        }
        for d in domains
    ]
