from fastapi import APIRouter, Depends
from fastapi_injector import Injected

from app.auth.dependencies import auth
from app.schemas.report import TopicsReport
from app.services.conversations import ConversationService

router = APIRouter()


@router.get(
    "/topics-report",
    response_model=TopicsReport,
    summary="Counts per topics report",
    description="Returns a map of topic→count across all conversation analyses.",
    dependencies=[
        Depends(auth),
    ],
)
async def topics_report(
    service: ConversationService = Injected(ConversationService),
) -> TopicsReport:
    return await service.get_topics_count()
