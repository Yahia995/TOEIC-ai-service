# TOEIC AI Service

AI-powered quiz difficulty categorization and personalized recommendation engine for the TOEIC Platform.

## How it works

When a student submits a quiz result, the service stores it and recomputes the quiz's `D_score` — a difficulty index derived from the grade history, score variance, and time usage of all attempts. When a recommendation is requested, the service builds a `S_score` for the student using the same formula, matches them to the right difficulty band, and returns the 5 most relevant quizzes they haven't taken yet.

The service integrates with the [TOEIC python-sdk](../python-sdk) to enrich the quiz catalog with real question text from the backend, enabling proper NLP-based type detection (grammar vs vocabulary) instead of relying only on statistical heuristics.

## Stack

- **FastAPI** — async HTTP framework
- **PostgreSQL** — production database (SQLite for local dev)
- **SQLAlchemy** — ORM
- **Pydantic** — request/response validation
- **toeic-client** — python-sdk for TOEIC backend integration

## Project structure

```
TOEIC_ai-service/
├── app/
│   ├── main.py             ← FastAPI app, routes, lifespan
│   ├── config.py           ← All settings via environment variables
│   ├── database.py         ← SQLAlchemy engine and session
│   ├── models.py           ← Database tables
│   ├── schemas.py          ← Pydantic schemas
│   ├── services.py         ← Business logic
│   ├── toeic_gateway.py    ← Singleton AsyncToeicClient wrapper
│   └── engine/
│       ├── scoring.py      ← D_score / S_score calculation
│       ├── clustering.py   ← Difficulty bands + NLP type detection
│       └── recommender.py  ← Recommendation logic
├── tests/
│   └── test_scoring.py     ← Unit tests for the scoring engine
├── conftest.py             ← Adds project root to sys.path for pytest
├── pyproject.toml          ← pytest configuration
├── requirements.txt
└── .env.example
```

## Installation

```bash
# 1. Use Python 3.11 (required — psycopg2-binary has no wheel for 3.14)
python3.11 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your values — see Configuration section below
```

## Running locally

### Without TOEIC backend (standalone, SQLite)

```bash
# Leave DATABASE_URL and TOEIC_TEACHER_TOKEN empty in .env
uvicorn app.main:app --reload
```

The service starts in degraded mode — scoring and recommendations work fully,
but quiz catalog enrichment (titles, question text) is skipped until a token is set.

### With TOEIC backend connected

```bash
# Fill in .env:
# TOEIC_BACKEND_URL=http://localhost:3000/api/v1
# TOEIC_TEACHER_TOKEN=your-teacher-token

uvicorn app.main:app --reload
```

### With Docker (full stack including PostgreSQL)

```bash
docker compose up --build
```

App: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

## Running tests

Always use the venv's pytest, not the system one:

```bash
.venv/bin/pytest tests/ -v
```

## API reference

### `POST /ai/quiz/result`

Records a student quiz result and recomputes the quiz difficulty score.
If the quiz is new, the service calls the TOEIC backend via the SDK to
fetch its title and question text for NLP type detection.

```bash
curl -X POST http://localhost:8000/ai/quiz/result \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "studentId": "s_501",
    "quizId":    "q_99",
    "score":               55,
    "maxScore":           100,
    "timeSpentSeconds":   720,
    "totalQuizTimeSeconds": 600
  }'
```

### `GET /ai/recommendations/{studentId}`

Returns up to 5 recommended quiz IDs for a student, ordered by fit quality.

```bash
curl http://localhost:8000/ai/recommendations/s_501 \
  -H "x-api-key: your-api-key"
```

```json
{
  "studentId": "s_501",
  "recommendedQuizIds": ["q_02", "q_07", "q_03", "q_08", "q_05"]
}
```

### `POST /ai/catalog/sync`

Pre-populates the quiz catalog by calling `get_teacher_quizzes()` via the SDK.
Run this once at first deployment, and again whenever new quizzes are added to the backend.
Without it, quizzes only enter the catalog when a student result arrives.

```bash
curl -X POST http://localhost:8000/ai/catalog/sync \
  -H "x-api-key: your-api-key"
```

```json
{ "synced": 12, "skipped": 3, "sdk_available": true }
```

### `GET /health`

```json
{ "status": "ok", "sdk_connected": true }
```

`sdk_connected: false` means the TOEIC backend is unreachable or the token is missing.
The service still works — recommendations just won't include quiz titles or NLP types.

## Configuration

All settings live in `.env`. No hardcoded values anywhere in the code.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | SQLite | PostgreSQL connection string for production |
| `API_KEY` | `dev-key` | Key required in `x-api-key` header |
| `TOEIC_BACKEND_URL` | `http://localhost:3000/api/v1` | TOEIC backend base URL |
| `TOEIC_TEACHER_TOKEN` | _(empty)_ | JWT from `client.login()` — enables SDK enrichment |
| `TOEIC_SDK_ENABLED` | `true` | Set to `false` to fully disable SDK calls |
| `WEIGHT_GRADE` | `0.60` | Grade contribution in D_score formula |
| `WEIGHT_TIME` | `0.25` | Time contribution in D_score formula |
| `WEIGHT_VARIANCE` | `0.15` | Variance contribution in D_score formula |
| `THRESHOLD_EASY` | `0.35` | D_score below this → Easy |
| `THRESHOLD_MEDIUM` | `0.60` | D_score below this → Medium, else Hard |
| `BOOST_MIN_SCORE` | `85.0` | Score threshold for the boost rule |
| `BOOST_MAX_TIME` | `0.85` | Time ratio threshold for the boost rule |
| `TOP_N_RECOMMENDATIONS` | `5` | Max quizzes returned per recommendation |
| `COLD_START_MIN_ATTEMPTS` | `5` | Min attempts before σ is included in D_score |
| `CONSOLIDATION_SCORE_THRESHOLD` | `75.0` | Below this score → quiz flagged for consolidation |

## Deployment

See [`infra/azure.md`](infra/azure.md) for Azure Container Apps.

The CI/CD pipeline in `.github/workflows/` builds the Docker image on every push
to `main`, pushes it to GHCR, and deploys automatically to the configured platform.
