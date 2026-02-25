from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

class QuizResultInput(BaseModel):
    studentId: str = Field(..., min_length=1, description="Identifiant unique de l'étudiant")
    quizId: str = Field(..., min_length=1, description="Identifiant unique du quiz")
    score: float = Field(..., ge=0, le=100, description="Note obtenue en pourcentage (0–100)")
    maxScore: float = Field(..., gt=0, description="Note maximale possible")
    timeSpentSeconds: int = Field(..., ge=0, description="Temps utilisé en secondes")
    totalQuizTimeSeconds: int = Field(..., gt=0, description="Temps total alloué en secondes")

    @field_validator("score")
    @classmethod
    def score_must_not_exceed_max(cls, v: float, info) -> float:
        return v

    def compute_time_ratio(self) -> float:
        return self.timeSpentSeconds / self.totalQuizTimeSeconds

    def compute_score_pct(self) -> float:
        return (self.score / self.maxScore) * 100

class RecommendationResponse(BaseModel):
    studentId: str
    recommendedQuizIds: list[str]


class QuizMetrics(BaseModel):
    quiz_id: str
    mu_grade: float
    sigma_grade: float
    mu_time: float
    d_score: float
    difficulty_group: str
    attempt_count: int
    is_verified: bool


class StudentProfile(BaseModel):
    student_id: str
    mu_score: float
    sigma_score: float
    mu_time: float
    s_score: float
    level: str
    boost_active: bool
    target_groups: list[str]
    taken_quiz_ids: list[str]


class QuizResultStored(BaseModel):
    quiz_id: str
    student_id: str
    score_pct: float
    time_ratio: float
    recorded_at: datetime

    class Config:
        from_attributes = True
