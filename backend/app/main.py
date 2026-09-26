import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.db import create_db_pool, create_tables_if_not_exists, close_db_pool
from app.core.exceptions import FishAIException
from app.core.logging import setup_logging
from app.api.v1.routes import api_router
from app.models.common import error_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_pool()
    await create_tables_if_not_exists()
    setup_logging()
    yield
    await close_db_pool()


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
        import traceback as _tb
        msg = "参数校验失败"
        loc = "input"
        try:
            first_err = exc.errors()[0] if exc.errors() else {}
            loc = ".".join(str(x) for x in first_err.get("loc", []) if x != "body") or "input"
            msg = f"参数 {loc} 不合法"
        except Exception:  # noqa: BLE001
            pass
        logging.getLogger(__name__).warning(
            "RequestValidation 4000 | url=%s | loc=%s | errors=%s\nTRACEBACK:\n%s",
            request.url, loc, exc.errors(), _tb.format_exc(),
        )
        body = error_response(4000, msg).model_dump()
        body.setdefault("data", {})
        body["data"] = {
            "debug_info": {
                "exc_type": "RequestValidationError",
                "exc_msg": msg,
                "loc": loc,
                "traceback_tail": _tb.format_exc().strip().splitlines()[-6:],
            }
        }
        return JSONResponse(status_code=200, content=body)

    @app.exception_handler(FishAIException)
    async def _fish_exception_handler(request: Request, exc: FishAIException):
        import traceback as _tb
        logging.getLogger(__name__).exception(
            "FishAIException caught | url=%s | code=%s | msg=%s",
            request.url, exc.code, exc.message,
        )
        body = error_response(exc.code, exc.message).model_dump()
        body.setdefault("data", {})
        body["data"] = {
            "debug_info": {
                "exc_type": type(exc).__name__,
                "exc_msg": exc.message,
                "code": exc.code,
                "traceback_tail": _tb.format_exc().strip().splitlines()[-6:],
            }
        }
        return JSONResponse(status_code=200, content=body)

    @app.exception_handler(Exception)
    async def _uncaught_exception_handler(request: Request, exc: Exception):
        import traceback as _tb
        logging.getLogger(__name__).exception(
            "Uncaught exception on %s | exc=%s", request.url, type(exc).__name__,
        )
        body = error_response(5000, "服务内部错误，请稍后重试").model_dump()
        body.setdefault("data", {})
        body["data"] = {
            "debug_info": {
                "exc_type": type(exc).__name__,
                "exc_msg": str(exc),
                "traceback_tail": _tb.format_exc().strip().splitlines()[-6:],
            }
        }
        return JSONResponse(status_code=200, content=body)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
