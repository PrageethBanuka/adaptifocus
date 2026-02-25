"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Events ───────────────────────────────────────────────────────────────────


class EventCreate(BaseModel):
    """Schema for submitting a browsing event from the extension."""

    url: Optional[str] = None
    domain: Optional[str] = None
    title: Optional[str] = None
    duration_seconds: int = Field(ge=0, default=0)
    category: Optional[str] = None
    session_id: Optional[int] = None
    timestamp: Optional[datetime] = None


class EventResponse(BaseModel):
    """Schema for returning a browsing event."""

    id: int
    timestamp: datetime
    url: Optional[str]
    domain: Optional[str]
    title: Optional[str]
    duration_seconds: int
    is_distraction: bool
    distraction_score: float
    category: Optional[str]
    session_id: Optional[int]

    model_config = {"from_attributes": True}


# ── Interventions ────────────────────────────────────────────────────────────


class InterventionRequest(BaseModel):
    """Request to check if an intervention should be triggered."""

    current_url: Optional[str] = None
    current_domain: Optional[str] = None
    current_title: Optional[str] = None
    time_on_current_seconds: int = 0
    session_id: Optional[int] = None


class InterventionResponse(BaseModel):
    """Response with intervention decision."""

    should_intervene: bool
    level: str = "none"  # none, nudge, warn, soft_block, hard_block
    message: str = ""
    distraction_score: float = 0.0
    total_distraction_seconds: int = 0


# ── Study Sessions ───────────────────────────────────────────────────────────


class SessionCreate(BaseModel):
    """Schema for starting a new study session."""

    study_topic: Optional[str] = None
    planned_duration_minutes: int = 45


class SessionResponse(BaseModel):
    """Schema for returning study session info."""

    id: int
    started_at: datetime
    ended_at: Optional[datetime]
    study_topic: Optional[str]
    planned_duration_minutes: int
    actual_focus_seconds: int
    actual_distraction_seconds: int
    is_active: bool

    model_config = {"from_attributes": True}


class SessionEndRequest(BaseModel):
    """Schema for ending a study session."""

    session_id: int


# ── Analytics ────────────────────────────────────────────────────────────────


class FocusSummary(BaseModel):
    """Summary statistics for dashboard."""

    total_events: int = 0
    distraction_events: int = 0
    total_seconds: int = 0
    focus_seconds: int = 0
    distraction_seconds: int = 0
    focus_percentage: float = 0.0
    top_distracting_domains: list[dict] = []
    top_productive_domains: list[dict] = []
    interventions_today: int = 0
    intervention_success_rate: float = 0.0


class PatternResponse(BaseModel):
    """A discovered behavioral pattern."""

    pattern_type: str
    description: Optional[str]
    confidence: float
    discovered_at: datetime

    model_config = {"from_attributes": True}
