from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db, Base
from app.schemas import QuizResultInput, RecommendationResponse
from app.services import store_quiz_result, fetch_recommendations

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Quiz AI Service",
    version="1.1.0",
    description=(
        "Moteur de catégorisation de quizzes par difficulté "
        "et de recommandation personnalisée par étudiant."
    ),
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
    description=(
        "Stocke le résultat d'un étudiant sur un quiz, puis recalcule "
        "automatiquement le D_score et la bande de difficulté du quiz concerné."
    ),
    dependencies=[Depends(verify_api_key)],
)
def post_quiz_result(
    payload: QuizResultInput,
    db: Session = Depends(get_db),
):
    store_quiz_result(payload=payload, db=db)
    return {"status": "stored"}


@app.get(
    "/ai/recommendations/{studentId}",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtenir les quizzes recommandés pour un étudiant",
    description=(
        "Calcule le profil de l'étudiant (S_score, niveau, boost), "
        "identifie les groupes cibles, et retourne les quiz_ids triés "
        "par adéquation décroissante."
    ),
    dependencies=[Depends(verify_api_key)],
)
def get_recommendations_route(
    studentId: str,
    db: Session = Depends(get_db),
):
    return fetch_recommendations(student_id=studentId, db=db)

@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}
