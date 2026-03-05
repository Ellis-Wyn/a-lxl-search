"""
测试熔断器.

验证：
- 状态机正确转换
- 失败阈值触发
- 自动恢复机制
- 成功后重置
"""

import asyncio
import pytest
import time

from core.circuit_breaker import (
    CircuitState,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerManager,
    get_circuit_breaker_manager,
)


class TestCircuitBreaker:
    """测试熔断器."""

    def test_initial_state(self):
        """测试初始状态."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=30,
        )
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_closed_state_on_success(self):
        """测试CLOSED状态下成功."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=30,
        )

        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_closed_to_open_transition(self):
        """测试从CLOSED到OPEN的转换."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=30,
        )

        async def failing_func():
            raise ValueError("Failure")

        # 触发3次失败
        for _ in range(3):
            try:
                await breaker.call(failing_func)
            except ValueError:
                pass

        # 应该转换为OPEN状态
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_state_rejects_requests(self):
        """测试OPEN状态拒绝请求."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=30,
        )

        async def failing_func():
            raise ValueError("Failure")

        # 触发2次失败
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except ValueError:
                pass

        # 应该是OPEN状态
        assert breaker.state == CircuitState.OPEN

        # 新的请求应该被拒绝
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(lambda: asyncio.sleep(0))

    @pytest.mark.asyncio
    async def test_open_to_half_open_transition(self):
        """测试从OPEN到HALF_OPEN的转换."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms
        )

        async def failing_func():
            raise ValueError("Failure")

        # 触发失败
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # 等待恢复超时
        await asyncio.sleep(0.15)

        # 下一次请求应该转换为HALF_OPEN
        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self):
        """测试HALF_OPEN状态下成功后转为CLOSED."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,
        )

        async def failing_func():
            raise ValueError("Failure")

        # 触发失败
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # 等待恢复超时
        await asyncio.sleep(0.15)

        # 连续成功两次
        async def success_func():
            return "success"

        await breaker.call(success_func)
        assert breaker.state == CircuitState.HALF_OPEN

        await breaker.call(success_func)
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        """测试HALF_OPEN状态下失败后重新转为OPEN."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,
        )

        async def failing_func():
            raise ValueError("Failure")

        # 触发失败
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # 等待恢复超时
        await asyncio.sleep(0.15)

        # 第一次成功
        async def success_func():
            return "success"

        await breaker.call(success_func)
        assert breaker.state == CircuitState.HALF_OPEN

        # 第二次失败
        try:
            await breaker.call(failing_func)
        except ValueError:
            pass

        assert breaker.state == CircuitState.OPEN

    def test_reset(self):
        """测试重置熔断器."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=30,
        )
        breaker._state = CircuitState.OPEN
        breaker._failure_count = 5

        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_decorator_usage(self):
        """测试装饰器用法."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=30,
        )

        @breaker
        async def test_func():
            return "success"

        # 需要在async上下文中测试
        assert asyncio.iscoroutinefunction(test_func)


class TestCircuitBreakerManager:
    """测试熔断器管理器."""

    def test_create_breaker(self):
        """测试创建熔断器."""
        manager = CircuitBreakerManager()
        breaker = manager.get_or_create(
            "test",
            failure_threshold=5,
            recovery_timeout=30,
        )
        assert breaker is not None
        assert breaker.name == "test"

    def test_get_existing_breaker(self):
        """测试获取已存在的熔断器."""
        manager = CircuitBreakerManager()
        breaker1 = manager.get_or_create("test")
        breaker2 = manager.get_or_create("test")
        assert breaker1 is breaker2

    def test_get_nonexistent_breaker(self):
        """测试获取不存在的熔断器."""
        manager = CircuitBreakerManager()
        breaker = manager.get("nonexistent")
        assert breaker is None

    def test_reset_all(self):
        """测试重置所有熔断器."""
        manager = CircuitBreakerManager()
        breaker1 = manager.get_or_create("test1")
        breaker2 = manager.get_or_create("test2")

        breaker1._state = CircuitState.OPEN
        breaker2._state = CircuitState.OPEN

        manager.reset_all()

        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED

    def test_get_states(self):
        """测试获取所有状态."""
        manager = CircuitBreakerManager()
        manager.get_or_create("test1")
        manager.get_or_create("test2")

        states = manager.get_states()
        assert "test1" in states
        assert "test2" in states
        assert "state" in states["test1"]
        assert "failure_count" in states["test1"]


class TestGlobalCircuitBreakerManager:
    """测试全局熔断器管理器."""

    def test_get_global_manager(self):
        """测试获取全局管理器."""
        manager = get_circuit_breaker_manager()
        assert manager is not None
        assert isinstance(manager, CircuitBreakerManager)
