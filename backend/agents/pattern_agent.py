"""Pattern Agent — learns and detects individual distraction patterns.

This agent analyzes browsing history to discover behavioral patterns like:
- Time-of-day vulnerability windows (e.g., always distracted at 2-3 PM)
- Distraction chains (e.g., YouTube → Reddit → Instagram spiral)
- Domain-specific dwell times that correlate with loss of focus
- Pre-distraction triggers (visiting certain sites before going off-track)
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from agents.base_agent import BaseAgent


# Default known distraction domains
DISTRACTION_DOMAINS = {
    "youtube.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "tiktok.com", "reddit.com", "netflix.com",
    "hulu.com", "twitch.tv", "9gag.com", "buzzfeed.com",
}

# Default known productive domains
PRODUCTIVE_DOMAINS = {
    "github.com", "gitlab.com", "stackoverflow.com", "stackexchange.com",
    "docs.google.com", "notion.so", "scholar.google.com",
    "arxiv.org", "ieee.org", "acm.org", "medium.com",
}


def _extract_domain(url: Optional[str]) -> Optional[str]:
    """Extract bare domain from a URL."""
    if not url:
        return None
    try:
        host = urlparse(url).hostname or ""
        # Strip www. prefix
        if host.startswith("www."):
            host = host[4:]
        return host.lower() or None
    except Exception:
        return None


def _hour_bucket(timestamp: Optional[str]) -> Optional[int]:
    """Extract hour (0-23) from an ISO timestamp string."""
    if not timestamp:
        return None
    try:
        if isinstance(timestamp, datetime):
            return timestamp.hour
        dt = datetime.fromisoformat(str(timestamp))
        return dt.hour
    except Exception:
        return None


class PatternAgent(BaseAgent):
    """Discovers distraction patterns from browsing event history.

    Input data shape:
        {
            "events": [
                {
                    "url": str | None,
                    "domain": str | None,
                    "title": str | None,
                    "duration_seconds": int,
                    "timestamp": str | None,
                    "is_distraction": bool,
                    "category": str | None,
                }
            ]
        }

    Output:
        {
            "patterns": [
                {
                    "type": str,
                    "description": str,
                    "confidence": float,
                    "data": dict,
                }
            ],
            "hourly_vulnerability": dict[int, float],  # hour → distraction %
            "domain_risk_scores": dict[str, float],     # domain → risk 0-1
            "distraction_chains": list[list[str]],      # common site sequences
        }
    """

    @property
    def name(self) -> str:
        return "Pattern Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        events: List[Dict] = data.get("events", [])

        if not events:
            return {
                "patterns": [],
                "hourly_vulnerability": {},
                "domain_risk_scores": {},
                "distraction_chains": [],
            }

        patterns = []

        # ── 1. Hourly vulnerability analysis ─────────────────────────────
        hourly_vuln = self._analyze_hourly_vulnerability(events)
        vulnerable_hours = [
            h for h, score in hourly_vuln.items() if score > 0.5
        ]
        if vulnerable_hours:
            patterns.append({
                "type": "time_vulnerability",
                "description": (
                    f"High distraction risk during hours: "
                    f"{', '.join(f'{h}:00' for h in sorted(vulnerable_hours))}"
                ),
                "confidence": round(
                    sum(hourly_vuln[h] for h in vulnerable_hours) / len(vulnerable_hours),
                    3,
                ),
                "data": {"vulnerable_hours": sorted(vulnerable_hours)},
            })

        # ── 2. Domain risk scoring ───────────────────────────────────────
        domain_risks = self._analyze_domain_risks(events)
        high_risk_domains = [
            d for d, score in domain_risks.items() if score > 0.6
        ]
        if high_risk_domains:
            patterns.append({
                "type": "high_risk_domains",
                "description": (
                    f"These domains consistently lead to extended distraction: "
                    f"{', '.join(high_risk_domains[:5])}"
                ),
                "confidence": round(
                    sum(domain_risks[d] for d in high_risk_domains) / len(high_risk_domains),
                    3,
                ),
                "data": {d: domain_risks[d] for d in high_risk_domains[:10]},
            })

        # ── 3. Distraction chains ────────────────────────────────────────
        chains = self._detect_distraction_chains(events)
        if chains:
            patterns.append({
                "type": "distraction_chain",
                "description": (
                    f"Common distraction sequences detected: "
                    f"{' → '.join(chains[0]) if chains else 'none'}"
                ),
                "confidence": 0.7,
                "data": {"chains": chains[:5]},
            })

        # ── 4. Long dwell detection ──────────────────────────────────────
        long_dwell = self._detect_long_dwells(events)
        if long_dwell:
            patterns.append({
                "type": "long_dwell",
                "description": (
                    f"Excessive time on distracting sites: "
                    f"{', '.join(f'{d} ({s}s avg)' for d, s in long_dwell[:3])}"
                ),
                "confidence": 0.8,
                "data": {"domains": dict(long_dwell[:10])},
            })

        return {
            "patterns": patterns,
            "hourly_vulnerability": hourly_vuln,
            "domain_risk_scores": domain_risks,
            "distraction_chains": chains,
        }

    # ── Private analysis methods ─────────────────────────────────────────

    def _analyze_hourly_vulnerability(
        self, events: List[Dict]
    ) -> Dict[int, float]:
        """Compute per-hour distraction ratio (0.0 - 1.0)."""
        hour_total: Dict[int, int] = defaultdict(int)
        hour_distraction: Dict[int, int] = defaultdict(int)

        for ev in events:
            hour = _hour_bucket(ev.get("timestamp"))
            if hour is None:
                continue
            dur = max(0, int(ev.get("duration_seconds", 0)))
            hour_total[hour] += dur

            domain = ev.get("domain") or _extract_domain(ev.get("url"))
            if ev.get("is_distraction") or (domain and domain in DISTRACTION_DOMAINS):
                hour_distraction[hour] += dur

        result = {}
        for h in range(24):
            total = hour_total.get(h, 0)
            if total > 0:
                result[h] = round(hour_distraction.get(h, 0) / total, 3)
            else:
                result[h] = 0.0
        return result

    def _analyze_domain_risks(
        self, events: List[Dict]
    ) -> Dict[str, float]:
        """Score each domain by distraction risk (0.0 - 1.0)."""
        domain_total: Dict[str, int] = defaultdict(int)
        domain_distraction: Dict[str, int] = defaultdict(int)

        for ev in events:
            domain = ev.get("domain") or _extract_domain(ev.get("url"))
            if not domain:
                continue
            dur = max(0, int(ev.get("duration_seconds", 0)))
            domain_total[domain] += dur

            is_distr = ev.get("is_distraction") or domain in DISTRACTION_DOMAINS
            if is_distr:
                domain_distraction[domain] += dur

        result = {}
        for domain, total in domain_total.items():
            if total > 0:
                result[domain] = round(domain_distraction.get(domain, 0) / total, 3)
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def _detect_distraction_chains(
        self, events: List[Dict], min_chain_length: int = 2
    ) -> List[List[str]]:
        """Find common sequences of distraction sites visited back-to-back."""
        # Build ordered domain sequence (distractions only)
        sequence = []
        for ev in events:
            domain = ev.get("domain") or _extract_domain(ev.get("url"))
            is_distr = ev.get("is_distraction") or (
                domain and domain in DISTRACTION_DOMAINS
            )
            if is_distr and domain:
                sequence.append(domain)

        if len(sequence) < min_chain_length:
            return []

        # Extract bigrams and trigrams
        bigrams: Counter = Counter()
        trigrams: Counter = Counter()

        for i in range(len(sequence) - 1):
            pair = (sequence[i], sequence[i + 1])
            if pair[0] != pair[1]:  # ignore self-loops
                bigrams[pair] += 1

        for i in range(len(sequence) - 2):
            triple = (sequence[i], sequence[i + 1], sequence[i + 2])
            if len(set(triple)) > 1:
                trigrams[triple] += 1

        chains = []
        for triple, count in trigrams.most_common(5):
            if count >= 2:
                chains.append(list(triple))
        for pair, count in bigrams.most_common(5):
            if count >= 3:
                chains.append(list(pair))

        return chains

    def _detect_long_dwells(
        self, events: List[Dict], threshold_seconds: int = 120
    ) -> List[tuple]:
        """Find domains where average distraction session exceeds threshold."""
        domain_durations: Dict[str, List[int]] = defaultdict(list)

        for ev in events:
            domain = ev.get("domain") or _extract_domain(ev.get("url"))
            is_distr = ev.get("is_distraction") or (
                domain and domain in DISTRACTION_DOMAINS
            )
            if is_distr and domain:
                dur = max(0, int(ev.get("duration_seconds", 0)))
                domain_durations[domain].append(dur)

        long_dwells = []
        for domain, durations in domain_durations.items():
            avg = sum(durations) / len(durations) if durations else 0
            if avg >= threshold_seconds:
                long_dwells.append((domain, round(avg)))

        return sorted(long_dwells, key=lambda x: x[1], reverse=True)
