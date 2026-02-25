"""Tests for the multi-agent system."""

import pytest
from agents.pattern_agent import PatternAgent
from agents.context_agent import ContextAgent
from agents.intervention_agent import InterventionAgent
from agents.coordinator import CoordinatorAgent


# ── Sample data ──────────────────────────────────────────────────────────────

SAMPLE_EVENTS = [
    {
        "url": "https://github.com/user/repo",
        "domain": "github.com",
        "title": "My Repo - GitHub",
        "duration_seconds": 300,
        "timestamp": "2026-02-24T10:00:00",
        "is_distraction": False,
        "category": "study",
    },
    {
        "url": "https://youtube.com/watch?v=abc",
        "domain": "youtube.com",
        "title": "Funny Cat Videos",
        "duration_seconds": 180,
        "timestamp": "2026-02-24T10:05:00",
        "is_distraction": True,
        "category": "distraction",
    },
    {
        "url": "https://reddit.com/r/memes",
        "domain": "reddit.com",
        "title": "r/memes - Reddit",
        "duration_seconds": 120,
        "timestamp": "2026-02-24T10:08:00",
        "is_distraction": True,
        "category": "distraction",
    },
    {
        "url": "https://stackoverflow.com/questions/123",
        "domain": "stackoverflow.com",
        "title": "Python async await - Stack Overflow",
        "duration_seconds": 200,
        "timestamp": "2026-02-24T10:12:00",
        "is_distraction": False,
        "category": "study",
    },
    {
        "url": "https://arxiv.org/abs/2024.12345",
        "domain": "arxiv.org",
        "title": "Attention Mechanisms in NLP - arXiv",
        "duration_seconds": 400,
        "timestamp": "2026-02-24T10:16:00",
        "is_distraction": False,
        "category": "study",
    },
]


# ── Pattern Agent Tests ──────────────────────────────────────────────────────


class TestPatternAgent:
    def setup_method(self):
        self.agent = PatternAgent()

    def test_empty_events(self):
        result = self.agent.analyze({"events": []})
        assert result["patterns"] == []
        assert result["domain_risk_scores"] == {}
        assert result["distraction_chains"] == []

    def test_hourly_vulnerability(self):
        result = self.agent.analyze({"events": SAMPLE_EVENTS})
        vuln = result["hourly_vulnerability"]
        # Hour 10 has both study and distraction events
        assert 10 in vuln
        assert 0.0 <= vuln[10] <= 1.0

    def test_domain_risk_scoring(self):
        result = self.agent.analyze({"events": SAMPLE_EVENTS})
        risks = result["domain_risk_scores"]
        # YouTube should be high risk
        assert "youtube.com" in risks
        assert risks["youtube.com"] > 0.5
        # GitHub should be low risk
        if "github.com" in risks:
            assert risks["github.com"] < 0.5

    def test_patterns_detected(self):
        # Generate enough data for pattern detection
        events = SAMPLE_EVENTS * 5  # Repeat to have enough data
        result = self.agent.analyze({"events": events})
        assert isinstance(result["patterns"], list)

    def test_agent_name(self):
        assert self.agent.name == "Pattern Agent"


# ── Context Agent Tests ──────────────────────────────────────────────────────


class TestContextAgent:
    def setup_method(self):
        self.agent = ContextAgent()

    def test_study_domain(self):
        result = self.agent.analyze({
            "current_url": "https://github.com/user/repo",
            "current_title": "My Repository",
            "current_domain": "github.com",
            "study_topic": None,
            "session_active": False,
            "recent_domains": [],
        })
        assert result["classification"] == "study"
        assert result["confidence"] > 0

    def test_distraction_domain(self):
        result = self.agent.analyze({
            "current_url": "https://youtube.com/watch?v=cats",
            "current_title": "Funny Cat Compilation",
            "current_domain": "youtube.com",
            "study_topic": None,
            "session_active": False,
            "recent_domains": [],
        })
        assert result["classification"] == "distraction"
        assert result["confidence"] > 0

    def test_topic_relevance(self):
        result = self.agent.analyze({
            "current_url": "https://scholar.google.com",
            "current_title": "Machine Learning Research Papers",
            "current_domain": "scholar.google.com",
            "study_topic": "machine learning",
            "session_active": True,
            "recent_domains": [],
        })
        assert result["topic_relevance"] > 0
        assert result["classification"] == "study"

    def test_neutral_domain(self):
        result = self.agent.analyze({
            "current_url": "https://weather.com",
            "current_title": "Weather Forecast",
            "current_domain": "weather.com",
            "study_topic": None,
            "session_active": False,
            "recent_domains": [],
        })
        assert result["classification"] in ("neutral", "study", "distraction")

    def test_agent_name(self):
        assert self.agent.name == "Context Agent"


# ── Intervention Agent Tests ─────────────────────────────────────────────────


class TestInterventionAgent:
    def setup_method(self):
        self.agent = InterventionAgent()

    def test_no_intervention_for_study(self):
        result = self.agent.analyze({
            "context_result": {
                "classification": "study",
                "confidence": 0.8,
                "context_score": 0.7,
            },
            "pattern_result": {"domain_risk_scores": {}},
            "time_on_current_seconds": 60,
            "current_domain": "github.com",
            "session_active": True,
            "total_distraction_seconds_today": 0,
            "interventions_today": 0,
        })
        assert result["should_intervene"] is False
        assert result["level"] == "none"

    def test_nudge_for_short_distraction(self):
        result = self.agent.analyze({
            "context_result": {
                "classification": "distraction",
                "confidence": 0.8,
                "context_score": -0.7,
            },
            "pattern_result": {"domain_risk_scores": {"youtube.com": 0.9}},
            "time_on_current_seconds": 35,
            "current_domain": "youtube.com",
            "session_active": False,
            "total_distraction_seconds_today": 100,
            "interventions_today": 0,
        })
        assert result["should_intervene"] is True
        assert result["level"] == "nudge"

    def test_escalation_to_warn(self):
        result = self.agent.analyze({
            "context_result": {
                "classification": "distraction",
                "confidence": 0.9,
                "context_score": -0.8,
            },
            "pattern_result": {"domain_risk_scores": {"youtube.com": 0.9}},
            "time_on_current_seconds": 130,
            "current_domain": "youtube.com",
            "session_active": False,
            "total_distraction_seconds_today": 500,
            "interventions_today": 1,
        })
        assert result["should_intervene"] is True
        assert result["level"] == "warn"

    def test_session_mode_stricter(self):
        # During session, should trigger intervention faster
        result_no_session = self.agent.analyze({
            "context_result": {
                "classification": "distraction",
                "confidence": 0.8,
                "context_score": -0.7,
            },
            "pattern_result": {"domain_risk_scores": {}},
            "time_on_current_seconds": 25,
            "current_domain": "youtube.com",
            "session_active": False,
            "total_distraction_seconds_today": 0,
            "interventions_today": 0,
        })

        result_with_session = self.agent.analyze({
            "context_result": {
                "classification": "distraction",
                "confidence": 0.8,
                "context_score": -0.7,
            },
            "pattern_result": {"domain_risk_scores": {}},
            "time_on_current_seconds": 25,
            "current_domain": "youtube.com",
            "session_active": True,
            "total_distraction_seconds_today": 0,
            "interventions_today": 0,
        })

        # Session mode should be more likely to intervene
        if not result_no_session["should_intervene"]:
            assert result_with_session["should_intervene"] is True

    def test_agent_name(self):
        assert self.agent.name == "Intervention Agent"


# ── Coordinator Agent Tests ──────────────────────────────────────────────────


class TestCoordinatorAgent:
    def setup_method(self):
        self.agent = CoordinatorAgent()

    def test_full_pipeline(self):
        result = self.agent.analyze({
            "current_url": "https://youtube.com/watch?v=cats",
            "current_title": "Funny Cat Videos",
            "current_domain": "youtube.com",
            "time_on_current_seconds": 60,
            "study_topic": "algorithms",
            "session_active": True,
            "session_id": 1,
            "recent_domains": ["github.com", "youtube.com"],
            "historical_events": SAMPLE_EVENTS,
            "total_distraction_seconds_today": 300,
            "interventions_today": 0,
        })

        assert "decision" in result
        assert "context" in result
        assert "patterns" in result
        assert result["context"]["classification"] == "distraction"

    def test_study_context(self):
        result = self.agent.analyze({
            "current_url": "https://arxiv.org/abs/2024.12345",
            "current_title": "Research Paper on Algorithms",
            "current_domain": "arxiv.org",
            "time_on_current_seconds": 300,
            "study_topic": "algorithms",
            "session_active": True,
            "session_id": 1,
            "recent_domains": ["arxiv.org", "github.com"],
            "historical_events": SAMPLE_EVENTS,
            "total_distraction_seconds_today": 0,
            "interventions_today": 0,
        })

        assert result["decision"]["should_intervene"] is False
        assert result["context"]["classification"] == "study"

    def test_agent_list(self):
        assert len(self.agent.agents) == 3

    def test_agent_name(self):
        assert self.agent.name == "Coordinator Agent"
