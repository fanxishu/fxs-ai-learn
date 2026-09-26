import logging as _logging
import traceback

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError

from app.core.auth import get_current_user_id_optional
from app.models.common import ApiResponse, error_response, ok_response
from app.models.report import ReportGenerateRequest
from app.repositories import (
    AnswerRecordRepository,
    ReportRepository,
    UserRepository,
)
from app.services.quiz_chain import ReportChainService

router = APIRouter(prefix="/report", tags=["report"])
_log = _logging.getLogger(__name__)


async def _persist_report_and_xp_if_logged_in(
    user_id: int | None,
    quiz_id: str,
    records_dump,
    correct_count: int,
    total_questions: int,
    accuracy_pct: int,
    report_dump,
) -> None:
    if not user_id:
        return
    try:
        uid = int(user_id)
        await AnswerRecordRepository.create(
            quiz_id=quiz_id,
            user_id=uid,
            records_json=records_dump,
            total_questions=int(total_questions),
            correct_count=int(correct_count),
            accuracy=float(accuracy_pct),
        )
        try:
            await ReportRepository.create(
                quiz_id=quiz_id,
                user_id=uid,
                report_json=report_dump,
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning("Persist report body failed (records persisted) quiz_id=%s err=%s", quiz_id, exc)
        try:
            delta_xp = 10 + (2 * int(correct_count))
            await UserRepository.add_xp(uid, delta_xp)
        except Exception as exc:  # noqa: BLE001
            _log.warning("XP accumulate failed quiz_id=%s err=%s", quiz_id, exc)
    except Exception as exc:  # noqa: BLE001
        _log.warning("Persist answer records failed (non-fatal) quiz_id=%s err=%s", quiz_id, exc)


@router.post("/generate")
async def generate_report(
    request: Request,
    user_id: int | None = Depends(get_current_user_id_optional),
) -> ApiResponse:
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
        _log.warning(
            "Report validate 4000 | loc=%s | errors=%s", loc, exc.errors()
        )
        return error_response(4000, msg)

    try:
        result = await ReportChainService.generate_report(req)
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        _log.error("Report generate 5002 FAILED | exc=%s\nTRACEBACK:\n%s", exc, tb)
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

    result_dump = result.model_dump()
    records_dump = [r.model_dump() for r in req.answer_records]
    total_questions = len(req.answer_records)
    correct_count = sum(1 for r in req.answer_records if r.is_correct)
    accuracy_pct = int(result.accuracy)
    await _persist_report_and_xp_if_logged_in(
        user_id=user_id,
        quiz_id=req.quiz_id,
        records_dump=records_dump,
        correct_count=correct_count,
        total_questions=total_questions,
        accuracy_pct=accuracy_pct,
        report_dump=result_dump,
    )

    return ok_response(result_dump, message="ok")
