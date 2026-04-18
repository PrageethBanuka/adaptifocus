"""AdaptiFocus Backend — FastAPI entry point."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

import asyncio
from database.db import init_db
from api.routes import events, interventions, sessions, analytics, auth, admin, ml, streaks, reports, ws

# ── Sentry Error Monitoring ──────────────────────────────────────────────────
# Why: In production, errors can happen silently. Sentry catches unhandled
# exceptions, groups them by root cause, and alerts you with full stack traces.
#
# How to set up:
#   1. Go to sentry.io → Create project (Python / FastAPI)
#   2. Copy your DSN (looks like: https://abc123@o456.ingest.sentry.io/789)
#   3. Set SENTRY_DSN env var in Render → your backend → Environment
#   4. That's it — errors will appear in your Sentry dashboard automatically.

SENTRY_DSN = os.getenv("SENTRY_DSN")

def filter_sentry_events(event, hint):
    """Filter out expected network drops and minor noise from Sentry alerts."""
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        
        # Check if it's a websocket ConnectionClosedError
        if exc_type.__name__ == "ConnectionClosedError":
            # 1011 = Internal Error (often caused by 'keepalive ping timeout')
            # 1000 = Normal Closure
            # 1001 = Going Away (Tab closed)
            # 1006 = Abnormal Closure (Network dropped)
            if hasattr(exc_value, 'code') and exc_value.code in [1000, 1001, 1006, 1011]:
                return None  # Returning None drops the event completely
                
    return event

if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,        # 100% of requests get performance tracing
        profiles_sample_rate=0.1,      # 10% get CPU profiling
        environment=os.getenv("ENVIRONMENT", "production"),
        release=f"adaptifocus@0.3.0",
        before_send=filter_sentry_events
    )


app = FastAPI(
    title="AdaptiFocus API",
    description=(
        "AI-driven adaptive attention management system for academic "
        "digital wellbeing. Provides event ingestion, multi-agent "
        "intervention decisions, study session management, and analytics."
    ),
    version="0.3.0",
)

# ── Proxy IP Resolution ──────────────────────────────────────────────────────
# Fixes slowapi rate limiting behind Render/Heroku load balancers so it tracks
# actual user IPs instead of banning the single proxy IP.
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# ── CORS ─────────────────────────────────────────────────────────────────────
# Why: allow_origins=["*"] lets ANY website call your API, which is dangerous.
# In production, only your dashboard and extension should be allowed.
#
# Chrome extensions use origin "chrome-extension://<extension-id>".
# The dashboard is deployed at a known Render URL.
# Extra origins can be added via CORS_ORIGINS env var (comma-separated).

_default_origins = [
    "https://adaptifocus-dashboard.onrender.com",  # Production dashboard
    "http://localhost:5173",                         # Vite dev server
    "http://localhost:3000",                         # Alternative dev server
]

# Merge with any extra origins from environment
_extra = os.getenv("CORS_ORIGINS", "")
ALLOWED_ORIGINS = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^chrome-extension://.*$",  # Allow ALL extension IDs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiting ────────────────────────────────────────────────────────────
# Why: Without rate limits, a single bad actor or buggy extension can
# flood the API with thousands of requests, overloading the DB and server.
# slowapi returns HTTP 429 (Too Many Requests) when limits are exceeded.

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from rate_limiter import limiter, RATE_CLASSIFY

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register routers
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(interventions.router)
app.include_router(sessions.router)
app.include_router(analytics.router)
app.include_router(admin.router)
app.include_router(ml.router)
app.include_router(streaks.router)
app.include_router(reports.router)
app.include_router(ws.router)


async def _retrain_loop():
    """Background task: retrain ML model every 24 hours."""
    from ml.retrain import retrain
    while True:
        await asyncio.sleep(86400)  # 24 hours
        try:
            await retrain()
        except Exception as e:
            print(f"[Scheduler] Retrain failed: {e}")


@app.on_event("startup")
async def on_startup():
    """Initialize database and start background tasks."""
    init_db()
    asyncio.create_task(_retrain_loop())


@app.get("/")
def root():
    return {
        "name": "AdaptiFocus API",
        "version": "0.3.0",
        "status": "running",
        "docs": "/docs",
    }


@app.post("/classify")
@limiter.limit(RATE_CLASSIFY)
def classify_page(request: Request, data: dict):
    """Classify a page as study, distraction, or neutral using Context Agent."""
    from agents.context_agent import ContextAgent
    agent = ContextAgent()
    result = agent.analyze({
        "current_url": data.get("url", ""),
        "current_domain": data.get("domain", ""),
        "current_title": data.get("title", ""),
        "study_topic": data.get("study_topic"),
        "session_active": data.get("session_active", False),
        "recent_domains": data.get("recent_domains", []),
    })
    return result



@app.get("/health")
def health():
    return {"status": "ok"}

