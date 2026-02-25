"""Tests for the ML feature extraction pipeline."""

import pytest
from datetime import datetime

from ml.feature_extractor import extract_features, features_to_vector, feature_names


SAMPLE_EVENTS = [
    {
        "url": "https://github.com/user/repo",
        "domain": "github.com",
        "duration_seconds": 300,
        "timestamp": "2026-02-24T10:00:00",
        "is_distraction": False,
        "category": "study",
    },
    {
        "url": "https://youtube.com/watch?v=abc",
        "domain": "youtube.com",
        "duration_seconds": 180,
        "timestamp": "2026-02-24T10:05:00",
        "is_distraction": True,
        "category": "distraction",
    },
    {
        "url": "https://stackoverflow.com/q/123",
        "domain": "stackoverflow.com",
        "duration_seconds": 200,
        "timestamp": "2026-02-24T10:10:00",
        "is_distraction": False,
        "category": "study",
    },
]


class TestFeatureExtraction:
    def test_basic_extraction(self):
        features = extract_features(SAMPLE_EVENTS)
        assert isinstance(features, dict)
        assert len(features) > 0

    def test_empty_events(self):
        features = extract_features([])
        assert all(v == 0.0 for v in features.values())

    def test_distraction_ratio(self):
        features = extract_features(SAMPLE_EVENTS)
        # 1 out of 3 events is a distraction
        assert abs(features["distraction_ratio"] - 1/3) < 0.01

    def test_duration_features(self):
        features = extract_features(SAMPLE_EVENTS)
        assert features["duration_total"] == 680.0  # 300 + 180 + 200
        assert features["duration_max"] == 300.0

    def test_unique_domains(self):
        features = extract_features(SAMPLE_EVENTS)
        assert features["unique_domains"] == 3.0

    def test_vector_conversion(self):
        features = extract_features(SAMPLE_EVENTS)
        vector = features_to_vector(features)
        assert vector.shape == (len(features),)

    def test_feature_names_match(self):
        features = extract_features(SAMPLE_EVENTS)
        names = feature_names()
        assert set(names) == set(features.keys())

    def test_temporal_features(self):
        features = extract_features(SAMPLE_EVENTS)
        # All events are at 10 AM
        assert features["is_morning"] == 1.0
        assert features["is_afternoon"] == 0.0

    def test_switch_rate(self):
        features = extract_features(SAMPLE_EVENTS)
        # All 3 events have different domains, so 2 switches out of 2 possible
        assert features["switch_rate"] == 1.0
