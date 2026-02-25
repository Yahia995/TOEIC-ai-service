from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Ils peuvent être surchargés via variables d'environnement ou fichier .env.
    """

    # Base de données
    database_url: str = "sqlite:///./quiz_ai.db"

    # Sécurité
    api_key: str = "dev-key"

    # --- Poids du D_score / S_score ---
    # Ces trois valeurs doivent toujours sommer à 1.0.
    weight_grade: float = 0.60       # contribution de la note moyenne
    weight_time: float = 0.25        # contribution du temps moyen
    weight_variance: float = 0.15    # contribution de l'écart-type des notes

    # --- Seuils de bande de difficulté ---
    threshold_easy: float = 0.35     # D_score < threshold_easy  → Facile
    threshold_medium: float = 0.60   # D_score < threshold_medium → Moyen, sinon Difficile

    # --- Règle de boost ---
    boost_min_score: float = 85.0    # score moyen au-dessus duquel le boost peut s'activer
    boost_max_time: float = 0.85     # temps moyen en dessous duquel le boost peut s'activer

    # --- Recommandation ---
    top_n_recommendations: int = 5   # nombre maximum de quizzes recommandés
    cold_start_min_attempts: int = 5  # tentatives minimales avant d'inclure σ dans le calcul
    consolidation_score_threshold: float = 75.0  # seuil en dessous duquel on propose la consolidation

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
