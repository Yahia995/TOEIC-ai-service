import logging
from toeic_client import AsyncToeicClient, AuthError, NotFoundError, ApiError
from app.config import settings

logger = logging.getLogger(__name__)


class ToeicGateway:

    def __init__(self) -> None:
        self._client: AsyncToeicClient | None = None

    async def start(self) -> None:
        if not settings.toeic_sdk_enabled:
            logger.info("TOEIC SDK disabled - gateway running in degraded mode.")
            return

        if not settings.toeic_teacher_token:
            logger.warning(
                "TOEIC_TEACHER_TOKEN is empty - gateway disabled. "
                "Set the token in .env to enable quiz metadata enrichment."
            )
            return

        self._client = AsyncToeicClient(
            base_url=settings.toeic_backend_url,
            token=settings.toeic_teacher_token,
        )
        logger.info("ToeicGateway connected to %s", settings.toeic_backend_url)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("ToeicGateway disconnected.")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def fetch_quiz_details(self, quiz_id: str) -> dict | None:
        if not self.is_available:
            return None

        try:
            quiz = await self._client.get_quiz(quiz_id)
            question_text = None
            if quiz.questions:
                question_text = " ".join(
                    q.prompt for q in quiz.questions if q.prompt
                )
            return {
                "title": quiz.title,
                "question_text": question_text,
            }
        except NotFoundError:
            logger.warning("Quiz %s not found in TOEIC backend.", quiz_id)
            return None
        except (AuthError, ApiError) as e:
            logger.error("SDK error fetching quiz %s: %s", quiz_id, e)
            return None

    async def fetch_all_quizzes(self) -> list[dict]:
        if not self.is_available:
            return []

        try:
            quizzes = await self._client.get_teacher_quizzes()
            result = []
            for q in quizzes:
                question_text = None
                if q.questions:
                    question_text = " ".join(
                        qs.prompt for qs in q.questions if qs.prompt
                    )
                result.append({
                    "quiz_id": q.id,
                    "title": q.title,
                    "question_text": question_text,
                })
            return result
        except (AuthError, ApiError) as e:
            logger.error("SDK error fetching quiz list: %s", e)
            return []

toeic_gateway = ToeicGateway()
