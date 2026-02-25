"""Pattern Classifier — ML model for distraction pattern classification.

Uses scikit-learn to classify browsing sessions into behavioral
patterns and predict distraction risk.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

from ml.feature_extractor import extract_features, features_to_vector, feature_names


MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class PatternClassifier:
    """Classifies browsing sessions into behavioral patterns.

    Labels:
        - "focused": User is primarily on study/productive sites
        - "drifting": User is starting to drift toward distractions
        - "distracted": User is primarily on distracting content
        - "recovering": User is transitioning back from distraction

    Uses a Random Forest classifier trained on extracted behavioral features.
    """

    def __init__(self) -> None:
        self.model: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self._labels = ["focused", "drifting", "distracted", "recovering"]
        self._load_or_init()

    def _load_or_init(self):
        """Load saved model or initialize a new one."""
        model_path = MODEL_DIR / "pattern_model.pkl"
        scaler_path = MODEL_DIR / "pattern_scaler.pkl"

        if model_path.exists() and scaler_path.exists():
            try:
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
                with open(scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
                return
            except Exception:
                pass

        # Initialize fresh
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight="balanced",
        )
        self.scaler = StandardScaler()

    def predict(self, events: List[Dict]) -> Dict:
        """Predict the behavioral pattern for a set of events.

        Returns:
            {
                "pattern": str,           # One of the 4 labels
                "confidence": float,      # 0.0 - 1.0
                "probabilities": dict,    # Label → probability
                "features": dict,         # Extracted features
            }
        """
        features = extract_features(events)
        vector = features_to_vector(features).reshape(1, -1)

        if not hasattr(self.model, "classes_"):
            # Model not yet trained — use rule-based fallback
            return self._rule_based_predict(features)

        try:
            scaled = self.scaler.transform(vector)
            prediction = self.model.predict(scaled)[0]
            probabilities = self.model.predict_proba(scaled)[0]
            prob_dict = {
                label: round(float(p), 3)
                for label, p in zip(self.model.classes_, probabilities)
            }
            confidence = float(max(probabilities))

            return {
                "pattern": prediction,
                "confidence": round(confidence, 3),
                "probabilities": prob_dict,
                "features": features,
            }
        except Exception:
            return self._rule_based_predict(features)

    def train(
        self,
        event_sessions: List[List[Dict]],
        labels: List[str],
    ) -> Dict:
        """Train the classifier on labeled session data.

        Args:
            event_sessions: List of event lists (one per session)
            labels: Corresponding pattern labels

        Returns:
            Training metrics (accuracy, cross-val scores)
        """
        if len(event_sessions) < 5:
            return {"error": "Need at least 5 labeled sessions to train"}

        # Extract features for each session
        X = np.array([
            features_to_vector(extract_features(session))
            for session in event_sessions
        ])
        y = np.array(labels)

        # Scale features
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)

        # Train model
        self.model.fit(X_scaled, y)

        # Evaluate with cross-validation
        if len(event_sessions) >= 10:
            cv_scores = cross_val_score(
                self.model, X_scaled, y, cv=min(5, len(event_sessions)), scoring="accuracy"
            )
        else:
            cv_scores = np.array([0.0])

        # Save model
        self._save()

        return {
            "samples": len(event_sessions),
            "features": len(feature_names()),
            "accuracy_cv_mean": round(float(cv_scores.mean()), 3),
            "accuracy_cv_std": round(float(cv_scores.std()), 3),
            "classes": list(self.model.classes_),
            "feature_importances": {
                name: round(float(imp), 4)
                for name, imp in zip(
                    feature_names(),
                    self.model.feature_importances_,
                )
            },
        }

    def _save(self):
        """Persist model and scaler to disk."""
        with open(MODEL_DIR / "pattern_model.pkl", "wb") as f:
            pickle.dump(self.model, f)
        with open(MODEL_DIR / "pattern_scaler.pkl", "wb") as f:
            pickle.dump(self.scaler, f)

    def _rule_based_predict(self, features: Dict[str, float]) -> Dict:
        """Fallback rule-based classification when model isn't trained."""
        ratio = features.get("distraction_ratio", 0.0)
        streak = features.get("max_distraction_streak", 0.0)
        d2f = features.get("distraction_to_focus_transitions", 0.0)

        if ratio < 0.2:
            pattern = "focused"
            confidence = 0.7
        elif ratio < 0.4 and streak < 3:
            pattern = "drifting"
            confidence = 0.5
        elif ratio >= 0.6:
            pattern = "distracted"
            confidence = 0.7
        elif d2f > 2:
            pattern = "recovering"
            confidence = 0.5
        else:
            pattern = "drifting"
            confidence = 0.4

        return {
            "pattern": pattern,
            "confidence": confidence,
            "probabilities": {pattern: confidence},
            "features": features,
        }
