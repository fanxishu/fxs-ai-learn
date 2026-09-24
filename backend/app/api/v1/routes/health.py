from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "project_name": settings.PROJECT_NAME,
        "use_mock_llm": settings.USE_MOCK_LLM,
    }
