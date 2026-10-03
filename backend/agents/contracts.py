"""Typed contracts shared by the AdaptiFocus agent workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Classification = Literal["study", "distraction", "neutral"]
InterventionLevel = Literal["none", "nudge", "warn", "soft_block", "hard_block"]


class ContractModel(BaseModel):
    """Validated model with temporary mapping compatibility for API callers."""

    model_config = ConfigDict(extra="forbid")

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


class BrowsingEventInput(ContractModel):
    url: str | None = None
    domain: str | None = None
    title: str | None = None
    duration_seconds: int = Field(default=0, ge=0)
    timestamp: datetime | str | None = None
    is_distraction: bool = False
    category: str | None = None


class ContextInput(ContractModel):
    current_url: str | None = None
    current_title: str = ""
    current_domain: str | None = None
    study_topic: str | None = None
    session_active: bool = False
    recent_domains: list[str] = Field(default_factory=list)


class PatternInput(ContractModel):
    events: list[BrowsingEventInput] = Field(default_factory=list)


class InterventionInput(ContractModel):
    context_result: "ContextResult"
    pattern_result: "PatternResult"
    time_on_current_seconds: int = Field(default=0, ge=0)
    current_domain: str | None = None
    session_active: bool = False
    total_distraction_seconds_today: int = Field(default=0, ge=0)
    interventions_today: int = Field(default=0, ge=0)
    user_compliance_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    recent_dismiss_streak: int = Field(default=0, ge=0)


class PatternFinding(ContractModel):
    type: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    data: dict[str, Any] = Field(default_factory=dict)


class PatternResult(ContractModel):
    patterns: list[PatternFinding] = Field(default_factory=list)
    hourly_vulnerability: dict[int, float] = Field(default_factory=dict)
    domain_risk_scores: dict[str, float] = Field(default_factory=dict)
    distraction_chains: list[list[str]] = Field(default_factory=list)


class ContextResult(ContractModel):
    classification: Classification
    confidence: float = Field(ge=0.0, le=1.0)
    topic_relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    context_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    is_adult: bool = False


class InterventionProposal(ContractModel):
    should_intervene: bool
    level: InterventionLevel
    message: str = ""
    urgency: float = Field(ge=0.0, le=1.0)
    cooldown_seconds: int = Field(ge=0)


class CoordinatorInput(ContractModel):
    current_url: str | None = None
    current_title: str | None = None
    current_domain: str | None = None
    time_on_current_seconds: int = Field(default=0, ge=0)
    study_topic: str | None = None
    session_active: bool = False
    session_id: int | None = None
    recent_domains: list[str] = Field(default_factory=list)
    historical_events: list[BrowsingEventInput] = Field(default_factory=list)
    total_distraction_seconds_today: int = Field(default=0, ge=0)
    interventions_today: int = Field(default=0, ge=0)
    user_compliance_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    recent_dismiss_streak: int = Field(default=0, ge=0)


class CoordinatorResult(ContractModel):
    decision: InterventionProposal
    context: ContextResult
    patterns: PatternResult


InterventionInput.model_rebuild()
