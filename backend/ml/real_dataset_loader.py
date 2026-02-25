"""Real dataset loader for AdaptiFocus.

Supports loading and transforming real browsing/digital wellbeing datasets
from Kaggle and other public sources for training the ML classifier.

Supported datasets:
1. Browser History Dataset (Firefox) — real browsing URLs with timestamps
2. Mental Health & Digital Behavior — screen time, focus, social media
3. Website Traffic Dataset — page views, session duration, bounce rate
4. Custom CSV — any CSV with domain/duration/timestamp columns

Usage:
    python -m ml.real_dataset_loader --source browser_history --path data/browser_history.csv
    python -m ml.real_dataset_loader --source digital_behavior --path data/mental_health.csv
    python -m ml.real_dataset_loader --source custom --path data/my_data.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

# ── Known domain categories ──────────────────────────────────────────────────

DISTRACTION_DOMAINS = {
    "youtube.com", "reddit.com", "twitter.com", "x.com",
    "instagram.com", "tiktok.com", "facebook.com", "netflix.com",
    "twitch.tv", "9gag.com", "buzzfeed.com", "imgur.com",
    "snapchat.com", "pinterest.com", "tumblr.com", "discord.com",
    "vine.co", "dailymotion.com", "vimeo.com",
}

STUDY_DOMAINS = {
    "github.com", "gitlab.com", "stackoverflow.com", "stackexchange.com",
    "arxiv.org", "scholar.google.com", "docs.python.org", "developer.mozilla.org",
    "leetcode.com", "hackerrank.com", "geeksforgeeks.org", "w3schools.com",
    "coursera.org", "edx.org", "udemy.com", "khanacademy.org",
    "ieeexplore.ieee.org", "acm.org", "overleaf.com", "notion.so",
    "classroom.google.com", "drive.google.com", "docs.google.com",
    "medium.com", "dev.to", "replit.com", "codepen.io",
}

NEUTRAL_DOMAINS = {
    "google.com", "gmail.com", "outlook.com", "yahoo.com",
    "weather.com", "maps.google.com", "amazon.com", "wikipedia.org",
    "news.google.com",
}


def classify_domain(domain: str) -> str:
    """Classify a domain as study, distraction, or neutral."""
    domain = domain.lower().strip()
    # Remove www prefix
    if domain.startswith("www."):
        domain = domain[4:]

    # Check exact matches
    if domain in DISTRACTION_DOMAINS:
        return "distraction"
    if domain in STUDY_DOMAINS:
        return "study"
    if domain in NEUTRAL_DOMAINS:
        return "neutral"

    # Check partial matches (subdomains)
    for d in DISTRACTION_DOMAINS:
        if domain.endswith("." + d) or domain == d:
            return "distraction"
    for d in STUDY_DOMAINS:
        if domain.endswith("." + d) or domain == d:
            return "study"

    return "neutral"


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from a URL."""
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        hostname = parsed.hostname or ""
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname if hostname else None
    except Exception:
        return None


# ── Dataset loaders ──────────────────────────────────────────────────────────

def load_browser_history(filepath: str) -> List[Dict]:
    """Load Firefox Browser History Dataset from Kaggle.

    Expected columns: link, first_visit_time, last_visit_time, click_count, frecency
    Source: https://www.kaggle.com/datasets/saloni1712/browser-history
    """
    events = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("link", row.get("url", ""))
            domain = extract_domain(url)
            if not domain:
                continue

            # Parse timestamps (Unix microseconds for Firefox)
            first_visit = row.get("first_visit_time", "")
            try:
                if first_visit.isdigit() and len(first_visit) > 10:
                    # Firefox stores in microseconds
                    ts = datetime.fromtimestamp(int(first_visit) / 1_000_000)
                elif first_visit.isdigit():
                    ts = datetime.fromtimestamp(int(first_visit))
                else:
                    ts = datetime.fromisoformat(first_visit)
            except Exception:
                ts = datetime.now() - timedelta(days=len(events) % 14)

            click_count = int(row.get("click_count", row.get("click-count", 1)))
            frecency = float(row.get("frecency", 0))

            category = classify_domain(domain)
            # Estimate duration from frecency/clicks
            estimated_duration = max(10, min(int(frecency / 10), 1800)) if frecency > 0 else 30

            events.append({
                "url": url,
                "domain": domain,
                "title": row.get("title", url[:80]),
                "duration_seconds": estimated_duration,
                "timestamp": ts.isoformat(),
                "is_distraction": category == "distraction",
                "category": category,
                "session_id": None,
                "source": "browser_history",
            })

    return events


def load_digital_behavior(filepath: str) -> List[Dict]:
    """Load Mental Health & Digital Behavior Dataset from Kaggle.

    Columns include: screen_time, social_media_time, app_switches,
    focus_score, notifications, etc.
    Source: https://www.kaggle.com/datasets
    """
    events = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            screen_time = float(row.get("daily_screen_time", row.get("screen_time_hours", 0)))
            social_media = float(row.get("social_media_usage_time", row.get("social_media_hours", 0)))
            focus_score = float(row.get("focus_score", row.get("concentration_score", 50)))

            # Create synthetic browsing events from aggregate data
            ts = datetime.now() - timedelta(days=i % 30)

            # Study time events
            study_hours = max(0, screen_time - social_media)
            if study_hours > 0:
                events.append({
                    "url": "https://study.example.com",
                    "domain": "github.com",
                    "title": "Study Session",
                    "duration_seconds": int(study_hours * 3600),
                    "timestamp": ts.replace(hour=9).isoformat(),
                    "is_distraction": False,
                    "category": "study",
                    "session_id": None,
                    "source": "digital_behavior",
                    "focus_score": focus_score,
                })

            # Social media / distraction events
            if social_media > 0:
                events.append({
                    "url": "https://social.example.com",
                    "domain": "youtube.com",
                    "title": "Social Media Browsing",
                    "duration_seconds": int(social_media * 3600),
                    "timestamp": ts.replace(hour=15).isoformat(),
                    "is_distraction": True,
                    "category": "distraction",
                    "session_id": None,
                    "source": "digital_behavior",
                    "focus_score": focus_score,
                })

    return events


def load_website_traffic(filepath: str) -> List[Dict]:
    """Load Website Traffic Dataset from Kaggle.

    Columns: page_views, session_duration, bounce_rate, traffic_source,
    time_on_page, previous_visits, conversion_rate
    """
    events = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            session_duration = float(row.get("session_duration", row.get("Session_Duration", 0)))
            time_on_page = float(row.get("time_on_page", row.get("Time_on_Page", 0)))
            bounce_rate = float(row.get("bounce_rate", row.get("Bounce_Rate", 0)))
            page_views = int(row.get("page_views", row.get("Page_Views", 1)))

            ts = datetime.now() - timedelta(days=i % 30, hours=i % 12)

            # High bounce rate + short session = distraction
            is_distraction = bounce_rate > 0.6 and session_duration < 120

            events.append({
                "url": f"https://site-{i}.example.com",
                "domain": f"site-{i % 50}.com",
                "title": f"Page Visit (bounce={bounce_rate:.0%})",
                "duration_seconds": int(max(session_duration, time_on_page, 5)),
                "timestamp": ts.isoformat(),
                "is_distraction": is_distraction,
                "category": "distraction" if is_distraction else "study",
                "session_id": None,
                "source": "website_traffic",
            })

    return events


def load_custom_csv(filepath: str) -> List[Dict]:
    """Load any CSV with at least domain/url and duration columns.

    Auto-detects column names from common variants.
    """
    events = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        headers = {h.lower().strip() for h in reader.fieldnames or []}

        for i, row in enumerate(reader):
            # Auto-detect URL/domain column
            url = ""
            domain = ""
            for key in ["url", "link", "page_url", "website"]:
                if key in row:
                    url = row[key]
                    domain = extract_domain(url) or ""
                    break
            for key in ["domain", "hostname", "site"]:
                if key in row and not domain:
                    domain = row[key]

            if not domain:
                continue

            # Auto-detect duration
            duration = 30
            for key in ["duration_seconds", "duration", "time_spent", "session_duration", "dwell_time"]:
                if key in row:
                    try:
                        duration = int(float(row[key]))
                    except ValueError:
                        pass
                    break

            # Auto-detect timestamp
            ts = datetime.now() - timedelta(days=i % 30)
            for key in ["timestamp", "datetime", "date", "time", "visit_time"]:
                if key in row:
                    try:
                        ts = datetime.fromisoformat(row[key])
                    except Exception:
                        pass
                    break

            category = classify_domain(domain)

            events.append({
                "url": url or f"https://{domain}",
                "domain": domain,
                "title": row.get("title", row.get("page_title", domain)),
                "duration_seconds": duration,
                "timestamp": ts.isoformat(),
                "is_distraction": category == "distraction",
                "category": category,
                "session_id": None,
                "source": "custom_csv",
            })

    return events


# ── Seed database ────────────────────────────────────────────────────────────

def seed_database(events: List[Dict]) -> int:
    """Seed the SQLite database with loaded events."""
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


# ── CLI ──────────────────────────────────────────────────────────────────────

LOADERS = {
    "browser_history": load_browser_history,
    "digital_behavior": load_digital_behavior,
    "website_traffic": load_website_traffic,
    "custom": load_custom_csv,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load real datasets for AdaptiFocus")
    parser.add_argument("--source", choices=list(LOADERS.keys()), required=True)
    parser.add_argument("--path", required=True, help="Path to the dataset CSV")
    parser.add_argument("--no-seed", action="store_true", help="Don't seed database")
    args = parser.parse_args()

    print(f"Loading {args.source} dataset from {args.path}...")
    loader = LOADERS[args.source]
    events = loader(args.path)

    total = len(events)
    distraction_count = sum(1 for e in events if e["is_distraction"])
    print(f"\nLoaded {total} events")
    print(f"  Study:       {total - distraction_count} ({(total-distraction_count)/max(total,1)*100:.1f}%)")
    print(f"  Distraction: {distraction_count} ({distraction_count/max(total,1)*100:.1f}%)")
    print(f"  Domains:     {len(set(e['domain'] for e in events))}")

    if not args.no_seed:
        count = seed_database(events)
        print(f"\nSeeded database with {count} events")

    print("Done!")
