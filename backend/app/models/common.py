from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="ok", description="业务信息")
    data: Optional[T] = Field(default=None, description="业务数据")


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


def ok_response(data: Any = None, message: str = "ok") -> ApiResponse[Any]:
    return ApiResponse[Any](code=0, message=message, data=data)


def error_response(
    code: int, message: str, data: Any = None
) -> ApiResponse[Any]:
    return ApiResponse[Any](code=code, message=message, data=data)
