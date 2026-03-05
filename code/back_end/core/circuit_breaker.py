"""
熔断器实现.

提供：
- 状态机：CLOSED → OPEN → HALF_OPEN
- 失败阈值触发
- 自动恢复机制
- 事件回调
"""

import asyncio
import time
from enum import Enum, auto
from typing import Callable, Optional, Any

from .logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """熔断器状态."""

    CLOSED = auto()  # 关闭状态：正常工作
    OPEN = auto()  # 开启状态：熔断触发，拒绝请求
    HALF_OPEN = auto()  # 半开状态：尝试恢复


class CircuitBreaker:
    """熔断器类.

    保护下游服务不被持续失败的请求压垮。

    Example:
        breaker = CircuitBreaker(
            name="pubmed_api",
            failure_threshold=5,
            recovery_timeout=30,
        )

        @breaker
        async def call_api():
            ...
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
        on_state_change: Optional[Callable] = None,
    ):
        """初始化熔断器.

        Args:
            name: 熔断器名称（用于日志和监控）
            failure_threshold: 失败阈值（连续失败多少次后触发熔断）
            recovery_timeout: 恢复超时时间（秒），
                             从OPEN转为HALF_OPEN的等待时间
            expected_exception: 触发熔断的异常类型
            on_state_change: 状态变化回调函数
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.on_state_change = on_state_change

        # 状态
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._success_count = 0  # HALF_OPEN状态下的成功次数
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """获取当前状态."""
        return self._state

    @property
    def failure_count(self) -> int:
        """获取当前失败计数."""
        return self._failure_count

    @property
    def last_failure_time(self) -> Optional[float]:
        """获取最后一次失败时间."""
        return self._last_failure_time

    def _transition_to(self, new_state: CircuitState) -> None:
        """状态转换.

        Args:
            new_state: 新状态
        """
        old_state = self._state
        self._state = new_state

        logger.info(
            f"Circuit breaker '{self.name}' state transition",
            extra={
                "circuit_breaker": self.name,
                "old_state": old_state.name,
                "new_state": new_state.name,
                "failure_count": self._failure_count,
            },
        )

        # 调用状态变化回调
        if self.on_state_change:
            self.on_state_change(self, old_state, new_state)

    def _on_success(self) -> None:
        """处理成功情况."""
        if self._state == CircuitState.CLOSED:
            # CLOSED状态下，重置失败计数
            self._failure_count = 0

        elif self._state == CircuitState.HALF_OPEN:
            # HALF_OPEN状态下，连续成功后转为CLOSED
            self._success_count += 1
            if self._success_count >= 2:  # 连续2次成功后恢复
                self._success_count = 0
                self._transition_to(CircuitState.CLOSED)

    def _on_failure(self) -> None:
        """处理失败情况."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.CLOSED:
            # CLOSED状态下，检查是否需要触发熔断
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

        elif self._state == CircuitState.HALF_OPEN:
            # HALF_OPEN状态下，任何失败都会重新触发熔断
            self._success_count = 0
            self._transition_to(CircuitState.OPEN)

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """调用受保护的函数.

        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerOpenError: 熔断器开启时拒绝请求
            Exception: 函数执行时的异常
        """
        async with self._lock:
            # 检查是否需要从OPEN转为HALF_OPEN
            if (
                self._state == CircuitState.OPEN
                and self._last_failure_time is not None
                and time.time() - self._last_failure_time >= self.recovery_timeout
            ):
                self._transition_to(CircuitState.HALF_OPEN)

            # 检查熔断器状态
            if self._state == CircuitState.OPEN:
                logger.warning(
                    f"Circuit breaker '{self.name}' is OPEN, rejecting request",
                    extra={
                        "circuit_breaker": self.name,
                        "failure_count": self._failure_count,
                    },
                )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN",
                    circuit_breaker=self.name,
                )

        # 执行函数
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
        except Exception as e:
            # 非预期的异常不触发熔断
            logger.error(
                f"Unexpected exception in circuit breaker '{self.name}'",
                extra={
                    "circuit_breaker": self.name,
                    "exception_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    def __call__(self, func: Callable) -> Callable:
        """装饰器模式."""

        async def async_wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            return asyncio.run(self.call(func, *args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    def reset(self) -> None:
        """重置熔断器状态（用于测试或手动恢复）."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._success_count = 0

        logger.info(
            f"Circuit breaker '{self.name}' has been reset",
            extra={"circuit_breaker": self.name},
        )


class CircuitBreakerOpenError(Exception):
    """熔断器开启异常."""

    def __init__(self, message: str, circuit_breaker: str):
        """初始化异常.

        Args:
            message: 错误消息
            circuit_breaker: 熔断器名称
        """
        super().__init__(message)
        self.circuit_breaker = circuit_breaker


class CircuitBreakerManager:
    """熔断器管理器.

    集中管理多个熔断器实例。

    Example:
        manager = CircuitBreakerManager()

        # 获取或创建熔断器
        pubmed_breaker = manager.get_or_create(
            "pubmed_api",
            failure_threshold=5,
            recovery_timeout=30,
        )
    """

    def __init__(self):
        """初始化管理器."""
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        **kwargs,
    ) -> CircuitBreaker:
        """获取或创建熔断器.

        Args:
            name: 熔断器名称
            **kwargs: 熔断器配置参数

        Returns:
            CircuitBreaker实例
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name, **kwargs)
            logger.info(f"Created circuit breaker: {name}")

        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """获取熔断器.

        Args:
            name: 熔断器名称

        Returns:
            CircuitBreaker实例，如果不存在则返回None
        """
        return self._breakers.get(name)

    def reset_all(self) -> None:
        """重置所有熔断器."""
        for breaker in self._breakers.values():
            breaker.reset()

        logger.info("All circuit breakers have been reset")

    def get_states(self) -> dict[str, dict]:
        """获取所有熔断器的状态.

        Returns:
            状态字典
        """
        return {
            name: {
                "state": breaker.state.name,
                "failure_count": breaker.failure_count,
                "last_failure_time": breaker.last_failure_time,
            }
            for name, breaker in self._breakers.items()
        }


# 全局熔断器管理器实例
_global_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """获取全局熔断器管理器.

    Returns:
        CircuitBreakerManager实例
    """
    return _global_manager


__all__ = [
    "CircuitState",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitBreakerManager",
    "get_circuit_breaker_manager",
]
