"""
=====================================================
爬虫重试服务 - Crawler Retry Service
=====================================================

核心功能：
- 指数退避重试策略
- 智能错误判断
- 重试历史记录
- 自动恢复机制

重试策略：
- 第1次失败：等待 1 分钟
- 第2次失败：等待 5 分钟
- 第3次失败：等待 15 分钟
- 超过最大重试次数：标记为最终失败

集成方式：
    from services.crawler_retry_service import CrawlerRetryService

    retry_service = CrawlerRetryService()
    result = await retry_service.execute_with_retry(
        spider_name="hengrui",
        execute_func=lambda: run_spider("hengrui")
    )

作者：A_lxl_search Team
创建日期：2026-02-04
=====================================================
"""

import asyncio
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any, List
from enum import Enum

from sqlalchemy.orm import Session

from models.crawler_execution_log import CrawlerExecutionLog
from utils.database import SessionLocal
from core.logger import get_logger
from config import settings

logger = get_logger(__name__)


class RetryStrategy(Enum):
    """重试策略枚举"""
    IMMEDIATE = "immediate"          # 立即重试（网络抖动）
    EXPONENTIAL_BACKOFF = "exponential"  # 指数退避（服务器错误）
    FIXED_DELAY = "fixed"            # 固定延迟（限流）


class RetryableError(Enum):
    """可重试的错误类型"""

    # 网络错误
    NETWORK_TIMEOUT = "timeout"
    NETWORK_CONNECTION_ERROR = "connection_error"
    NETWORK_DNS_ERROR = "dns_error"

    # HTTP错误
    HTTP_5XX = "http_5xx"            # 服务器内部错误
    HTTP_429 = "http_429"            # Too Many Requests (限流)
    HTTP_503 = "http_503"            # Service Unavailable

    # 数据库错误
    DATABASE_CONNECTION_ERROR = "db_connection_error"
    DATABASE_TIMEOUT = "db_timeout"

    # 临时错误
    TEMPORARY_ERROR = "temporary"


class CrawlerRetryService:
    """
    爬虫重试服务

    功能：
    - 指数退避重试
    - 智能错误分类
    - 重试历史记录
    - 最大重试次数控制
    """

    def __init__(
        self,
        max_attempts: int = None,
        base_delay: float = None,
        backoff_factor: float = None,
        max_delay: float = None
    ):
        """
        初始化重试服务

        Args:
            max_attempts: 最大重试次数（默认从配置读取）
            base_delay: 基础延迟（秒，默认从配置读取）
            backoff_factor: 退避因子（默认从配置读取）
            max_delay: 最大延迟（秒，默认从配置读取）
        """
        # 从配置读取参数
        self.max_attempts = max_attempts or settings.CRAWLER_RETRY_MAX_ATTEMPTS
        self.base_delay = base_delay or settings.CRAWLER_RETRY_BASE_DELAY
        self.backoff_factor = backoff_factor or settings.CRAWLER_RETRY_BACKOFF_FACTOR
        self.max_delay = max_delay or settings.CRAWLER_RETRY_MAX_DELAY

        logger.info(
            f"CrawlerRetryService initialized: "
            f"max_attempts={self.max_attempts}, "
            f"base_delay={self.base_delay}s, "
            f"backoff_factor={self.backoff_factor}, "
            f"max_delay={self.max_delay}s"
        )

    async def execute_with_retry(
        self,
        spider_name: str,
        execute_func: Callable,
        execution_service,
        trigger_type: str = "scheduler",
        execution_id: str = None
    ) -> Dict[str, Any]:
        """
        带重试地执行爬虫

        Args:
            spider_name: 爬虫名称
            execute_func: 执行函数（同步或异步）
            execution_service: 执行历史服务
            trigger_type: 触发方式
            execution_id: 执行ID（如果有）

        Returns:
            执行结果字典
        """
        attempt = 0
        last_error = None
        execution_logs = []

        while attempt < self.max_attempts:
            attempt += 1
            start_time = datetime.now()

            # 更新执行日志（重试状态）
            if execution_id and attempt > 1:
                execution_service.update_execution_log(
                    execution_id=execution_id,
                    status="retry",
                    stats={"retry_count": attempt - 1}
                )
                logger.info(f"🔄 Retry attempt {attempt - 1} for spider '{spider_name}'")

            try:
                # 执行爬虫（支持同步和异步函数）
                if asyncio.iscoroutinefunction(execute_func):
                    result = await execute_func()
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, execute_func)

                # 成功：返回结果
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                logger.info(
                    f"✅ Spider '{spider_name}' succeeded on attempt {attempt} "
                    f"({duration:.2f}s)"
                )

                return {
                    "spider_name": spider_name,
                    "success": True,
                    "attempt": attempt,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "result": result
                }

            except Exception as e:
                last_error = e
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                logger.warning(
                    f"❌ Spider '{spider_name}' failed on attempt {attempt}: {e}"
                )

                # 记录本次执行
                execution_logs.append({
                    "attempt": attempt,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "error": str(e),
                    "error_type": e.__class__.__name__
                })

                # 判断是否应该重试
                if not self.should_retry(e, attempt):
                    logger.error(
                        f"⚠️  Spider '{spider_name}' error is not retryable, "
                        f"stopping after {attempt} attempts"
                    )
                    break

                # 如果还有重试机会，等待后重试
                if attempt < self.max_attempts:
                    delay = self.calculate_retry_delay(attempt)
                    logger.info(
                        f"⏳ Waiting {delay:.1f}s before retry {attempt + 1}..."
                    )
                    await asyncio.sleep(delay)

        # 所有重试都失败
        logger.error(
            f"💀 Spider '{spider_name}' failed after {attempt} attempts. "
            f"Final error: {last_error}"
        )

        return {
            "spider_name": spider_name,
            "success": False,
            "attempt": attempt,
            "total_attempts": attempt,
            "last_error": str(last_error),
            "error_type": last_error.__class__.__name__ if last_error else None,
            "execution_logs": execution_logs
        }

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        判断是否应该重试

        Args:
            error: 异常对象
            attempt: 当前尝试次数

        Returns:
            是否应该重试
        """
        # 超过最大重试次数
        if attempt >= self.max_attempts:
            return False

        # 检查错误类型
        error_type = self._classify_error(error)

        # 不可重试的错误
        non_retryable_errors = [
            "FileNotFoundError",
            "PermissionError",
            "ValueError",
            "KeyError",
            "AttributeError",
            "TypeError",
            "ImportError",
        ]

        if error.__class__.__name__ in non_retryable_errors:
            logger.warning(f"Error '{error.__class__.__name__}' is not retryable")
            return False

        # HTTP 4xx 错误（除了 429）不重试
        error_str = str(error).lower()
        if "404" in error_str or "not found" in error_str:
            return False
        if "401" in error_str or "unauthorized" in error_str:
            return False
        if "403" in error_str or "forbidden" in error_str:
            return False

        # 默认：可重试
        return True

    def calculate_retry_delay(self, attempt: int) -> float:
        """
        计算重试延迟（指数退避）

        Args:
            attempt: 当前尝试次数（从1开始）

        Returns:
            延迟秒数

        策略：
        - attempt=1: 1分钟 (60s)
        - attempt=2: 5分钟 (300s)
        - attempt=3: 15分钟 (900s)
        """
        # 指数退避公式：base_delay * (backoff_factor ^ (attempt - 1))
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))

        # 限制最大延迟
        delay = min(delay, self.max_delay)

        return delay

    def _classify_error(self, error: Exception) -> RetryableError:
        """
        分类错误类型

        Args:
            error: 异常对象

        Returns:
            错误类型枚举
        """
        error_name = error.__class__.__name__
        error_str = str(error).lower()

        # 网络错误
        if "timeout" in error_name.lower() or "timeout" in error_str:
            return RetryableError.NETWORK_TIMEOUT
        if "connection" in error_name.lower():
            return RetryableError.NETWORK_CONNECTION_ERROR

        # HTTP错误
        if "5" in error_str:  # 5xx
            return RetryableError.HTTP_5XX
        if "429" in error_str or "too many requests" in error_str:
            return RetryableError.HTTP_429

        # 数据库错误
        if "database" in error_str or "db" in error_str:
            return RetryableError.DATABASE_CONNECTION_ERROR

        # 默认：临时错误
        return RetryableError.TEMPORARY_ERROR


# =====================================================
# 辅助函数
# =====================================================

def is_retryable_error(error: Exception) -> bool:
    """
    快速判断错误是否可重试

    Args:
        error: 异常对象

    Returns:
        是否可重试
    """
    retry_service = CrawlerRetryService()
    return retry_service.should_retry(error, attempt=1)


def calculate_backoff_delay(attempt: int) -> float:
    """
    快速计算退避延迟

    Args:
        attempt: 尝试次数

    Returns:
        延迟秒数
    """
    retry_service = CrawlerRetryService()
    return retry_service.calculate_retry_delay(attempt)


__all__ = [
    "CrawlerRetryService",
    "RetryStrategy",
    "RetryableError",
    "is_retryable_error",
    "calculate_backoff_delay",
]
