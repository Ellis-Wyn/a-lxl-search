"""
全局异常处理器.

为FastAPI应用注册全局异常处理器，统一错误响应格式。
"""

import contextvars
from typing import Union

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from .exceptions import BaseAppException, ErrorCode
from .logger import get_logger

# 上下文变量用于传递request_id
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

logger = get_logger(__name__)


async def base_app_exception_handler(
    request: Request, exc: BaseAppException
) -> JSONResponse:
    """处理应用自定义异常.

    Args:
        request: FastAPI请求对象
        exc: 应用异常

    Returns:
        JSON格式的错误响应
    """
    request_id = request_id_var.get()
    status_code = exc.status_code

    # 构建错误响应
    error_response = exc.to_dict()
    error_response["request_id"] = request_id

    # 记录错误日志
    logger.error(
        f"Application error: {exc.error_code.value} - {exc.message}",
        extra={
            "error_code": exc.error_code.value,
            "error_id": exc.error_id,
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "detail": exc.detail,
        },
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response,
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """处理Pydantic验证错误.

    Args:
        request: FastAPI请求对象
        exc: 验证错误

    Returns:
        JSON格式的错误响应
    """
    request_id = request_id_var.get()

    # 提取验证错误详情
    errors = []
    if isinstance(exc, RequestValidationError):
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

    # 构建错误响应
    error_response = {
        "error_code": ErrorCode.VALIDATION_ERROR.value,
        "message": "请求参数验证失败",
        "request_id": request_id,
        "detail": {"errors": errors},
    }

    # 记录警告日志
    logger.warning(
        f"Validation error: {len(errors)} field(s)",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "errors": errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response,
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """处理SQLAlchemy数据库异常.

    Args:
        request: FastAPI请求对象
        exc: SQLAlchemy异常

    Returns:
        JSON格式的错误响应
    """
    request_id = request_id_var.get()

    # 生产环境隐藏数据库错误详情
    error_message = "数据库操作失败，请稍后重试"

    error_response = {
        "error_code": ErrorCode.DATABASE_QUERY_ERROR.value,
        "message": error_message,
        "request_id": request_id,
    }

    # 记录错误日志（包含完整的数据库错误）
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常.

    Args:
        request: FastAPI请求对象
        exc: 未捕获的异常

    Returns:
        JSON格式的错误响应
    """
    request_id = request_id_var.get()

    # 生产环境隐藏详细错误信息
    error_message = "服务器内部错误，请稍后重试"

    error_response = {
        "error_code": ErrorCode.INTERNAL_SERVER_ERROR.value,
        "message": error_message,
        "request_id": request_id,
    }

    # 记录错误日志
    logger.bind(
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
    ).error(f"Unhandled exception: {type(exc).__name__}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )


def register_exception_handlers(app) -> None:
    """注册所有异常处理器到FastAPI应用.

    Args:
        app: FastAPI应用实例
    """
    # 自定义应用异常
    app.add_exception_handler(BaseAppException, base_app_exception_handler)

    # Pydantic验证错误
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # SQLAlchemy数据库异常
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # 通用异常处理器（兜底）
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered successfully")
