"""End-to-end ML training pipeline for AdaptiFocus.

Downloads a real Kaggle dataset, extracts features, trains the classifier,
evaluates accuracy, and saves the model for production use.

Usage:
    python -m ml.train_pipeline                    # Use synthetic data from DB
    python -m ml.train_pipeline --kaggle           # Download + use Kaggle data
    python -m ml.train_pipeline --csv data/my.csv  # Use custom CSV
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

from ml.feature_extractor import extract_features, features_to_vector, feature_names
from ml.pattern_classifier import PatternClassifier


def load_events_from_db(days: int = 30) -> List[Dict]:
    """Load browsing events from the SQLite database."""
    from database.db import init_db, SessionLocal
    from database.models import BrowsingEvent

    init_db()
    db = SessionLocal()

    since = datetime.utcnow() - timedelta(days=days)
    events = db.query(BrowsingEvent).filter(
        BrowsingEvent.timestamp >= since
    ).all()

    result = [
        {
            "url": e.url,
            "domain": e.domain,
            "title": e.title,
            "duration_seconds": e.duration_seconds,
            "timestamp": e.timestamp.isoformat() if e.timestamp else "",
            "is_distraction": e.is_distraction,
            "category": e.category or "",
        }
        for e in events
    ]
    db.close()
    return result


def load_events_from_csv(filepath: str) -> List[Dict]:
    """Load events from a CSV file using the real_dataset_loader."""
    from ml.real_dataset_loader import load_custom_csv
    return load_custom_csv(filepath)


def create_sessions(events: List[Dict], window_minutes: int = 30) -> List[Tuple[List[Dict], str]]:
    """Segment events into sessions and label each session.

    A session is a contiguous group of events within `window_minutes`.
    Label is based on the dominant category in the session.
    """
    if not events:
        return []

    # Sort by timestamp
    sorted_events = sorted(events, key=lambda e: e.get("timestamp", ""))

    sessions = []
    current_session: List[Dict] = [sorted_events[0]]

    for e in sorted_events[1:]:
        try:
            prev_ts = datetime.fromisoformat(current_session[-1]["timestamp"])
            curr_ts = datetime.fromisoformat(e["timestamp"])
            gap = (curr_ts - prev_ts).total_seconds() / 60
        except Exception:
            gap = 0

        if gap > window_minutes:
            # New session
            sessions.append(current_session)
            current_session = [e]
        else:
            current_session.append(e)

    if current_session:
        sessions.append(current_session)

    # Label each session
    labeled = []
    for session in sessions:
        if len(session) < 3:
            continue  # Skip very short sessions

        distraction_count = sum(1 for e in session if e.get("is_distraction", False))
        ratio = distraction_count / len(session)

        # Check for recovery pattern (distraction → focus transition)
        transitions = sum(
            1 for i in range(1, len(session))
            if session[i - 1].get("is_distraction") and not session[i].get("is_distraction")
        )

        if ratio < 0.2:
            label = "focused"
        elif ratio < 0.4:
            label = "drifting"
        elif transitions >= 2 and ratio < 0.6:
            label = "recovering"
        else:
            label = "distracted"

        labeled.append((session, label))

    return labeled


def train_and_evaluate(
    sessions: List[Tuple[List[Dict], str]],
    test_size: float = 0.2,
) -> Dict:
    """Train the classifier and evaluate on a held-out test set."""
    if len(sessions) < 10:
        print(f"Warning: Only {len(sessions)} sessions. Need at least 10 for reliable training.")
        if len(sessions) < 5:
            return {"error": f"Only {len(sessions)} sessions, need >= 5"}

    event_lists = [s[0] for s in sessions]
    labels = [s[1] for s in sessions]

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        event_lists, labels, test_size=test_size, random_state=42, stratify=labels if len(set(labels)) > 1 else None,
    )

    # Train
    classifier = PatternClassifier()
    train_metrics = classifier.train(X_train, y_train)
    print(f"\n--- Training Metrics ---")
    print(f"Samples:      {train_metrics.get('samples', 0)}")
    print(f"Features:     {train_metrics.get('features', 0)}")
    print(f"CV Accuracy:  {train_metrics.get('accuracy_cv_mean', 0):.3f} ± {train_metrics.get('accuracy_cv_std', 0):.3f}")

    # Feature importances
    importances = train_metrics.get("feature_importances", {})
    if importances:
        sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\nTop 5 features:")
        for name, imp in sorted_imp:
            print(f"  {name}: {imp:.4f}")

    # Evaluate on test set
    print(f"\n--- Test Set Evaluation ({len(X_test)} sessions) ---")
    y_pred = [classifier.predict(events)["pattern"] for events in X_test]

    report = classification_report(y_test, y_pred, zero_division=0)
    print(report)

    cm = confusion_matrix(y_test, y_pred, labels=sorted(set(y_test)))
    print(f"Confusion Matrix:\n{cm}")

    return {
        "train_metrics": train_metrics,
        "test_samples": len(X_test),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }


def download_kaggle_dataset() -> str:
    """Download a real browsing dataset from Kaggle.

    Requires: pip install kaggle (and Kaggle API key configured)
    Falls back to generating enhanced synthetic data if Kaggle unavailable.
    """
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    csv_path = data_dir / "kaggle_browser_history.csv"

    if csv_path.exists():
        print(f"Using cached dataset: {csv_path}")
        return str(csv_path)

    try:
        import subprocess
        print("Downloading Browser History dataset from Kaggle...")
        subprocess.run([
            "kaggle", "datasets", "download",
            "-d", "saloni1712/browser-history",
            "-p", str(data_dir),
            "--unzip",
        ], check=True, capture_output=True)
        # Find the downloaded CSV
        for f in data_dir.glob("*.csv"):
            if "browser" in f.name.lower() or "history" in f.name.lower():
                f.rename(csv_path)
                return str(csv_path)
    except Exception as e:
        print(f"Kaggle download failed ({e}). Using synthetic dataset instead.")

    # Fallback: generate enhanced synthetic data
    print("Generating enhanced synthetic dataset for training...")
    from ml.dataset_generator import generate_dataset, export_csv
    import random
    random.seed(42)
    events = generate_dataset(days=30)
    export_csv(events, "data/kaggle_browser_history.csv")
    return str(csv_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train AdaptiFocus ML pipeline")
    parser.add_argument("--kaggle", action="store_true", help="Download + use Kaggle dataset")
    parser.add_argument("--csv", type=str, help="Path to custom CSV dataset")
    parser.add_argument("--days", type=int, default=30, help="Days of DB data to use")
    parser.add_argument("--window", type=int, default=30, help="Session window (minutes)")
    args = parser.parse_args()

    print("=" * 60)
    print("  AdaptiFocus ML Training Pipeline")
    print("=" * 60)

    # Load events
    if args.csv:
        print(f"\nLoading from CSV: {args.csv}")
        events = load_events_from_csv(args.csv)
    elif args.kaggle:
        csv_path = download_kaggle_dataset()
        from ml.real_dataset_loader import load_browser_history
        events = load_browser_history(csv_path)
    else:
        print(f"\nLoading from database (last {args.days} days)...")
        events = load_events_from_db(args.days)

    print(f"Loaded {len(events)} events")
    print(f"  Distraction: {sum(1 for e in events if e.get('is_distraction'))} ({sum(1 for e in events if e.get('is_distraction'))/max(len(events),1)*100:.1f}%)")
    print(f"  Domains: {len(set(e.get('domain', '') for e in events))}")

    # Create sessions
    print(f"\nSegmenting into sessions (window={args.window}min)...")
    sessions = create_sessions(events, window_minutes=args.window)
    print(f"Created {len(sessions)} sessions")

    # Label distribution
    from collections import Counter
    label_counts = Counter(s[1] for s in sessions)
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")

    # Train and evaluate
    results = train_and_evaluate(sessions)

    if "error" not in results:
        print(f"\n{'=' * 60}")
        print("  Training complete! Model saved to data/models/")
        print(f"{'=' * 60}")
    else:
        print(f"\nTraining failed: {results['error']}")
