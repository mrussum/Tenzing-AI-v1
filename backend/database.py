"""Database engine and session factory."""
from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Local development fallback — SQLite
    DATABASE_URL = "sqlite:///./decisions.db"
    _using_sqlite = True
else:
    _using_sqlite = False
    # Render injects postgres:// — SQLAlchemy 2.x requires postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite requires connect_args for thread safety with FastAPI
connect_args = {"check_same_thread": False} if _using_sqlite else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)

if _using_sqlite:
    logger.info("Database mode: SQLite (local dev fallback) — %s", DATABASE_URL)
else:
    logger.info("Database mode: PostgreSQL — %s", DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
