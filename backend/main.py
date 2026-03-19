"""AdaptiFocus Backend — FastAPI entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import asyncio
from database.db import init_db
from api.routes import events, interventions, sessions, analytics, auth, admin, ml, streaks

app = FastAPI(
    title="AdaptiFocus API",
    description=(
        "AI-driven adaptive attention management system for academic "
        "digital wellbeing. Provides event ingestion, multi-agent "
        "intervention decisions, study session management, and analytics."
    ),
    version="0.2.0",
)

# CORS — allow extension and dashboard origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(interventions.router)
app.include_router(sessions.router)
app.include_router(analytics.router)
app.include_router(admin.router)
app.include_router(ml.router)
app.include_router(streaks.router)


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
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }


@app.post("/classify")
def classify_page(data: dict):
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
