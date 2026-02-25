# TOEIC AI Service

Moteur de catégorisation de quizzes par difficulté et de recommandation personnalisée par étudiant.

## Stack technique

- **FastAPI** — framework HTTP
- **PostgreSQL** — base de données (SQLite pour le développement local)
- **SQLAlchemy** — ORM
- **Pydantic** — validation des données

## Structure du projet

```
TOEIC-ai-service/
├── app/
│   ├── main.py          ← Application FastAPI + routes
│   ├── config.py        ← Tous les paramètres (via variables d'environnement)
│   ├── database.py      ← Connexion SQLAlchemy
│   ├── models.py        ← Modèles de base de données
│   ├── schemas.py       ← Schémas Pydantic (validation)
│   ├── services.py      ← Logique métier
│   └── engine/
│       ├── scoring.py      ← Calcul D_score / S_score
│       ├── clustering.py   ← Attribution des bandes + détection NLP
│       └── recommender.py  ← Logique de recommandation personnalisée
├── tests/
│   └── test_scoring.py  ← Tests unitaires du moteur
└── requirements.txt
```

## Installation

```bash
# 1. Cloner et se placer dans le dossier
git clone https://github.com/Yahia995/TOEIC-ai-service.git
cd TOEIC-ai-service

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer l'environnement
touch .env
# Éditer .env avec vos valeurs (DATABASE_URL, API_KEY)
```

## Démarrage

### Développement (SQLite, pas besoin de PostgreSQL)

```bash
# Laisser DATABASE_URL vide dans .env → SQLite automatique
uvicorn app.main:app --reload
```

### Production (PostgreSQL)

```bash
# Remplir DATABASE_URL dans .env :
# DATABASE_URL=postgresql://user:password@localhost:5432/quiz_ai
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

L'application démarre sur `http://localhost:8000`.  
Documentation interactive : `http://localhost:8000/docs`

## Tests

```bash
pytest tests/ -v
```

## Utilisation de l'API

### Enregistrer un résultat

```bash
curl -X POST http://localhost:8000/ai/quiz/result \
  -H "x-api-key: your-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "studentId": "s_501",
    "quizId": "q_99",
    "score": 55,
    "maxScore": 100,
    "timeSpentSeconds": 720,
    "totalQuizTimeSeconds": 600
  }'
```

### Obtenir des recommandations

```bash
curl http://localhost:8000/ai/recommendations/s_501 \
  -H "x-api-key: your-secret-api-key-here"
```

Réponse :
```json
{
  "studentId": "s_501",
  "recommendedQuizIds": ["q_02", "q_07", "q_03", "q_08", "q_05"]
}
```

## Paramètres ajustables

Tous les paramètres numériques sont dans `.env` — aucun chiffre n'est codé en dur dans le code :

| Variable | Défaut | Description |
|---|---|---|
| `WEIGHT_GRADE` | 0.60 | Poids de la note dans le D_score |
| `WEIGHT_TIME` | 0.25 | Poids du temps dans le D_score |
| `WEIGHT_VARIANCE` | 0.15 | Poids de l'écart-type dans le D_score |
| `THRESHOLD_EASY` | 0.35 | Seuil Facile/Moyen |
| `THRESHOLD_MEDIUM` | 0.60 | Seuil Moyen/Difficile |
| `BOOST_MIN_SCORE` | 85.0 | Score min pour déclencher le boost |
| `BOOST_MAX_TIME` | 0.85 | Temps max pour déclencher le boost |
| `TOP_N_RECOMMENDATIONS` | 5 | Nombre de quizzes recommandés |
