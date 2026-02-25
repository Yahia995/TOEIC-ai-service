from datetime import datetime

from sqlalchemy.orm import Session

from app.engine.scoring import compute_d_score
from app.engine.clustering import assign_band, detect_quiz_type
from app.engine.recommender import get_recommendations, build_student_profile
from app.models import QuizAttempt, QuizCatalog
from app.schemas import QuizResultInput, QuizResultStored, RecommendationResponse


def store_quiz_result(payload: QuizResultInput, db: Session) -> QuizResultStored:
    score_pct = payload.compute_score_pct()
    time_ratio = payload.compute_time_ratio()

    attempt = QuizAttempt(
        quiz_id=payload.quizId,
        student_id=payload.studentId,
        score=score_pct,
        time_used=time_ratio,
        recorded_at=datetime.utcnow(),
    )
    db.add(attempt)
    db.flush()

    quiz = db.query(QuizCatalog).filter(QuizCatalog.quiz_id == payload.quizId).first()
    if quiz is None:
        quiz = QuizCatalog(quiz_id=payload.quizId, attempt_count=0)
        db.add(quiz)
        db.flush()

    all_attempts: list[QuizAttempt] = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == payload.quizId)
        .all()
    )
    grades = [a.score for a in all_attempts]
    times = [a.time_used for a in all_attempts]

    d_score = compute_d_score(grades=grades, times=times)
    difficulty_group = assign_band(d_score)
    quiz_type = detect_quiz_type(question_text=None, sigma_grade=_std_dev(grades))

    from app.config import settings

    quiz.d_score = d_score
    quiz.difficulty_group = difficulty_group
    quiz.quiz_type = quiz_type
    quiz.attempt_count = len(all_attempts)
    quiz.is_verified = len(all_attempts) >= settings.cold_start_min_attempts
    quiz.last_computed_at = datetime.utcnow()

    db.commit()
    db.refresh(attempt)

    return QuizResultStored(
        quiz_id=attempt.quiz_id,
        student_id=attempt.student_id,
        score_pct=round(score_pct, 2),
        time_ratio=round(time_ratio, 3),
        recorded_at=attempt.recorded_at,
    )


def fetch_recommendations(student_id: str, db: Session) -> RecommendationResponse:
    recommended_ids = get_recommendations(student_id=student_id, db=db)
    return RecommendationResponse(
        studentId=student_id,
        recommendedQuizIds=recommended_ids,
    )

def _std_dev(values: list[float]) -> float | None:
    import math
    if len(values) < 2:
        return None
    mu = sum(values) / len(values)
    variance = sum((x - mu) ** 2 for x in values) / len(values)
    return math.sqrt(variance)
