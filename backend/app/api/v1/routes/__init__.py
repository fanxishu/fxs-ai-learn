from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.quiz import router as quiz_router
from app.api.v1.routes.report import router as report_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(quiz_router)
api_router.include_router(report_router)

__all__ = ["api_router"]
