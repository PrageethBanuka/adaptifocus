"""API routes for intervention decisions."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import BrowsingEvent, Intervention, StudySession
from api.models.schemas import InterventionRequest, InterventionResponse
from api.auth import require_user
from database.models import User
from agents.coordinator import CoordinatorAgent

router = APIRouter(prefix="/interventions", tags=["interventions"])

_coordinator = CoordinatorAgent()


@router.post("/check", response_model=InterventionResponse)
def check_intervention(
    request: InterventionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Check whether an intervention should be triggered for current browsing.

    Called periodically by the browser extension (e.g., every 10 seconds).
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Fetch today's events for pattern analysis for the CURRENT USER
    historical = (
        db.query(BrowsingEvent)
        .filter(BrowsingEvent.user_id == user.id)
        .filter(BrowsingEvent.timestamp >= today_start)
        .order_by(BrowsingEvent.timestamp.asc())
        .all()
    )

    historical_dicts = [
        {
            "url": e.url,
            "domain": e.domain,
            "title": e.title,
            "duration_seconds": e.duration_seconds,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "is_distraction": e.is_distraction,
            "category": e.category,
        }
        for e in historical
    ]

    # Recent domains for trajectory
    recent_domains = [e.domain for e in historical[-10:] if e.domain]

    # Total distraction today
    total_distraction_today = sum(
        e.duration_seconds for e in historical if e.is_distraction
    )

    # Interventions today for the CURRENT USER
    interventions_today = (
        db.query(Intervention)
        .filter(Intervention.user_id == user.id)
        .filter(Intervention.timestamp >= today_start)
        .count()
    )

    # Active study session
    session_active = False
    study_topic = None
    if request.session_id:
        session = db.query(StudySession).get(request.session_id)
        if session and session.is_active:
            session_active = True
            study_topic = session.study_topic

    # Run coordinator
    result = _coordinator.analyze({
        "current_url": request.current_url,
        "current_title": request.current_title,
        "current_domain": request.current_domain,
        "time_on_current_seconds": request.time_on_current_seconds,
        "study_topic": study_topic,
        "session_active": session_active,
        "session_id": request.session_id,
        "recent_domains": recent_domains,
        "historical_events": historical_dicts,
        "total_distraction_seconds_today": total_distraction_today,
        "interventions_today": interventions_today,
    })

    decision = result["decision"]

    # Record intervention if triggered
    if decision["should_intervene"]:
        intervention = Intervention(
            user_id=user.id,
            level=decision["level"],
            trigger_url=request.current_url,
            trigger_domain=request.current_domain,
            duration_on_distraction_seconds=request.time_on_current_seconds,
            session_id=request.session_id,
        )
        db.add(intervention)
        db.commit()

    return InterventionResponse(
        should_intervene=decision["should_intervene"],
        level=decision["level"],
        message=decision["message"],
        distraction_score=abs(result["context"].get("context_score", 0.0)),
        total_distraction_seconds=total_distraction_today,
    )


@router.post("/{intervention_id}/response")
def record_response(
    intervention_id: int,
    response: str,  # "dismissed", "complied", "overrode"
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Record the user's response to an intervention."""
    intervention = (
        db.query(Intervention)
        .filter(Intervention.id == intervention_id, Intervention.user_id == user.id)
        .first()
    )
    if not intervention:
        return {"error": "Intervention not found"}

    intervention.user_response = response
    intervention.was_effective = response == "complied"
    db.commit()

    return {"status": "recorded", "was_effective": intervention.was_effective}
