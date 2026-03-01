"""Context Agent — analyzes the current academic context of browsing.

This agent determines:
- Whether the current page is study-related or a distraction
- The relevance of the current page to the active study topic
- The academic productivity score for the current browsing session
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from functools import lru_cache

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

from agents.base_agent import BaseAgent


# ── Domain categories ────────────────────────────────────────────────────────

STUDY_DOMAINS = {
    # Academic
    "scholar.google.com", "arxiv.org", "ieee.org", "ieeexplore.ieee.org",
    "acm.org", "dl.acm.org", "researchgate.net", "semanticscholar.org",
    "sciencedirect.com", "springer.com", "jstor.org",
    # Development
    "github.com", "gitlab.com", "stackoverflow.com", "stackexchange.com",
    "developer.mozilla.org", "docs.python.org", "devdocs.io",
    # Productivity
    "docs.google.com", "sheets.google.com", "slides.google.com",
    "notion.so", "overleaf.com", "sharelatex.com",
    # Learning
    "coursera.org", "edx.org", "udemy.com", "khanacademy.org",
    "leetcode.com", "hackerrank.com", "geeksforgeeks.org",
    # University websites
    "mit.edu", "ocw.mit.edu", "stanford.edu", "harvard.edu",
    "ox.ac.uk", "cam.ac.uk", "berkeley.edu",
}

# These domains depend on CONTENT — title decides if it's study or not
MIXED_DOMAINS = {
    "youtube.com", "reddit.com", "medium.com", "quora.com",
    "twitter.com", "x.com",
}

DISTRACTION_DOMAINS = {
    "facebook.com", "instagram.com", "tiktok.com",
    "netflix.com", "hulu.com", "twitch.tv", "9gag.com",
    "buzzfeed.com", "disneyplus.com", "primevideo.com",
}

# Title keywords that suggest academic content
STUDY_KEYWORDS = [
    r"\b(algorithm|data\s*structure|machine\s*learning|deep\s*learning|neural\s*network)s?\b",
    r"\b(research|paper|thesis|dissertation|survey|abstract)s?\b",
    r"\b(programming|coding|software|developer|engineering)s?\b",
    r"\b(lecture|tutorial|course|lesson|class|assignment|homework|syllabus)s?\b",
    r"\b(database|network|security|system\s*design|architecture)s?\b",
    r"\b(python|java|javascript|typescript|c\+\+|rust|golang|react|node)s?\b",
    r"\b(ieee|acm|arxiv|conference|journal|proceedings)s?\b",
    r"\b(exam|quiz|test|study|review|notes|textbook)s?\b",
    r"\b(math|calculus|algebra|statistics|probability|physics|chemistry|biology)s?\b",
    r"\b(MIT|Stanford|Harvard|Oxford|Cambridge|Berkeley)\b",
    r"\b(CS\s?\d|6\.\d{3}|CS\d{2,3}|COMP\s?\d|EE\s?\d|MATH\s?\d)\b",  # Course numbers
    r"\b(introduction\s+to|fundamentals\s+of|principles\s+of|learn)\b",
    r"\b(how\s+to\s+(code|program|build|implement|solve|debug))s?\b",
    r"\b(documentation|docs|reference|guide|manual|handbook|API)s?\b",
    r"\b(open\s*courseware|OCW|MOOC|coursework|curriculum)s?\b",
    r"\b(analysis|computing|informatics|data\s*science|AI|NLP|CV)\b",
]

DISTRACTION_KEYWORDS = [
    r"\b(viral|meme|celebrity|gossip|prank|fails?|bloopers?)s?\b",
    r"\b(gaming|gameplay|twitch|lets?\s*play|walkthrough|speedrun)s?\b",
    r"\b(funny|comedy|entertainment|trending|react(ion)?s?)s?\b",
    r"\b(shopping|sale|discount|deal|coupon|unboxing)s?\b",
    r"\b(drama|reality\s*TV|vlog|mukbang|ASMR|compilation)s?\b",
    r"\b(shorts|reel|story|tiktok|snap)s?\b",
]

# Specifically block explicit adult content instantly
ADULT_DOMAINS = {
    "pornhub.com", "xvideos.com", "xnxx.com", "xhamster.com",
    "redtube.com", "youporn.com", "chaturbate.com", "onlyfans.com",
}

ADULT_KEYWORDS = [
    r"\b(porn|porno|pornography|xxx|nsfw|sex|camgirl|adult\s*video)s?\b",
]


def _extract_domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        host = urlparse(url).hostname or ""
        if host.startswith("www."):
            host = host[4:]
        return host.lower() or None
    except Exception:
        return None


class ContextAgent(BaseAgent):
    """Analyzes the academic context of current browsing activity.

    Input data shape:
        {
            "current_url": str | None,
            "current_title": str | None,
            "current_domain": str | None,
            "study_topic": str | None,       # Active study topic if any
            "session_active": bool,           # Is a study session running?
            "recent_domains": list[str],      # Last N domains visited
        }

    Output:
        {
            "classification": str,           # "study", "distraction", "neutral"
            "confidence": float,             # 0.0 - 1.0
            "topic_relevance": float,        # 0.0 - 1.0 (if study_topic set)
            "context_score": float,          # -1.0 (distraction) to 1.0 (focused)
            "reasons": list[str],            # Human-readable explanations
        }
    """

    @property
    def name(self) -> str:
        return "Context Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        url = data.get("current_url")
        title = data.get("current_title", "") or ""
        domain = data.get("current_domain") or _extract_domain(url)
        study_topic = data.get("study_topic")
        session_active = data.get("session_active", False)
        recent_domains = data.get("recent_domains", [])

        reasons: List[str] = []
        scores: List[float] = []

        # ── 1. Domain classification ─────────────────────────────────────
        domain_score = self._score_domain(domain)
        scores.append(domain_score)
        if domain_score > 0:
            reasons.append(f"Domain '{domain}' is associated with study/productivity")
        elif domain_score < 0:
            reasons.append(f"Domain '{domain}' is typically a distraction")

        # ── 2. Title keyword analysis (or LLM override) ──────────────────
        title_score = 0.0
        
        # If it's a mixed domain (like YouTube), ask Gemini to classify it
        if domain in MIXED_DOMAINS and genai and os.getenv("GEMINI_API_KEY"):
            llm_result = self._ask_gemini_classification(title)
            if llm_result == "distraction":
                title_score = -0.8
                reasons.append("AI determined the video/page content is entertainment or distracting")
            elif llm_result == "study":
                title_score = 0.8
                reasons.append("AI determined the video/page content is study or academic material")
            else:
                title_score = self._score_title_regex(title)
        else:
            # Traditional Regex fallback
            title_score = self._score_title_regex(title)
            
        scores.append(title_score)
        if title_score > 0 and "AI" not in reasons[-1] if reasons else True:
            reasons.append("Page title contains study-related keywords")
        elif title_score < 0 and "AI" not in reasons[-1] if reasons else True:
            reasons.append("Page title contains distraction-related keywords")

        # ── 3. Context override: title can flip domain classification ────
        # This is what makes AdaptiFocus smarter than domain blockers.
        # Example: YouTube + "MIT Linear Algebra Lecture" → study, not distraction
        if domain_score <= 0 and title_score > 0:
            # Any study keyword in title overrides distraction/mixed domain!
            override_bonus = 1.0 + title_score  # Scales with strength
            scores.append(override_bonus)
            reasons.append(
                f"Study content detected on '{domain}' — title suggests academic use"
            )
        elif domain_score >= 0 and title_score < 0:
            # Distraction content on a study/neutral domain
            override_penalty = -0.8 + title_score
            scores.append(override_penalty)
            reasons.append(
                f"Distraction content detected on '{domain}' — title suggests non-academic use"
            )

        # ── 4. Topic relevance ───────────────────────────────────────────
        topic_relevance = 0.0
        if study_topic and title:
            topic_relevance = self._compute_topic_relevance(study_topic, title)
            if topic_relevance > 0.3:
                # Strong topic match can also override domain classification
                relevance_boost = 0.8 if domain_score < 0 else 0.5
                scores.append(relevance_boost)
                reasons.append(
                    f"Page is relevant to study topic '{study_topic}'"
                )

        # ── 5. Session context penalty ───────────────────────────────────
        if session_active and domain_score < 0 and title_score <= 0:
            # Only penalize during sessions if title doesn't indicate study
            scores.append(-0.3)
            reasons.append("Distraction detected during an active study session")

        # ── 6. Recent browsing trajectory ────────────────────────────────
        trajectory_score = self._score_trajectory(recent_domains)
        if abs(trajectory_score) > 0.1:
            scores.append(trajectory_score * 0.5)
            if trajectory_score < 0:
                reasons.append("Recent browsing trend is shifting toward distractions")
            else:
                reasons.append("Recent browsing trend is focused on study content")

        # ── Aggregate ────────────────────────────────────────────────────
        is_adult = domain_score <= -2.0 or title_score <= -2.0
        if is_adult:
            context_score = -1.0
            classification = "distraction"
            confidence = 1.0
            if "Explicit/adult content detected" not in reasons:
                reasons.append("Explicit/adult content detected")
        else:
            context_score = sum(scores) / max(len(scores), 1)
            context_score = max(-1.0, min(1.0, context_score))  # Clamp

            if context_score > 0.2:
                classification = "study"
            elif context_score < -0.2:
                classification = "distraction"
            else:
                classification = "neutral"

            confidence = min(1.0, abs(context_score) * 1.5)

        return {
            "classification": classification,
            "confidence": round(confidence, 3),
            "topic_relevance": round(topic_relevance, 3),
            "context_score": round(context_score, 3),
            "reasons": reasons,
            "is_adult": is_adult,
        }

    # ── Private scoring methods ──────────────────────────────────────────

    def _score_domain(self, domain: Optional[str]) -> float:
        if not domain:
            return 0.0
        if domain in ADULT_DOMAINS:
            return -2.0  # Instant severe penalty
        if domain in STUDY_DOMAINS:
            return 0.8
        if domain in MIXED_DOMAINS:
            return 0.0  # Let title decide!
        if domain in DISTRACTION_DOMAINS:
            return -0.8
        # Check subdomains
        for dd in ADULT_DOMAINS:
            if domain.endswith(f".{dd}"):
                return -2.0
        for sd in STUDY_DOMAINS:
            if domain.endswith(f".{sd}"):
                return 0.6
        for md in MIXED_DOMAINS:
            if domain.endswith(f".{md}"):
                return 0.0
        for dd in DISTRACTION_DOMAINS:
            if domain.endswith(f".{dd}"):
                return -0.6
        return 0.0

        return 0.0

    @lru_cache(maxsize=500)
    def _ask_gemini_classification(self, title: str) -> str:
        """Use Gemini 2.0 Flash to semantically classify confusing titles (e.g. YouTube videos).
        LRU Cached out-of-the-box so repeating users/clicks do not hit the API twice.
        """
        if not title or len(title) < 5:
            return "neutral"
            
        try:
            client = genai.Client() # Picks up GEMINI_API_KEY from env
            prompt = (
                f"You are categorizing browsing history for a university student's productivity app. "
                f"Is the following video/page title strictly for studying/academics, strictly for entertainment/distraction "
                f"(like anime, video games, vlogs, memes), or neutral?\n\n"
                f"Title: \"{title}\"\n\n"
                f"Respond with EXACTLY ONE WORD from this list: [study, distraction, neutral]"
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=5,
                )
            )
            text = response.text.strip().lower()
            if "distraction" in text: return "distraction"
            if "study" in text: return "study"
            return "neutral"
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return "neutral"

    def _score_title_regex(self, title: str) -> float:
        if not title:
            return 0.0

        # Instant check for adult keywords
        for kw in ADULT_KEYWORDS:
            if re.search(kw, title, re.IGNORECASE):
                return -2.0

        study_hits = sum(
            1 for kw in STUDY_KEYWORDS if re.search(kw, title, re.IGNORECASE)
        )
        distraction_hits = sum(
            1 for kw in DISTRACTION_KEYWORDS
            if re.search(kw, title, re.IGNORECASE)
        )

        if study_hits > distraction_hits:
            return min(0.7, study_hits * 0.2)
        elif distraction_hits > study_hits:
            return max(-0.7, distraction_hits * -0.2)
        return 0.0

    def _compute_topic_relevance(self, topic: str, title: str) -> float:
        """Simple keyword overlap relevance score."""
        topic_words = set(topic.lower().split())
        title_words = set(title.lower().split())

        # Remove common stop words
        stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of",
                       "and", "or", "is", "it", "with", "-", "|", "—"}
        topic_words -= stop_words
        title_words -= stop_words

        if not topic_words:
            return 0.0

        overlap = topic_words & title_words
        return len(overlap) / len(topic_words)

    def _score_trajectory(self, recent_domains: List[str]) -> float:
        """Score the trajectory of recent browsing (last N domains)."""
        if not recent_domains:
            return 0.0

        scores = []
        for d in recent_domains[-5:]:  # Last 5 domains
            if d in STUDY_DOMAINS:
                scores.append(1.0)
            elif d in DISTRACTION_DOMAINS:
                scores.append(-1.0)
            else:
                scores.append(0.0)

        if not scores:
            return 0.0

        # Weight recent domains more heavily
        weighted = sum(s * (i + 1) for i, s in enumerate(scores))
        max_weight = sum(i + 1 for i in range(len(scores)))
        return weighted / max_weight if max_weight > 0 else 0.0
