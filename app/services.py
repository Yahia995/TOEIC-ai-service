import math
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.engine.scoring import compute_d_score
from app.engine.clustering import assign_band, detect_quiz_type
from app.engine.recommender import get_recommendations
from app.models import QuizAttempt, QuizCatalog
from app.schemas import QuizResultInput, QuizResultStored, RecommendationResponse
from app.toeic_gateway import toeic_gateway

logger = logging.getLogger(__name__)


async def store_quiz_result(payload: QuizResultInput, db: Session) -> QuizResultStored:
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
    is_new_quiz = quiz is None

    if is_new_quiz:
        quiz = QuizCatalog(quiz_id=payload.quizId, attempt_count=0)
        db.add(quiz)
        db.flush()

    if is_new_quiz or (quiz.question_text is None and toeic_gateway.is_available):
        details = await toeic_gateway.fetch_quiz_details(payload.quizId)
        if details:
            quiz.title = details["title"]
            quiz.question_text = details["question_text"]
            logger.info(
                "Quiz %s enriched from TOEIC backend: title=%s, has_text=%s",
                payload.quizId,
                details["title"],
                details["question_text"] is not None,
            )

    all_attempts: list[QuizAttempt] = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == payload.quizId)
        .all()
    )
    grades = [a.score for a in all_attempts]
    times = [a.time_used for a in all_attempts]

    d_score = compute_d_score(grades=grades, times=times)
    difficulty_group = assign_band(d_score)

    quiz_type = detect_quiz_type(
        question_text=quiz.question_text,
        sigma_grade=_std_dev(grades),
    )

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


async def sync_catalog(db: Session) -> dict:
    if not toeic_gateway.is_available:
        return {"synced": 0, "skipped": 0, "sdk_available": False}

    quizzes = await toeic_gateway.fetch_all_quizzes()
    synced = 0
    skipped = 0

    for q in quizzes:
        existing = db.query(QuizCatalog).filter(
            QuizCatalog.quiz_id == q["quiz_id"]
        ).first()

        if existing is None:
            db.add(QuizCatalog(
                quiz_id=q["quiz_id"],
                title=q["title"],
                question_text=q["question_text"],
                attempt_count=0,
            ))
            synced += 1
        elif existing.title is None:
            existing.title = q["title"]
            existing.question_text = q["question_text"]
            synced += 1
        else:
            skipped += 1

    db.commit()
    logger.info("Catalog sync: %d synced, %d skipped", synced, skipped)
    return {"synced": synced, "skipped": skipped, "sdk_available": True}

def _std_dev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mu = sum(values) / len(values)
    variance = sum((x - mu) ** 2 for x in values) / len(values)
    return math.sqrt(variance)
