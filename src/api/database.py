"""
SQLite database setup for GuardianShield API.

Stores prediction logs and user feedback using SQLAlchemy.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


class PredictionLog(Base):
    """Log of every prediction made by the API."""

    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(Text, nullable=False)
    label = Column(String(20), nullable=False)
    label_id = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    processing_time_ms = Column(Float, nullable=True)
    user_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FeedbackLog(Base):
    """User-submitted feedback on model predictions."""

    __tablename__ = "feedback_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(Text, nullable=False)
    predicted_label = Column(String(20), nullable=False)
    actual_label = Column(String(20), nullable=False)
    user_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Global engine and session factory
_engine = None
_SessionLocal = None


def init_db(db_url: str | None = None) -> None:
    """Initialize the database connection and create tables."""
    global _engine, _SessionLocal

    if db_url is None:
        cfg = get_config()
        db_url = cfg["api"]["db_url"]

    _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)
    logger.info(f"Database initialized: {db_url}")


def get_session() -> Session:
    """FastAPI dependency that provides a database session."""
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_prediction(
    db: Session, text: str, result: dict, user_id: str | None = None
) -> PredictionLog:
    """Save a prediction result to the database."""
    log = PredictionLog(
        text=text[:500],  # Truncate for storage
        label=result["label"],
        label_id=result["label_id"],
        confidence=result["confidence"],
        risk_level=result["risk_level"],
        processing_time_ms=result.get("processing_time_ms"),
        user_id=user_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def log_feedback(
    db: Session, text: str, predicted: str, actual: str, user_id: str | None = None
) -> FeedbackLog:
    """Save user feedback to the database."""
    feedback = FeedbackLog(
        text=text[:500],
        predicted_label=predicted,
        actual_label=actual,
        user_id=user_id,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_stats(db: Session) -> dict:
    """Aggregate prediction statistics from the database."""
    total = db.query(PredictionLog).count()
    spam = db.query(PredictionLog).filter(PredictionLog.label == "spam").count()
    phishing = db.query(PredictionLog).filter(PredictionLog.label == "phishing").count()
    ham = db.query(PredictionLog).filter(PredictionLog.label == "ham").count()
    feedback = db.query(FeedbackLog).count()

    return {
        "total_predictions": total,
        "spam_count": spam,
        "phishing_count": phishing,
        "ham_count": ham,
        "spam_rate": round(spam / total, 4) if total > 0 else 0.0,
        "phishing_rate": round(phishing / total, 4) if total > 0 else 0.0,
        "feedback_count": feedback,
    }
