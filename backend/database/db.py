"""Database setup — PostgreSQL for production, SQLite for development."""

import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

# Use PostgreSQL in production, SQLite for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    from config import DATABASE_URL as SQLITE_URL
    DATABASE_URL = SQLITE_URL

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

is_sqlite = DATABASE_URL.startswith("sqlite")
if is_sqlite and "sqlite://" in DATABASE_URL and not DATABASE_URL.startswith("sqlite+aiosqlite://"):
    DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)

if is_sqlite:
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        # pool_pre_ping is not supported for async sqlite
    )

    # Note: SQLite AsyncPragma setup is omitted for brevity,
    # as WAL mode generally persists once the DB file is created!
else:
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    """FastAPI dependency to get an async DB session."""
    async with SessionLocal() as db:
        yield db

async def init_db():
    """Create all tables (if Alembic is not used)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
