"""
测试重试机制.

验证：
- 重试装饰器正确工作
- 指数退避正确计算
- 最大重试次数限制
- 异步和同步函数支持
"""

import asyncio
import pytest

from core.retry import retry, RetryPolicy


class TestRetryDecorator:
    """测试重试装饰器."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """测试首次成功."""
        call_count = 0

        @retry(max_attempts=3)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_until_success(self):
        """测试重试直到成功."""
        call_count = 0

        @retry(max_attempts=3, exceptions=(ValueError,))
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Not yet")
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """测试超过最大重试次数."""
        @retry(max_attempts=3, exceptions=(ValueError,), raise_on_max_attempts=True)
        async def always_failing_function():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await always_failing_function()

    @pytest.mark.asyncio
    async def test_return_none_on_failure(self):
        """测试失败时返回None."""
        @retry(max_attempts=3, exceptions=(ValueError,), raise_on_max_attempts=False)
        async def always_failing_function():
            raise ValueError("Always fails")

        result = await always_failing_function()
        assert result is None

    @pytest.mark.asyncio
    async def test_retry_with_callback(self):
        """测试带回调的重试."""
        call_count = 0
        callback_count = 0

        @retry(
            max_attempts=3,
            exceptions=(ValueError,),
            on_retry=lambda attempt, exc: callback_count.__setitem__(0, callback_count[0] + 1),
        )
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Not yet")
            return "success"

        # 使用列表作为可变对象
        callback_count = [0]

        @retry(
            max_attempts=3,
            exceptions=(ValueError,),
            on_retry=lambda attempt, exc: callback_count.__setitem__(0, callback_count[0] + 1),
        )
        async def failing_function_with_callback():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Not yet")
            return "success"

        result = await failing_function_with_callback()
        assert result == "success"
        assert callback_count[0] == 1  # 回调被调用一次

    def test_sync_function_retry(self):
        """测试同步函数重试."""
        call_count = 0

        @retry(max_attempts=3, exceptions=(ValueError,))
        def sync_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Not yet")
            return "success"

        result = sync_failing_function()
        assert result == "success"
        assert call_count == 2


class TestRetryPolicy:
    """测试重试策略."""

    def test_create_database_policy(self):
        """测试创建数据库策略."""
        decorator = RetryPolicy.create_retry("DATABASE")
        assert decorator is not None

    def test_create_http_request_policy(self):
        """测试创建HTTP请求策略."""
        decorator = RetryPolicy.create_retry("HTTP_REQUEST")
        assert decorator is not None

    def test_create_external_api_policy(self):
        """测试创建外部API策略."""
        decorator = RetryPolicy.create_retry("EXTERNAL_API")
        assert decorator is not None

    def test_create_crawler_policy(self):
        """测试创建爬虫策略."""
        decorator = RetryPolicy.create_retry("CRAWLER")
        assert decorator is not None

    def test_invalid_policy_name(self):
        """测试无效的策略名称."""
        with pytest.raises(ValueError, match="Unknown retry policy"):
            RetryPolicy.create_retry("INVALID_POLICY")

    @pytest.mark.asyncio
    async def test_apply_database_policy(self):
        """测试应用数据库策略."""
        call_count = 0

        @RetryPolicy.create_retry("DATABASE")
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Database error")
            return "success"

        result = await failing_function()
        assert result == "success"
