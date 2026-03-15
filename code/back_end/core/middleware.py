"""
FastAPI中间件.

提供：
- 请求日志中间件（记录请求/响应）
- 上下文注入中间件（request_id、user_id等）
- 性能监控中间件
- 日志脱敏
"""

import contextvars
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logger import get_logger, bind_context, unbind_context

logger = get_logger(__name__)

# 上下文变量
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """请求上下文中间件.

    功能：
    1. 生成request_id
    2. 记录请求开始时间
    3. 注入上下文变量
    4. 记录请求/响应日志
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        skip_paths: list[str] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ):
        """初始化中间件.

        Args:
            app: ASGI应用
            skip_paths: 跳过日志记录的路径列表（如健康检查）
            log_request_body: 是否记录请求体
            log_response_body: 是否记录响应体
        """
        super().__init__(app)
        self.skip_paths = set(skip_paths or ["/health", "/metrics", "/docs", "/redoc"])
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求.

        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            FastAPI响应对象
        """
        # 生成request_id
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)

        # 记录请求开始时间
        start_time = time.time()

        # 绑定上下文
        bind_context(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        # 跳过健康检查等路径的日志
        skip_log = request.url.path in self.skip_paths

        if not skip_log:
            # 记录请求信息
            log_data = {
                "type": "request",
                "path": request.url.path,
                "method": request.method,
                "client": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }

            # 添加查询参数
            if request.query_params:
                log_data["query_params"] = dict(request.query_params)

            # 记录请求体（如果启用）
            if self.log_request_body:
                # 注意：读取请求体后需要重置，否则会导致后续处理无法读取
                # 这里简化处理，实际使用时需要更复杂的逻辑
                pass

            logger.info("Incoming request", extra=log_data)

        try:
            # 调用下一个处理器
            response = await call_next(request)

            # 计算耗时
            process_time = (time.time() - start_time) * 1000  # 转换为毫秒

            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(f"{process_time:.2f}")

            if not skip_log:
                # 记录响应信息
                log_data = {
                    "type": "response",
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time, 2),
                }

                # 根据状态码决定日志级别
                if response.status_code >= 500:
                    logger.error("Request completed with server error", extra=log_data)
                elif response.status_code >= 400:
                    logger.warning("Request completed with client error", extra=log_data)
                else:
                    logger.info("Request completed successfully", extra=log_data)

            return response

        except Exception as e:
            # 记录未处理的异常
            process_time = (time.time() - start_time) * 1000
            logger.error(
                "Request failed with unhandled exception",
                extra={
                    "type": "error",
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "process_time_ms": round(process_time, 2),
                },
                exc_info=True,
            )
            raise

        finally:
            # 清理上下文
            unbind_context("request_id", "path", "method")


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    """性能监控中间件.

    功能：
    1. 记录慢查询
    2. 记录异常状态码
    3. 性能指标统计
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        slow_request_threshold: float = 1000.0,  # 慢请求阈值（毫秒）
    ):
        """初始化中间件.

        Args:
            app: ASGI应用
            slow_request_threshold: 慢请求阈值（毫秒）
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求."""
        start_time = time.time()

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000

        # 检测慢请求
        if process_time > self.slow_request_threshold:
            logger.warning(
                "Slow request detected",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "process_time_ms": round(process_time, 2),
                    "threshold_ms": self.slow_request_threshold,
                },
            )

        return response


def setup_cors(app) -> None:
    """配置CORS中间件.

    Args:
        app: FastAPI应用实例
    """
    from config import settings

    # 生产环境应该限制允许的来源
    allow_origins = ["*"] if settings.DEBUG else [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://lxlsearch.com",  # 生产环境自定义域名
        "https://www.lxlsearch.com",  # www子域名
        # Vercel自动分配的域名（如果有）
        # "https://your-project.vercel.app",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    logger.info(f"CORS middleware configured: allow_origins={allow_origins}")


def setup_middlewares(app) -> None:
    """配置所有中间件.

    Args:
        app: FastAPI应用实例
    """
    # CORS中间件（最先添加）
    setup_cors(app)

    # 请求上下文中间件
    app.add_middleware(
        RequestContextMiddleware,
        skip_paths=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
        log_request_body=False,  # 生产环境通常不记录请求体
        log_response_body=False,
    )

    # 性能监控中间件
    app.add_middleware(
        PerformanceMonitorMiddleware,
        slow_request_threshold=1000.0,  # 1秒
    )

    logger.info("Middlewares configured successfully")


__all__ = [
    "RequestContextMiddleware",
    "PerformanceMonitorMiddleware",
    "setup_cors",
    "setup_middlewares",
    "request_id_var",
    "user_id_var",
]
