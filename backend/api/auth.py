"""Authentication — Google OAuth + JWT for AdaptiFocus."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS
from database.db import get_db
from database.models import User

# Google OAuth config
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"

security = HTTPBearer(auto_error=False)


def verify_google_token(id_token: str) -> dict:
    """Verify a Google ID token and return user info.

    Returns: {"email": "...", "name": "...", "picture": "...", "sub": "..."}
    """
    resp = requests.get(
        GOOGLE_TOKEN_INFO_URL,
        params={"id_token": id_token},
        timeout=10,
    )

    if resp.status_code != 200:
        raise HTTPException(401, "Invalid Google token")

    payload = resp.json()

    # Verify the token is for our app (if client ID is configured)
    if GOOGLE_CLIENT_ID and payload.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(401, "Token not issued for this application")

    if payload.get("email_verified") != "true":
        raise HTTPException(401, "Email not verified by Google")

    return {
        "email": payload["email"],
        "name": payload.get("name", payload["email"].split("@")[0]),
        "picture": payload.get("picture", ""),
        "google_id": payload["sub"],
    }


def create_token(user_id: int, email: str) -> str:
    """Create a JWT access token."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get authenticated user or None."""
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials)
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()

    if not user:
        raise HTTPException(401, "User not found")
    return user


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    """Require authenticated user."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
