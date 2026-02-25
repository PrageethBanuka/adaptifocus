"""Intervention Agent — decides when and how to intervene.

This is the core novel contribution: graduated micro-interventions that
escalate based on distraction severity rather than binary blocking.

Levels:
    1. NUDGE — Subtle reminder overlay (e.g., "Still studying algorithms?")
    2. WARN — More prominent warning with focus stats
    3. SOFT_BLOCK — Overlay with 15s delay before allowing access
    4. HARD_BLOCK — Full page block requiring explicit override
"""

from __future__ import annotations

from typing import Any, Dict

from agents.base_agent import BaseAgent
from config import (
    NUDGE_THRESHOLD_SECONDS,
    WARN_THRESHOLD_SECONDS,
    SOFT_BLOCK_THRESHOLD_SECONDS,
    HARD_BLOCK_THRESHOLD_SECONDS,
)


# ── Nudge messages by level ──────────────────────────────────────────────────

NUDGE_MESSAGES = [
    "📚 Gentle reminder — you're in a study session. Ready to refocus?",
    "💡 Quick check-in: Is this helping you with your study goal?",
    "🎯 You started a focused session. Want to get back on track?",
]

WARN_MESSAGES = [
    "⚠️ You've been on a distracting site for {duration}. "
    "Your focus score is dropping.",
    "📉 Focus alert: {duration} on non-study content. "
    "Your study session goal is at risk.",
]

SOFT_BLOCK_MESSAGES = [
    "🛑 Extended distraction detected ({duration}). "
    "Take a breath — this page will be accessible in 15 seconds if you choose.",
    "⏸️ Focus pause: You've spent {duration} away from your study topic. "
    "Continuing in 15 seconds...",
]

HARD_BLOCK_MESSAGES = [
    "🚫 Maximum distraction threshold reached ({duration}). "
    "This site is blocked for the remainder of your study session. "
    "Click 'Override' if you genuinely need access.",
]


def _format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    remaining_secs = seconds % 60
    if remaining_secs == 0:
        return f"{minutes}m"
    return f"{minutes}m {remaining_secs}s"


class InterventionAgent(BaseAgent):
    """Decides the intervention level based on context and pattern analysis.

    Input data shape:
        {
            "context_result": {              # From ContextAgent
                "classification": str,
                "confidence": float,
                "context_score": float,
            },
            "pattern_result": {              # From PatternAgent
                "domain_risk_scores": dict,
                "hourly_vulnerability": dict,
            },
            "time_on_current_seconds": int,  # Time spent on current page
            "current_domain": str | None,
            "session_active": bool,
            "total_distraction_seconds_today": int,
            "interventions_today": int,       # How many already triggered
        }

    Output:
        {
            "should_intervene": bool,
            "level": str,                    # none, nudge, warn, soft_block, hard_block
            "message": str,
            "urgency": float,                # 0.0 - 1.0
            "cooldown_seconds": int,         # Wait before next check
        }
    """

    @property
    def name(self) -> str:
        return "Intervention Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        context = data.get("context_result", {})
        pattern = data.get("pattern_result", {})
        time_on_current = data.get("time_on_current_seconds", 0)
        current_domain = data.get("current_domain")
        session_active = data.get("session_active", False)
        total_distraction_today = data.get("total_distraction_seconds_today", 0)
        interventions_today = data.get("interventions_today", 0)

        classification = context.get("classification", "neutral")
        context_score = context.get("context_score", 0.0)
        confidence = context.get("confidence", 0.0)

        # ── No intervention needed for study/neutral content ─────────────
        if classification != "distraction" or confidence < 0.3:
            return {
                "should_intervene": False,
                "level": "none",
                "message": "",
                "urgency": 0.0,
                "cooldown_seconds": 30,
            }

        # ── Calculate adjusted thresholds based on patterns ──────────────
        domain_risk = pattern.get("domain_risk_scores", {}).get(
            current_domain, 0.5
        )

        # Higher-risk domains get tighter thresholds
        risk_multiplier = max(0.5, 1.0 - (domain_risk * 0.5))

        adjusted_nudge = int(NUDGE_THRESHOLD_SECONDS * risk_multiplier)
        adjusted_warn = int(WARN_THRESHOLD_SECONDS * risk_multiplier)
        adjusted_soft = int(SOFT_BLOCK_THRESHOLD_SECONDS * risk_multiplier)
        adjusted_hard = int(HARD_BLOCK_THRESHOLD_SECONDS * risk_multiplier)

        # ── Extra strictness during study sessions ───────────────────────
        if session_active:
            adjusted_nudge = int(adjusted_nudge * 0.7)
            adjusted_warn = int(adjusted_warn * 0.7)
            adjusted_soft = int(adjusted_soft * 0.7)
            adjusted_hard = int(adjusted_hard * 0.7)

        # ── Determine intervention level ─────────────────────────────────
        duration_str = _format_duration(time_on_current)

        if time_on_current >= adjusted_hard:
            level = "hard_block"
            message = HARD_BLOCK_MESSAGES[
                interventions_today % len(HARD_BLOCK_MESSAGES)
            ].format(duration=duration_str)
            urgency = 1.0
            cooldown = 0

        elif time_on_current >= adjusted_soft:
            level = "soft_block"
            message = SOFT_BLOCK_MESSAGES[
                interventions_today % len(SOFT_BLOCK_MESSAGES)
            ].format(duration=duration_str)
            urgency = 0.8
            cooldown = 15

        elif time_on_current >= adjusted_warn:
            level = "warn"
            message = WARN_MESSAGES[
                interventions_today % len(WARN_MESSAGES)
            ].format(duration=duration_str)
            urgency = 0.6
            cooldown = 30

        elif time_on_current >= adjusted_nudge:
            level = "nudge"
            message = NUDGE_MESSAGES[
                interventions_today % len(NUDGE_MESSAGES)
            ]
            urgency = 0.3
            cooldown = 60

        else:
            return {
                "should_intervene": False,
                "level": "none",
                "message": "",
                "urgency": 0.0,
                "cooldown_seconds": max(5, adjusted_nudge - time_on_current),
            }

        return {
            "should_intervene": True,
            "level": level,
            "message": message,
            "urgency": urgency,
            "cooldown_seconds": cooldown,
        }
