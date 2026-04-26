from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db, Base
from app.schemas import QuizResultInput, RecommendationResponse
from app.services import store_quiz_result, fetch_recommendations, sync_catalog
from app.toeic_gateway import toeic_gateway

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await toeic_gateway.start()
    yield
    await toeic_gateway.stop()

app = FastAPI(
    title="Quiz AI Service",
    version="1.1.0",
    description=(
        "Moteur de catégorisation de quizzes par difficulté "
        "et de recommandation personnalisée par étudiant."
    ),
    lifespan=lifespan,
)

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API manquante. Fournir le header 'x-api-key'.",
        )
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide.",
        )
    return api_key

@app.post(
    "/ai/quiz/result",
    status_code=status.HTTP_200_OK,
    summary="Enregistrer un résultat de quiz",
    dependencies=[Depends(verify_api_key)],
)
async def post_quiz_result(
    payload: QuizResultInput,
    db: Session = Depends(get_db),
):
    await store_quiz_result(payload=payload, db=db)
    return {"status": "stored"}


@app.get(
    "/ai/recommendations/{studentId}",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtenir les quizzes recommandés pour un étudiant",
    dependencies=[Depends(verify_api_key)],
)
def get_recommendations_route(
    studentId: str,
    db: Session = Depends(get_db),
):
    return fetch_recommendations(student_id=studentId, db=db)


@app.post(
    "/ai/catalog/sync",
    status_code=status.HTTP_200_OK,
    summary="Synchroniser le catalogue depuis le backend TOEIC",
    description=(
        "Appelle get_teacher_quizzes() via le python-sdk et pré-peuple "
        "QuizCatalog avec les titres et textes des questions. "
        "À appeler au premier déploiement et après chaque ajout de quiz."
    ),
    dependencies=[Depends(verify_api_key)],
)
async def post_catalog_sync(db: Session = Depends(get_db)):
    return await sync_catalog(db=db)

@app.get("/health", include_in_schema=False)
def health_check():
    return {
        "status": "ok",
        "sdk_connected": toeic_gateway.is_available,
    }
