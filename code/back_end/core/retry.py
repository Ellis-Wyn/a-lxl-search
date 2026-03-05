"""
重试机制装饰器.

提供：
- 指数退避重试
- 随机抖动（避免雷击效应）
- 可配置的重试条件
- 重试回调
"""

import asyncio
import random
import functools
from typing import Callable, Type, Tuple, Union, Optional, Any

from .logger import get_logger

logger = get_logger(__name__)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    jitter_range: float = 0.5,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    on_retry: Optional[Callable] = None,
    raise_on_max_attempts: bool = True,
):
    """重试装饰器.

    Args:
        max_attempts: 最大重试次数（包括首次调用）
        base_delay: 基础延迟时间（秒）
        backoff_factor: 退避因子（每次重试延迟时间 = base_delay * backoff_factor^attempt）
        max_delay: 最大延迟时间（秒）
        jitter: 是否添加随机抖动
        jitter_range: 抖动范围（0-1之间，表示延迟时间的百分比）
        exceptions: 需要重试的异常类型
        on_retry: 重试前的回调函数（接收attempt, exception参数）
        raise_on_max_attempts: 达到最大重试次数后是否抛出异常

    Returns:
        装饰器函数

    Example:
        @retry(max_attempts=3, exceptions=(TimeoutError, ConnectionError))
        async def fetch_data():
            ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            """异步函数包装器."""
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt >= max_attempts:
                        # 达到最大重试次数
                        logger.warning(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            extra={
                                "function": func.__name__,
                                "attempts": max_attempts,
                                "exception_type": type(e).__name__,
                            },
                        )

                        if raise_on_max_attempts:
                            raise
                        else:
                            return None

                    # 计算延迟时间
                    delay = min(
                        base_delay * (backoff_factor ** (attempt - 1)),
                        max_delay,
                    )

                    # 添加随机抖动
                    if jitter:
                        jitter_amount = delay * jitter_range * (random.random() - 0.5) * 2
                        delay = max(0, delay + jitter_amount)

                    # 记录重试日志
                    logger.info(
                        f"Retrying function {func.__name__} (attempt {attempt + 1}/{max_attempts})",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay_seconds": round(delay, 2),
                            "exception_type": type(e).__name__,
                            "exception_message": str(e),
                        },
                    )

                    # 调用重试回调
                    if on_retry:
                        if asyncio.iscoroutinefunction(on_retry):
                            await on_retry(attempt, e)
                        else:
                            on_retry(attempt, e)

                    # 等待后重试
                    await asyncio.sleep(delay)

            # 理论上不会到这里，但保留兜底
            if last_exception and raise_on_max_attempts:
                raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """同步函数包装器."""
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt >= max_attempts:
                        logger.warning(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            extra={
                                "function": func.__name__,
                                "attempts": max_attempts,
                                "exception_type": type(e).__name__,
                            },
                        )

                        if raise_on_max_attempts:
                            raise
                        else:
                            return None

                    # 计算延迟时间
                    delay = min(
                        base_delay * (backoff_factor ** (attempt - 1)),
                        max_delay,
                    )

                    # 添加随机抖动
                    if jitter:
                        jitter_amount = delay * jitter_range * (random.random() - 0.5) * 2
                        delay = max(0, delay + jitter_amount)

                    logger.info(
                        f"Retrying function {func.__name__} (attempt {attempt + 1}/{max_attempts})",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay_seconds": round(delay, 2),
                            "exception_type": type(e).__name__,
                        },
                    )

                    # 调用重试回调
                    if on_retry:
                        on_retry(attempt, e)

                    # 等待后重试
                    import time

                    time.sleep(delay)

            if last_exception and raise_on_max_attempts:
                raise last_exception

        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class RetryPolicy:
    """重试策略配置类.

    提供预设的重试策略，便于复用。
    """

    # 数据库操作重试策略
    DATABASE = {
        "max_attempts": 3,
        "base_delay": 0.5,
        "backoff_factor": 2.0,
        "max_delay": 10.0,
        "exceptions": (Exception,),  # 数据库异常通常是通用的
    }

    # HTTP请求重试策略
    HTTP_REQUEST = {
        "max_attempts": 3,
        "base_delay": 1.0,
        "backoff_factor": 2.0,
        "max_delay": 30.0,
        "exceptions": (
            TimeoutError,
            ConnectionError,
            OSError,
        ),
    }

    # 外部API调用重试策略
    EXTERNAL_API = {
        "max_attempts": 5,
        "base_delay": 2.0,
        "backoff_factor": 2.0,
        "max_delay": 60.0,
        "exceptions": (
            TimeoutError,
            ConnectionError,
        ),
    }

    # 爬虫重试策略
    CRAWLER = {
        "max_attempts": 3,
        "base_delay": 5.0,
        "backoff_factor": 1.5,
        "max_delay": 60.0,
        "exceptions": (Exception,),
    }

    @classmethod
    def create_retry(cls, policy_name: str):
        """根据策略名称创建装饰器.

        Args:
            policy_name: 策略名称（DATABASE、HTTP_REQUEST等）

        Returns:
            retry装饰器
        """
        policy = getattr(cls, policy_name, None)
        if policy is None:
            raise ValueError(f"Unknown retry policy: {policy_name}")

        return retry(**policy)


__all__ = [
    "retry",
    "RetryPolicy",
]
