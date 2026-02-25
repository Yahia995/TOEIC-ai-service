from app.config import settings

BAND_EASY = "Easy"
BAND_MEDIUM = "Medium"
BAND_HARD = "Hard"

BAND_ORDER = [BAND_EASY, BAND_MEDIUM, BAND_HARD] 


def assign_band(d_score: float) -> str:
    if d_score < settings.threshold_easy:
        return BAND_EASY
    if d_score < settings.threshold_medium:
        return BAND_MEDIUM
    return BAND_HARD


def next_band(band: str) -> str | None:
    idx = BAND_ORDER.index(band)
    if idx < len(BAND_ORDER) - 1:
        return BAND_ORDER[idx + 1]
    return None

_GRAMMAR_SIGNALS: frozenset[str] = frozenset({
    "tense", "tenses", "verb", "verbs", "conjugate", "conjugation",
    "syntax", "pronoun", "pronouns", "preposition", "prepositions",
    "clause", "clauses", "agreement", "subjunctive", "passive",
    "active", "participle", "infinitive", "modal", "auxiliary",
    "temps", "verbe", "conjugaison", "accord", "subjonctif",
})

_VOCAB_SIGNALS: frozenset[str] = frozenset({
    "definition", "definitions", "word", "words", "synonym", "synonyms",
    "antonym", "antonyms", "meaning", "meanings", "spelling", "vocabulary",
    "translate", "translation", "lexical", "term", "terms", "idiom", "idioms",
    "définition", "mot", "synonyme", "antonyme", "orthographe", "vocabulaire",
    "traduction", "sens",
})

def detect_quiz_type(question_text: str | None, sigma_grade: float | None = None) -> str | None:
    if question_text:
        return _classify_by_keywords(question_text)

    if sigma_grade is not None:
        return _classify_by_variance(sigma_grade)

    return None

def _classify_by_keywords(text: str) -> str:
    tokens = set(text.lower().split())
    g_hits = len(tokens & _GRAMMAR_SIGNALS)
    v_hits = len(tokens & _VOCAB_SIGNALS)

    if g_hits > v_hits:
        return "grammar"
    if v_hits > g_hits:
        return "vocabulary"
    return "mixed"

def _classify_by_variance(sigma_grade: float) -> str:
    return "vocabulary" if sigma_grade > 20.0 else "grammar"
