"""Auth routes — Google Sign-In, profile, consent, and data management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import User
from api.auth import verify_google_token, create_token, require_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    id_token: str

class ConsentRequest(BaseModel):
    consent_given: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: str
    experiment_group: str
    is_new_user: bool = False

class UserProfile(BaseModel):
    id: int
    email: str
    username: str
    experiment_group: str
    consent_given: bool
    picture: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/google", response_model=TokenResponse)
def google_signin(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Sign in with Google. Creates account on first login."""
    # Verify the Google token
    google_info = verify_google_token(req.id_token)
    email = google_info["email"]

    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    is_new = False

    if not user:
        # New user — assign experiment group round-robin
        user_count = db.query(User).count()
        groups = ["adaptive", "adaptive", "static_block", "control"]
        group = groups[user_count % len(groups)]

        user = User(
            email=email,
            username=google_info["name"],
            google_id=google_info["google_id"],
            picture=google_info.get("picture", ""),
            hashed_password="",  # No password needed for Google auth
            experiment_group=group,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new = True

    if not user.is_active:
        raise HTTPException(403, "Account deactivated")

    # Update picture on each login
    if google_info.get("picture") and user.picture != google_info["picture"]:
        user.picture = google_info["picture"]
        db.commit()

    token = create_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        email=user.email,
        experiment_group=user.experiment_group,
        is_new_user=is_new,
    )


class DevLoginRequest(BaseModel):
    email: str = "dev@test.local"
    username: str = "Developer"


@router.post("/dev-login", response_model=TokenResponse)
def dev_login(req: DevLoginRequest, db: Session = Depends(get_db)):
    """Dev mode login — skips Google OAuth. Only works locally."""
    import os
    if os.getenv("DEV_MODE", "1") != "1":
        raise HTTPException(403, "Dev login is only available in development mode")

    # Normalize email to prevent duplicates if typed differently
    req_email = req.email.strip().lower()

    user = db.query(User).filter(User.email == req_email).first()
    is_new = False

    if not user:
        user_count = db.query(User).count()
        groups = ["adaptive", "adaptive", "static_block", "control"]
        user = User(
            email=req_email,
            username=req.username,
            hashed_password="",
            experiment_group=groups[user_count % len(groups)],
            consent_given=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new = True

    token = create_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        email=user.email,
        experiment_group=user.experiment_group,
        is_new_user=is_new,
    )


@router.get("/me", response_model=UserProfile)
def get_profile(user: User = Depends(require_user)):
    """Get current user profile."""
    return user


@router.post("/consent")
def give_consent(
    req: ConsentRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Record user consent for data collection."""
    user.consent_given = req.consent_given
    user.consent_timestamp = datetime.utcnow() if req.consent_given else None
    db.commit()
    return {"status": "ok", "consent_given": user.consent_given}


@router.delete("/data")
def delete_my_data(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Delete all data for current user (GDPR)."""
    from database.models import BrowsingEvent, StudySession, Intervention, UserPattern

    db.query(BrowsingEvent).filter(BrowsingEvent.user_id == user.id).delete()
    db.query(Intervention).filter(Intervention.user_id == user.id).delete()
    db.query(StudySession).filter(StudySession.user_id == user.id).delete()
    db.query(UserPattern).filter(UserPattern.user_id == user.id).delete()
    db.commit()

    return {"status": "ok", "message": "All your data has been deleted"}
