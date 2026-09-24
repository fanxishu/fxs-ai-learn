from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import FishAIException
from app.core.logging import setup_logging
from app.api.v1.routes import api_router
from app.models.common import error_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
    )

    if settings.BACKEND_CORS_ORIGINS:
        origins = (
            settings.BACKEND_CORS_ORIGINS.split(",")
            if "," in settings.BACKEND_CORS_ORIGINS
            else [settings.BACKEND_CORS_ORIGINS]
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        msg = "参数校验失败"
        try:
            first_err = exc.errors()[0] if exc.errors() else {}
            loc = ".".join(str(x) for x in first_err.get("loc", []) if x != "body") or "input"
            msg = f"参数 {loc} 不合法"
        except Exception:  # noqa: BLE001
            pass
        return JSONResponse(
            status_code=200,
            content=error_response(4000, msg).model_dump(),
        )

    @app.exception_handler(FishAIException)
    async def _fish_exception_handler(request: Request, exc: FishAIException):
        return JSONResponse(
            status_code=200,
            content=error_response(exc.code, exc.message).model_dump(),
        )

    @app.exception_handler(Exception)
    async def _uncaught_exception_handler(request: Request, exc: Exception):
        import logging
        logging.getLogger(__name__).exception("Uncaught exception on %s", request.url)
        return JSONResponse(
            status_code=200,
            content=error_response(5000, "服务内部错误，请稍后重试").model_dump(),
        )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
