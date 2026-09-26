from fastapi import APIRouter, Request
from pydantic import ValidationError
import traceback

from app.models.common import ApiResponse, error_response, ok_response
from app.models.report import ReportGenerateRequest
from app.services.quiz_chain import ReportChainService

router = APIRouter(prefix="/report", tags=["report"])


@router.post("/generate")
async def generate_report(request: Request) -> ApiResponse:
    try:
        raw = await request.json()
    except Exception:
        return error_response(4000, "请求体必须是合法的 JSON")

    if not isinstance(raw, dict):
        return error_response(4000, "请求体必须是 JSON 对象")

    try:
        req = ReportGenerateRequest.model_validate(raw)
    except ValidationError as exc:
        msg = "参数校验失败"
        loc = "input"
        try:
            first_err = exc.errors()[0] if exc.errors() else {}
            loc = ".".join(str(x) for x in first_err.get("loc", [])) or "input"
            msg = f"参数 {loc} 不合法"
        except Exception:  # noqa: BLE001
            pass
        import logging
        logging.getLogger(__name__).warning(
            "Report validate 4000 | loc=%s | errors=%s", loc, exc.errors()
        )
        return error_response(4000, msg)

    try:
        result = await ReportChainService.generate_report(req)
    except Exception as exc:  # noqa: BLE001
        import logging
        log = logging.getLogger(__name__)
        tb = traceback.format_exc()
        log.error("Report generate 5002 FAILED | exc=%s\nTRACEBACK:\n%s", exc, tb)
        try:
            debug_excerpt = tb.strip().splitlines()[-6:]
        except Exception:  # noqa: BLE001
            debug_excerpt = [str(exc)]
        return error_response(
            5002,
            "生成报告失败，请重试",
            debug_info={
                "exc_type": type(exc).__name__,
                "exc_msg": str(exc),
                "traceback_tail": debug_excerpt,
            },
        )

    return ok_response(result.model_dump(), message="ok")
