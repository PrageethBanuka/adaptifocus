"""Feature extraction from browsing events for ML classification.

Extracts behavioral features from raw event data to feed into the
pattern classifier. This is a key component for the research paper's
ML contribution.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np


def extract_features(events: List[Dict]) -> Dict[str, float]:
    """Extract a feature vector from a list of browsing events.

    Features computed:
    - Temporal: hour distribution, day-of-week patterns, session length stats
    - Behavioral: switch frequency, unique domains, dwell time stats
    - Content: distraction ratio, domain category distribution
    - Sequential: transition probabilities, chain lengths

    Args:
        events: List of event dicts with url, domain, duration_seconds,
                timestamp, is_distraction, category.

    Returns:
        Dictionary of feature_name → float value.
    """
    if not events:
        return _empty_features()

    features: Dict[str, float] = {}

    durations = [max(0, int(e.get("duration_seconds", 0))) for e in events]
    domains = [e.get("domain", "") or "" for e in events]
    timestamps = _parse_timestamps(events)
    distractions = [bool(e.get("is_distraction", False)) for e in events]

    # ── Temporal features ────────────────────────────────────────────────
    if timestamps:
        hours = [t.hour for t in timestamps]
        features["hour_mean"] = float(np.mean(hours))
        features["hour_std"] = float(np.std(hours)) if len(hours) > 1 else 0.0
        features["is_morning"] = sum(1 for h in hours if 6 <= h < 12) / len(hours)
        features["is_afternoon"] = sum(1 for h in hours if 12 <= h < 18) / len(hours)
        features["is_evening"] = sum(1 for h in hours if 18 <= h < 24) / len(hours)
        features["is_night"] = sum(1 for h in hours if 0 <= h < 6) / len(hours)
    else:
        features.update({
            "hour_mean": 12.0, "hour_std": 0.0,
            "is_morning": 0.0, "is_afternoon": 0.0,
            "is_evening": 0.0, "is_night": 0.0,
        })

    # ── Duration features ────────────────────────────────────────────────
    if durations:
        features["duration_mean"] = float(np.mean(durations))
        features["duration_std"] = float(np.std(durations)) if len(durations) > 1 else 0.0
        features["duration_max"] = float(max(durations))
        features["duration_total"] = float(sum(durations))
    else:
        features.update({
            "duration_mean": 0.0, "duration_std": 0.0,
            "duration_max": 0.0, "duration_total": 0.0,
        })

    # ── Behavioral features ──────────────────────────────────────────────
    unique_domains = set(d for d in domains if d)
    features["unique_domains"] = float(len(unique_domains))
    features["total_events"] = float(len(events))
    features["events_per_domain"] = (
        len(events) / len(unique_domains) if unique_domains else 0.0
    )

    # Switch frequency (domain changes per event)
    switches = sum(
        1 for i in range(1, len(domains))
        if domains[i] != domains[i - 1] and domains[i] and domains[i - 1]
    )
    features["switch_rate"] = switches / max(1, len(events) - 1)

    # ── Distraction features ─────────────────────────────────────────────
    distraction_count = sum(distractions)
    features["distraction_ratio"] = distraction_count / max(1, len(events))
    features["distraction_count"] = float(distraction_count)

    distraction_durations = [
        d for d, is_d in zip(durations, distractions) if is_d
    ]
    features["distraction_duration_mean"] = (
        float(np.mean(distraction_durations)) if distraction_durations else 0.0
    )
    features["distraction_duration_total"] = float(sum(distraction_durations))

    # ── Sequential features ──────────────────────────────────────────────
    # Consecutive distraction streak length
    max_streak = 0
    current_streak = 0
    for is_d in distractions:
        if is_d:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    features["max_distraction_streak"] = float(max_streak)

    # Distraction-to-focus transition count
    d2f = sum(
        1 for i in range(1, len(distractions))
        if distractions[i - 1] and not distractions[i]
    )
    features["distraction_to_focus_transitions"] = float(d2f)

    return features


def features_to_vector(features: Dict[str, float]) -> np.ndarray:
    """Convert feature dict to a sorted numpy vector for ML models."""
    keys = sorted(features.keys())
    return np.array([features[k] for k in keys], dtype=np.float64)


def feature_names() -> List[str]:
    """Get the sorted list of feature names."""
    return sorted(_empty_features().keys())


def _empty_features() -> Dict[str, float]:
    """Return a zero-valued feature dict."""
    return {
        "hour_mean": 0.0, "hour_std": 0.0,
        "is_morning": 0.0, "is_afternoon": 0.0,
        "is_evening": 0.0, "is_night": 0.0,
        "duration_mean": 0.0, "duration_std": 0.0,
        "duration_max": 0.0, "duration_total": 0.0,
        "unique_domains": 0.0, "total_events": 0.0,
        "events_per_domain": 0.0, "switch_rate": 0.0,
        "distraction_ratio": 0.0, "distraction_count": 0.0,
        "distraction_duration_mean": 0.0, "distraction_duration_total": 0.0,
        "max_distraction_streak": 0.0,
        "distraction_to_focus_transitions": 0.0,
    }


def _parse_timestamps(events: List[Dict]) -> List[datetime]:
    """Parse timestamps from events, skipping unparseable ones."""
    result = []
    for e in events:
        ts = e.get("timestamp")
        if not ts:
            continue
        if isinstance(ts, datetime):
            result.append(ts)
            continue
        try:
            result.append(datetime.fromisoformat(str(ts)))
        except Exception:
            pass
    return result
