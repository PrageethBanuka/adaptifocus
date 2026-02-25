"""Synthetic browsing dataset generator for AdaptiFocus.

Generates realistic browsing event data simulating a university student's
typical daily browsing patterns — mixing study sessions with distraction
episodes, time-of-day patterns, and distraction chains.

Usage:
    python -m ml.dataset_generator            # Generate & seed DB
    python -m ml.dataset_generator --csv      # Export to CSV
    python -m ml.dataset_generator --days 30  # Generate 30 days
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# ── Browsing behavior profiles ───────────────────────────────────────────────

STUDY_SITES = [
    ("github.com", "Pull Request #42 - MyProject", "study", (60, 600)),
    ("stackoverflow.com", "Python async await explained - Stack Overflow", "study", (30, 300)),
    ("arxiv.org", "Attention Is All You Need - arXiv", "study", (120, 900)),
    ("scholar.google.com", "Search results - Google Scholar", "study", (30, 180)),
    ("docs.python.org", "asyncio — Python documentation", "study", (60, 400)),
    ("developer.mozilla.org", "JavaScript Guide - MDN Web Docs", "study", (45, 350)),
    ("leetcode.com", "Two Sum - LeetCode", "study", (120, 1200)),
    ("geeksforgeeks.org", "Binary Search Tree - GeeksforGeeks", "study", (60, 480)),
    ("overleaf.com", "Research Paper Draft - Overleaf", "study", (180, 1800)),
    ("notion.so", "Study Notes - Notion", "study", (60, 600)),
    ("coursera.org", "Machine Learning by Andrew Ng - Coursera", "study", (300, 3600)),
    ("ieeexplore.ieee.org", "Digital Wellbeing Framework - IEEE", "study", (120, 600)),
    ("docs.google.com", "Group Project Report - Google Docs", "study", (120, 900)),
    ("slides.google.com", "Presentation Slides - Google Slides", "study", (60, 600)),
    ("hackerrank.com", "Data Structures Challenge - HackerRank", "study", (120, 900)),
]

DISTRACTION_SITES = [
    ("youtube.com", "Funny Cat Compilation 2026", "distraction", (30, 1200)),
    ("youtube.com", "Top 10 Gaming Moments", "distraction", (60, 1800)),
    ("youtube.com", "Music Mix - Lofi Hip Hop", "distraction", (120, 3600)),
    ("reddit.com", "r/programming - Reddit", "distraction", (30, 600)),
    ("reddit.com", "r/memes - Reddit", "distraction", (30, 900)),
    ("twitter.com", "Home / X", "distraction", (15, 600)),
    ("instagram.com", "Instagram", "distraction", (15, 480)),
    ("tiktok.com", "For You - TikTok", "distraction", (30, 900)),
    ("facebook.com", "Facebook", "distraction", (30, 600)),
    ("netflix.com", "Trending Now - Netflix", "distraction", (60, 3600)),
    ("twitch.tv", "Live Stream - Twitch", "distraction", (60, 1800)),
    ("9gag.com", "Trending - 9GAG", "distraction", (15, 300)),
    ("buzzfeed.com", "Trending - BuzzFeed", "distraction", (15, 300)),
]

NEUTRAL_SITES = [
    ("google.com", "Google Search", "neutral", (5, 30)),
    ("gmail.com", "Inbox - Gmail", "neutral", (15, 180)),
    ("weather.com", "Weather Forecast", "neutral", (5, 30)),
    ("maps.google.com", "Google Maps", "neutral", (10, 60)),
    ("amazon.com", "Amazon.com", "neutral", (30, 300)),
    ("wikipedia.org", "Wikipedia", "neutral", (30, 300)),
]

# ── Time-of-day behavior patterns ────────────────────────────────────────────
# (hour_range, study_probability, distraction_probability)

TIME_PATTERNS = [
    ((6, 8),   0.3, 0.5),    # Early morning: moderate study, checking phone
    ((8, 10),  0.7, 0.15),   # Morning class time: high study
    ((10, 12), 0.6, 0.25),   # Late morning: study with breaks
    ((12, 13), 0.2, 0.6),    # Lunch: mostly distraction
    ((13, 15), 0.65, 0.2),   # Early afternoon: focused study
    ((15, 17), 0.4, 0.4),    # Late afternoon: 50/50 — vulnerability window
    ((17, 19), 0.3, 0.5),    # Evening: winding down
    ((19, 21), 0.5, 0.35),   # Night study: moderate
    ((21, 23), 0.25, 0.6),   # Late night: high distraction
    ((23, 6),  0.1, 0.7),    # Very late: mostly distraction
]

# ── Distraction chain patterns ───────────────────────────────────────────────

DISTRACTION_CHAINS = [
    ["youtube.com", "reddit.com", "instagram.com"],
    ["twitter.com", "youtube.com", "tiktok.com"],
    ["reddit.com", "youtube.com", "twitch.tv"],
    ["instagram.com", "tiktok.com", "youtube.com"],
    ["facebook.com", "instagram.com", "youtube.com"],
]


def _get_time_pattern(hour: int) -> Tuple[float, float]:
    """Get study/distraction probability for a given hour."""
    for (start, end), study_p, distract_p in TIME_PATTERNS:
        if start <= hour < end or (start > end and (hour >= start or hour < end)):
            return study_p, distract_p
    return 0.4, 0.4


def _pick_site(category: str) -> Tuple[str, str, str, Tuple[int, int]]:
    """Pick a random site from the given category."""
    if category == "study":
        return random.choice(STUDY_SITES)
    elif category == "distraction":
        return random.choice(DISTRACTION_SITES)
    else:
        return random.choice(NEUTRAL_SITES)


def generate_day(
    date: datetime,
    active_hours: Tuple[int, int] = (7, 23),
    events_per_hour: Tuple[int, int] = (3, 8),
    study_sessions: int = 2,
) -> List[Dict]:
    """Generate browsing events for a single day.

    Simulates realistic patterns:
    - Time-of-day influenced study/distraction ratio
    - Study sessions with focused periods
    - Random distraction chains
    - Varying dwell times
    """
    events = []
    current_time = date.replace(
        hour=active_hours[0],
        minute=random.randint(0, 30),
        second=0,
        microsecond=0,
    )
    end_time = date.replace(hour=active_hours[1], minute=0, second=0)

    # Plan study session windows
    session_starts = []
    session_hours = sorted(random.sample(
        range(active_hours[0] + 1, active_hours[1] - 2),
        min(study_sessions, active_hours[1] - active_hours[0] - 3),
    ))
    for sh in session_hours:
        session_starts.append(date.replace(hour=sh, minute=random.randint(0, 15)))

    in_distraction_chain = False
    chain_sites: List[str] = []
    chain_index = 0

    while current_time < end_time:
        hour = current_time.hour
        study_p, distract_p = _get_time_pattern(hour)

        # Check if in a study session window (boost study probability)
        in_session = any(
            s <= current_time <= s + timedelta(minutes=random.randint(30, 60))
            for s in session_starts
        )
        if in_session:
            study_p = min(0.85, study_p + 0.3)
            distract_p = max(0.05, distract_p - 0.2)

        # Distraction chain logic
        if in_distraction_chain and chain_index < len(chain_sites):
            domain = chain_sites[chain_index]
            # Find matching site
            matches = [s for s in DISTRACTION_SITES if s[0] == domain]
            site = random.choice(matches) if matches else random.choice(DISTRACTION_SITES)
            chain_index += 1
            if chain_index >= len(chain_sites):
                in_distraction_chain = False
        else:
            # Normal category selection
            roll = random.random()
            if roll < study_p:
                category = "study"
            elif roll < study_p + distract_p:
                category = "distraction"
                # 20% chance to start a chain
                if random.random() < 0.2:
                    chain_sites = list(random.choice(DISTRACTION_CHAINS))
                    in_distraction_chain = True
                    chain_index = 0
                    domain = chain_sites[0]
                    matches = [s for s in DISTRACTION_SITES if s[0] == domain]
                    site = random.choice(matches) if matches else random.choice(DISTRACTION_SITES)
                    chain_index = 1
                    category = "_chain"  # flag to skip normal pick
            else:
                category = "neutral"

            if category != "_chain":
                site = _pick_site(category)

        domain, title, cat, (min_dur, max_dur) = site

        # Duration with some randomness
        duration = random.randint(min_dur, max_dur)

        # Add slight title variation
        if random.random() < 0.3:
            title = title + f" ({random.choice(['Part 2', 'Continued', 'Updated', '#' + str(random.randint(1, 99))])})"

        events.append({
            "url": f"https://{domain}/page_{random.randint(1000, 9999)}",
            "domain": domain,
            "title": title,
            "duration_seconds": duration,
            "timestamp": current_time.isoformat(),
            "is_distraction": cat == "distraction",
            "category": cat if cat != "_chain" else "distraction",
            "session_id": None,
        })

        # Advance time
        gap = random.randint(5, 120)  # 5s to 2min between events
        current_time += timedelta(seconds=duration + gap)

    return events


def generate_dataset(
    days: int = 14,
    start_date: datetime | None = None,
) -> List[Dict]:
    """Generate a full synthetic dataset spanning multiple days.

    Args:
        days: Number of days to simulate
        start_date: Starting date (defaults to N days ago)

    Returns:
        List of all generated events
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=days)

    all_events = []

    for day_offset in range(days):
        date = start_date + timedelta(days=day_offset)

        # Skip some weekend hours or add variety
        is_weekend = date.weekday() >= 5
        study_sessions = random.randint(1, 2) if is_weekend else random.randint(2, 4)
        start_hour = random.randint(9, 11) if is_weekend else random.randint(7, 8)
        end_hour = random.randint(20, 22) if is_weekend else random.randint(21, 23)

        day_events = generate_day(
            date,
            active_hours=(start_hour, end_hour),
            study_sessions=study_sessions,
        )
        all_events.extend(day_events)

    return all_events


def seed_database(events: List[Dict]) -> int:
    """Seed the SQLite database with generated events."""
    from database.db import init_db, SessionLocal
    from database.models import BrowsingEvent

    init_db()
    db = SessionLocal()

    count = 0
    try:
        for ev in events:
            db_event = BrowsingEvent(
                timestamp=datetime.fromisoformat(ev["timestamp"]),
                url=ev["url"],
                domain=ev["domain"],
                title=ev["title"],
                duration_seconds=ev["duration_seconds"],
                is_distraction=ev["is_distraction"],
                distraction_score=0.8 if ev["is_distraction"] else 0.1,
                category=ev["category"],
                session_id=ev.get("session_id"),
            )
            db.add(db_event)
            count += 1

        db.commit()
    finally:
        db.close()

    return count


def export_csv(events: List[Dict], path: str = "data/synthetic_dataset.csv"):
    """Export events to CSV for analysis."""
    filepath = Path(__file__).resolve().parent.parent / path
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "url", "domain", "title",
            "duration_seconds", "is_distraction", "category",
        ])
        writer.writeheader()
        for ev in events:
            writer.writerow({k: ev[k] for k in writer.fieldnames})

    return str(filepath)


def print_stats(events: List[Dict]):
    """Print dataset statistics."""
    total = len(events)
    distraction_count = sum(1 for e in events if e["is_distraction"])
    study_count = sum(1 for e in events if e["category"] == "study")
    neutral_count = total - distraction_count - study_count

    total_duration = sum(e["duration_seconds"] for e in events)
    distraction_duration = sum(
        e["duration_seconds"] for e in events if e["is_distraction"]
    )

    domains = set(e["domain"] for e in events)

    days = set(e["timestamp"][:10] for e in events)

    print("\n" + "=" * 50)
    print("  AdaptiFocus Synthetic Dataset Statistics")
    print("=" * 50)
    print(f"  Days simulated:      {len(days)}")
    print(f"  Total events:        {total}")
    print(f"  Study events:        {study_count} ({study_count/total*100:.1f}%)")
    print(f"  Distraction events:  {distraction_count} ({distraction_count/total*100:.1f}%)")
    print(f"  Neutral events:      {neutral_count} ({neutral_count/total*100:.1f}%)")
    print(f"  Unique domains:      {len(domains)}")
    print(f"  Total duration:      {total_duration//3600}h {(total_duration%3600)//60}m")
    print(f"  Distraction time:    {distraction_duration//3600}h {(distraction_duration%3600)//60}m")
    print(f"  Focus percentage:    {(1 - distraction_duration/total_duration)*100:.1f}%")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic browsing dataset")
    parser.add_argument("--days", type=int, default=14, help="Days to simulate")
    parser.add_argument("--csv", action="store_true", help="Export to CSV")
    parser.add_argument("--no-seed", action="store_true", help="Don't seed database")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)
    print(f"Generating {args.days} days of synthetic browsing data...")

    events = generate_dataset(days=args.days)
    print_stats(events)

    if args.csv:
        csv_path = export_csv(events)
        print(f"Exported to: {csv_path}")

    if not args.no_seed:
        count = seed_database(events)
        print(f"Seeded database with {count} events")

    print("Done!")
