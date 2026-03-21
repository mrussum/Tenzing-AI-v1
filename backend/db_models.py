"""SQLAlchemy table definitions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class DBDecision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True)
    account_id = Column(String, nullable=False, index=True)
    text = Column(Text, nullable=False)
    decided_by = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)


class DBAIAnalysisCache(Base):
    __tablename__ = "ai_analysis_cache"

    account_id = Column(String, primary_key=True)
    payload = Column(Text, nullable=False)   # JSON-serialised AIAnalysis
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DBPortfolioBriefingCache(Base):
    __tablename__ = "portfolio_briefing_cache"

    id = Column(Integer, primary_key=True, default=1)
    briefing = Column(Text, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
