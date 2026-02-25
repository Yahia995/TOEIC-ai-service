from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(String, ForeignKey("quiz_catalog.quiz_id"), nullable=False, index=True)
    student_id = Column(String, nullable=False, index=True)
    score = Column(Float, nullable=False)
    time_used = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    quiz = relationship("QuizCatalog", back_populates="attempts")


class QuizCatalog(Base):
    __tablename__ = "quiz_catalog"

    quiz_id = Column(String, primary_key=True, index=True)
    d_score = Column(Float, nullable=True)
    difficulty_group = Column(String, nullable=True)
    quiz_type = Column(String, nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_computed_at = Column(DateTime, nullable=True)

    attempts = relationship("QuizAttempt", back_populates="quiz")
