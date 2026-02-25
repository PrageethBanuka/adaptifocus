"""SQLAlchemy ORM models for AdaptiFocus (multi-user)."""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from database.db import Base


class User(Base):
    """Registered user (beta tester)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), default="")  # Empty for Google auth
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    picture = Column(String(512), nullable=True)
    experiment_group = Column(
        String(50), default="adaptive"
    )  # control | static_block | adaptive
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    consent_given = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime, nullable=True)

    # Relationships
    events = relationship("BrowsingEvent", back_populates="user", lazy="dynamic")
    sessions = relationship("StudySession", back_populates="user", lazy="dynamic")
    interventions = relationship("Intervention", back_populates="user", lazy="dynamic")
    patterns = relationship("UserPattern", back_populates="user", lazy="dynamic")


class BrowsingEvent(Base):
    """Raw browsing activity event from the extension."""

    __tablename__ = "browsing_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    url = Column(String(2048), nullable=True)
    domain = Column(String(255), nullable=True)
    title = Column(String(512), nullable=True)
    duration_seconds = Column(Integer, default=0)
    is_distraction = Column(Boolean, default=False)
    distraction_score = Column(Float, default=0.0)
    category = Column(String(100), nullable=True)
    session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=True)

    user = relationship("User", back_populates="events")
    session = relationship("StudySession", back_populates="events")


class StudySession(Base):
    """A focused study session with start/end times."""

    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    study_topic = Column(String(255), nullable=True)
    planned_duration_minutes = Column(Integer, default=45)
    actual_focus_seconds = Column(Integer, default=0)
    actual_distraction_seconds = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")
    events = relationship("BrowsingEvent", back_populates="session")
    interventions = relationship("Intervention", back_populates="session")


class Intervention(Base):
    """Record of an intervention delivered to the user."""

    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    level = Column(String(20), nullable=False)
    trigger_url = Column(String(2048), nullable=True)
    trigger_domain = Column(String(255), nullable=True)
    duration_on_distraction_seconds = Column(Integer, default=0)
    was_effective = Column(Boolean, nullable=True)
    user_response = Column(String(50), nullable=True)
    session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=True)

    user = relationship("User", back_populates="interventions")
    session = relationship("StudySession", back_populates="interventions")


class UserPattern(Base):
    """Learned behavioral pattern for a user."""

    __tablename__ = "user_patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    pattern_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    data_json = Column(Text, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="patterns")
