from sqlalchemy.orm import Session

from app.config import settings
from app.engine.scoring import compute_s_score
from app.engine.clustering import assign_band, next_band, BAND_HARD
from app.models import QuizAttempt, QuizCatalog
from app.schemas import StudentProfile

def build_student_profile(student_id: str, db: Session) -> StudentProfile | None:
    attempts: list[QuizAttempt] = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == student_id)
        .all()
    )

    if not attempts:
        return None

    scores = [a.score for a in attempts]
    times = [a.time_used for a in attempts]
    taken_ids = list({a.quiz_id for a in attempts})

    s_score = compute_s_score(scores=scores, times=times)
    level = assign_band(s_score)

    mu_score = sum(scores) / len(scores)
    mu_time = sum(times) / len(times)

    boost_active = (
        mu_score > settings.boost_min_score
        and mu_time < settings.boost_max_time
    )

    target_groups = _compute_target_groups(level=level, boost_active=boost_active)

    return StudentProfile(
        student_id=student_id,
        mu_score=round(mu_score, 2),
        sigma_score=0.0,
        mu_time=round(mu_time, 3),
        s_score=s_score,
        level=level,
        boost_active=boost_active,
        target_groups=target_groups,
        taken_quiz_ids=taken_ids,
    )


def _compute_target_groups(level: str, boost_active: bool) -> list[str]:
    upper = next_band(level)

    if boost_active and upper is not None:
        return [upper]

    if upper is not None:
        return [level, upper]

    return [BAND_HARD]

def get_recommendations(student_id: str, db: Session) -> list[str]:
    profile = build_student_profile(student_id=student_id, db=db)

    if profile is None:
        return []

    candidates = _fetch_candidates(profile=profile, db=db)

    if not candidates:
        candidates = _fetch_consolidation_candidates(profile=profile, db=db)

    candidates.sort(key=lambda q: abs(q.d_score - profile.s_score))

    return [q.quiz_id for q in candidates[: settings.top_n_recommendations]]


def _fetch_candidates(profile: StudentProfile, db: Session) -> list[QuizCatalog]:
    return (
        db.query(QuizCatalog)
        .filter(
            QuizCatalog.difficulty_group.in_(profile.target_groups),
            QuizCatalog.quiz_id.notin_(profile.taken_quiz_ids),
            QuizCatalog.d_score.isnot(None),
        )
        .all()
    )


def _fetch_consolidation_candidates(profile: StudentProfile, db: Session) -> list[QuizCatalog]:
    weak_attempts: list[QuizAttempt] = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.student_id == profile.student_id,
            QuizAttempt.score < settings.consolidation_score_threshold,
        )
        .order_by(QuizAttempt.score.asc())
        .all()
    )

    seen: set[str] = set()
    weak_quiz_ids: list[str] = []
    for attempt in weak_attempts:
        if attempt.quiz_id not in seen:
            seen.add(attempt.quiz_id)
            weak_quiz_ids.append(attempt.quiz_id)

    if not weak_quiz_ids:
        return []

    return (
        db.query(QuizCatalog)
        .filter(
            QuizCatalog.quiz_id.in_(weak_quiz_ids),
            QuizCatalog.d_score.isnot(None),
        )
        .all()
    )
