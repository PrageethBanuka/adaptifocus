"""Coordinator Agent — orchestrates all sub-agents and produces unified decisions.

The Coordinator is the entry point for the multi-agent system. It:
1. Runs the Pattern Agent on historical data
2. Runs the Context Agent on the current browsing state
3. Feeds both results into the Intervention Agent
4. Returns a unified decision with all analysis combined
"""

from __future__ import annotations

from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from agents.contracts import CoordinatorInput, CoordinatorResult
from agents.pattern_agent import PatternAgent
from agents.context_agent import ContextAgent
from agents.intervention_agent import InterventionAgent


class CoordinatorAgent(BaseAgent[CoordinatorInput, CoordinatorResult]):
    """Orchestrates all agents and produces a unified analysis + decision.

    Input data shape:
        {
            "current_url": str | None,
            "current_title": str | None,
            "current_domain": str | None,
            "time_on_current_seconds": int,
            "study_topic": str | None,
            "session_active": bool,
            "session_id": int | None,
            "recent_domains": list[str],
            "historical_events": list[dict],  # For pattern analysis
            "total_distraction_seconds_today": int,
            "interventions_today": int,
        }

    Output:
        {
            "decision": {
                "should_intervene": bool,
                "level": str,
                "message": str,
                "urgency": float,
                "cooldown_seconds": int,
            },
            "context": {
                "classification": str,
                "confidence": float,
                "context_score": float,
                "topic_relevance": float,
                "reasons": list[str],
            },
            "patterns": {
                "patterns": list[dict],
                "hourly_vulnerability": dict,
                "domain_risk_scores": dict,
                "distraction_chains": list,
            },
        }
    """

    def __init__(self) -> None:
        self._pattern_agent = PatternAgent()
        self._context_agent = ContextAgent()
        self._intervention_agent = InterventionAgent()

    @property
    def name(self) -> str:
        return "Coordinator Agent"

    def analyze(self, data: CoordinatorInput | Dict[str, Any]) -> CoordinatorResult:
        data = CoordinatorInput.model_validate(data)
        # ── Step 1: Pattern analysis on historical data ──────────────────
        pattern_result = self._pattern_agent.analyze(
            {"events": data.historical_events}
        )

        # ── Step 2: Context analysis on current state ────────────────────
        context_result = self._context_agent.analyze(
            {
                "current_url": data.current_url,
                "current_title": data.current_title or "",
                "current_domain": data.current_domain,
                "study_topic": data.study_topic,
                "session_active": data.session_active,
                "recent_domains": data.recent_domains,
            }
        )

        # ── Step 3: Intervention decision ────────────────────────────────
        intervention_result = self._intervention_agent.analyze(
            {
                "context_result": context_result,
                "pattern_result": pattern_result,
                "time_on_current_seconds": data.time_on_current_seconds,
                "current_domain": data.current_domain,
                "session_active": data.session_active,
                "total_distraction_seconds_today": data.total_distraction_seconds_today,
                "interventions_today": data.interventions_today,
                "user_compliance_rate": data.user_compliance_rate,
                "recent_dismiss_streak": data.recent_dismiss_streak,
            }
        )

        return CoordinatorResult(
            decision=intervention_result,
            context=context_result,
            patterns=pattern_result,
        )

    @property
    def agents(self) -> List[BaseAgent]:
        """List of sub-agents managed by this coordinator."""
        return [
            self._pattern_agent,
            self._context_agent,
            self._intervention_agent,
        ]
