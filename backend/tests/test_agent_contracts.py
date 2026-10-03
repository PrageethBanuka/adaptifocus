"""Tests for typed multi-agent contracts."""

import pytest
from pydantic import ValidationError

from agents.contracts import ContextResult, InterventionProposal
from agents.coordinator import CoordinatorAgent


def test_context_result_validates_score_ranges():
    with pytest.raises(ValidationError):
        ContextResult(
            classification="study",
            confidence=1.2,
            context_score=0.5,
        )


def test_intervention_proposal_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        InterventionProposal(
            should_intervene=False,
            level="none",
            urgency=0.0,
            cooldown_seconds=30,
            unexpected_field=True,
        )


def test_contracts_keep_legacy_read_access_during_migration():
    result = ContextResult(
        classification="study",
        confidence=0.9,
        context_score=0.8,
    )

    assert result["classification"] == "study"
    assert result.get("missing", "fallback") == "fallback"
    assert "classification" in result


def test_coordinator_normalizes_missing_title():
    result = CoordinatorAgent().analyze({"current_title": None})

    assert result.context.classification in {"study", "distraction", "neutral"}
