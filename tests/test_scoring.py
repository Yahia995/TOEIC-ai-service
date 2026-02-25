import pytest
from app.engine.scoring import compute_d_score, compute_s_score, compute_quiz_metrics
from app.engine.clustering import assign_band, detect_quiz_type, next_band

class TestComputeDScore:

    def test_easy_quiz(self):
        grades = [90.0, 95.0, 88.0]
        times = [0.5, 0.6, 0.55]
        score = compute_d_score(grades, times)
        assert score < 0.35, f"Attendu < 0.35 (Easy), obtenu {score}"

    def test_hard_quiz(self):
        grades = [10.0, 15.0, 20.0]
        times = [1.5, 1.6, 1.7]
        score = compute_d_score(grades, times)
        assert score >= 0.60, f"Attendu ≥ 0.60 (Hard), obtenu {score}"

    def test_medium_quiz(self):
        grades = [40.0, 45.0, 38.0]
        times = [1.1, 1.2, 1.0]
        score = compute_d_score(grades, times)
        assert 0.35 <= score < 0.60, f"Attendu dans [0.35, 0.60], obtenu {score}"

    def test_q99_from_brief(self):
        grades = [85.0, 40.0, 55.0]
        times = [0.8, 1.2, 1.5]
        score = compute_d_score(grades, times)
        assert score < 0.35, f"q_99 devrait etre Easy, D_score={score}"

    def test_score_is_between_0_and_1(self):
        for grades, times in [
            ([0.0], [2.0]),
            ([100.0], [0.1]),
            ([50.0, 50.0], [1.0, 1.0]),
        ]:
            score = compute_d_score(grades, times)
            assert 0.0 <= score <= 1.0, f"Score hors bornes : {score}"

    def test_empty_grades_raises(self):
        with pytest.raises(ValueError, match="vide"):
            compute_d_score([], [])

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="meme longueur"):
            compute_d_score([80.0, 90.0], [1.0])

    def test_single_attempt_cold_start(self):
        score = compute_d_score([70.0], [1.1])
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_high_variance_increases_score(self):
        grades_uniform = [60.0, 60.0, 60.0, 60.0, 60.0]
        grades_spread = [10.0, 30.0, 60.0, 90.0, 100.0]
        times = [1.0, 1.0, 1.0, 1.0, 1.0]
        score_uniform = compute_d_score(grades_uniform, times)
        score_spread = compute_d_score(grades_spread, times)
        assert score_spread > score_uniform, "Variance élevée devrait augmenter le score"

class TestComputeSScore:

    def test_high_performer_fast(self):
        scores = [93.0, 91.0, 88.0]
        times = [0.5, 0.6, 0.65]
        score = compute_s_score(scores, times)
        assert score < 0.35

    def test_s501_from_brief(self):
        scores = [75.0, 82.0, 68.0]
        times = [1.1, 0.9, 1.3]
        score = compute_s_score(scores, times)
        assert score < 0.35, f"s_501 devrait etre Easy, S_score={score}"

    def test_symmetry_with_d_score(self):
        from app.engine.scoring import compute_d_score
        grades = [70.0, 75.0, 65.0]
        times = [1.0, 0.95, 1.05]
        assert compute_s_score(grades, times) == compute_d_score(grades, times)

class TestAssignBand:

    def test_easy_band(self):
        assert assign_band(0.10) == "Easy"
        assert assign_band(0.34) == "Easy"

    def test_medium_band(self):
        assert assign_band(0.35) == "Medium"
        assert assign_band(0.50) == "Medium"
        assert assign_band(0.59) == "Medium"

    def test_hard_band(self):
        assert assign_band(0.60) == "Hard"
        assert assign_band(0.90) == "Hard"

    def test_boundary_values(self):
        assert assign_band(0.349) == "Easy"
        assert assign_band(0.350) == "Medium"
        assert assign_band(0.599) == "Medium"
        assert assign_band(0.600) == "Hard"

class TestDetectQuizType:

    def test_grammar_keywords(self):
        text = "Identify the correct tense for the verb in the clause below"
        assert detect_quiz_type(text) == "grammar"

    def test_vocabulary_keywords(self):
        text = "Choose the synonym for the word 'benevolent' from the definitions below"
        assert detect_quiz_type(text) == "vocabulary"

    def test_mixed_or_no_signal(self):
        text = "Answer the following questions"
        assert detect_quiz_type(text) == "mixed"

    def test_no_text_high_variance_fallback(self):
        assert detect_quiz_type(None, sigma_grade=25.0) == "vocabulary"

    def test_no_text_low_variance_fallback(self):
        assert detect_quiz_type(None, sigma_grade=10.0) == "grammar"

    def test_no_text_no_sigma(self):
        assert detect_quiz_type(None, sigma_grade=None) is None

class TestNextBand:

    def test_easy_to_medium(self):
        assert next_band("Easy") == "Medium"

    def test_medium_to_hard(self):
        assert next_band("Medium") == "Hard"

    def test_hard_has_no_next(self):
        assert next_band("Hard") is None
