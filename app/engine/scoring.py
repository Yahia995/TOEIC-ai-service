import math
from app.config import settings

def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("Impossible de calculer la moyenne d'une liste vide.")
    return sum(values) / len(values)


def _std_dev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    variance = sum((x - mu) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _trimmed_mean(values: list[float]) -> float:
    if len(values) < settings.cold_start_min_attempts:
        return _mean(values)
    trimmed = sorted(values)[1:-1]
    return _mean(trimmed)


def compute_d_score(grades: list[float], times: list[float]) -> float:
    if not grades or not times:
        raise ValueError("Les listes grades et times ne peuvent pas etre vides.")
    if len(grades) != len(times):
        raise ValueError(
            f"grades ({len(grades)}) et times ({len(times)}) doivent avoir la meme longueur."
        )

    n = len(grades)

    mu_grade = _trimmed_mean(grades) if n >= settings.cold_start_min_attempts else _mean(grades)
    mu_time = _mean(times)

    if n >= 2:
        sigma_grade = _std_dev(grades)
        variance_contribution = (sigma_grade / 50.0) * settings.weight_variance
    else:
        sigma_grade = 0.0
        variance_contribution = 0.0

    grade_contribution = (1.0 - mu_grade / 100.0) * settings.weight_grade
    time_contribution = _clamp(mu_time - 1.0, -1.0, 1.0) * settings.weight_time

    d_score = grade_contribution + time_contribution + variance_contribution

    return round(_clamp(d_score, 0.0, 1.0), 4)

def compute_s_score(scores: list[float], times: list[float]) -> float:
    return compute_d_score(grades=scores, times=times)

def compute_quiz_metrics(grades: list[float], times: list[float]) -> dict:
    n = len(grades)
    mu_grade = _trimmed_mean(grades) if n >= settings.cold_start_min_attempts else _mean(grades)
    sigma_grade = _std_dev(grades) if n >= 2 else 0.0
    mu_time = _mean(times)

    grade_contribution = (1.0 - mu_grade / 100.0) * settings.weight_grade
    time_contribution = _clamp(mu_time - 1.0, -1.0, 1.0) * settings.weight_time
    variance_contribution = (
        (sigma_grade / 50.0) * settings.weight_variance
        if n >= 2 else 0.0
    )
    d_score = _clamp(grade_contribution + time_contribution + variance_contribution, 0.0, 1.0)

    return {
        "n": n,
        "mu_grade": round(mu_grade, 2),
        "sigma_grade": round(sigma_grade, 2),
        "mu_time": round(mu_time, 3),
        "grade_contribution": round(grade_contribution, 4),
        "time_contribution": round(time_contribution, 4),
        "variance_contribution": round(variance_contribution, 4),
        "d_score": round(d_score, 4),
        "sigma_included": n >= 2,
        "trimmed_mean_used": n >= settings.cold_start_min_attempts,
    }
