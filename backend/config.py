"""Application configuration."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "adaptifocus.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{DB_PATH}"

# API
API_HOST = "0.0.0.0"
API_PORT = 8000

# ── Authentication ───────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "adaptifocus-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72  # Token valid for 3 days

# ── Agent Thresholds ─────────────────────────────────────────────────────────
NUDGE_THRESHOLD_SECONDS = 30
WARN_THRESHOLD_SECONDS = 120
SOFT_BLOCK_THRESHOLD_SECONDS = 300
HARD_BLOCK_THRESHOLD_SECONDS = 600

# Intervention escalation levels
INTERVENTION_LEVELS = {
    "none": 0,
    "nudge": 1,
    "warn": 2,
    "soft_block": 3,
    "hard_block": 4,
}

# ── ML & Pattern Classification ──────────────────────────────────────────────
MIN_EVENTS_FOR_PATTERN = 50
PATTERN_UPDATE_INTERVAL = 300

# Study session defaults
DEFAULT_STUDY_DURATION_MINUTES = 45
DEFAULT_BREAK_DURATION_MINUTES = 10

# ── Beta Testing ─────────────────────────────────────────────────────────────
EXPERIMENT_GROUP_CONTROL = "control"        # Tracking only
EXPERIMENT_GROUP_STATIC = "static_block"    # Basic blocking
EXPERIMENT_GROUP_ADAPTIVE = "adaptive"      # Full AdaptiFocus

