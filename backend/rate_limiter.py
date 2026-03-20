"""Rate limiting configuration using slowapi.

How it works:
    - slowapi uses the 'limits' library under the hood
    - Rate limits are specified as strings like "60/minute" or "5/second"
    - Limits are tracked per-IP by default (via get_remote_address)
    - When exceeded, returns HTTP 429 Too Many Requests

Rate limit format:
    "N/period" where period is: second, minute, hour, day
    Examples: "60/minute", "5/second", "1000/hour"
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create rate limiter — keyed by client IP address
limiter = Limiter(key_func=get_remote_address)

# ── Rate limit presets ───────────────────────────────────────────────────────
# Use these constants in route decorators: @limiter.limit(RATE_STANDARD)

RATE_STANDARD = "60/minute"     # Normal API calls (analytics, stats)
RATE_AUTH = "10/minute"         # Login/signup attempts
RATE_WRITE = "30/minute"        # Event ingestion, session starts
RATE_HEAVY = "10/minute"        # ML retraining, pattern analysis
RATE_CLASSIFY = "120/minute"    # Page classification (called frequently)
