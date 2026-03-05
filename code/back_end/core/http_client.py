"""
HTTP客户端封装.

基于httpx提供：
- 异步HTTP请求
- 集成重试机制
- 集成熔断器
- 请求/响应日志
- 超时控制
"""

from typing import Optional, Dict, Any

import httpx
from httpx import AsyncClient, Response, TimeoutException

from .retry import RetryPolicy, retry
from .circuit_breaker import CircuitBreaker, get_circuit_breaker_manager, CircuitBreakerOpenError
from .logger import get_logger
from .exceptions import ExternalAPIError

logger = get_logger(__name__)


class HttpClient:
    """HTTP客户端类.

    封装httpx客户端，提供重试、熔断、日志等功能。

    Example:
        client = HttpClient(
            base_url="https://api.example.com",
            timeout=10.0,
            circuit_breaker=True,
        )

        response = await client.get("/endpoint")
        data = await client.post("/endpoint", json={"key": "value"})
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        circuit_breaker: bool = False,
        circuit_breaker_name: Optional[str] = None,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        """初始化HTTP客户端.

        Args:
            base_url: 基础URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            circuit_breaker: 是否启用熔断器
            circuit_breaker_name: 熔断器名称（默认使用base_url）
            circuit_breaker_threshold: 熔断器失败阈值
            circuit_breaker_timeout: 熔断器恢复超时时间（秒）
            headers: 默认请求头
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = headers or {}

        # 熔断器配置
        self.circuit_breaker_enabled = circuit_breaker
        self._circuit_breaker: Optional[CircuitBreaker] = None

        if circuit_breaker:
            name = circuit_breaker_name or base_url or "default"
            manager = get_circuit_breaker_manager()
            self._circuit_breaker = manager.get_or_create(
                name,
                failure_threshold=circuit_breaker_threshold,
                recovery_timeout=circuit_breaker_timeout,
                expected_exception=(TimeoutException, ConnectionError, httpx.HTTPError),
            )

        # httpx客户端（延迟初始化）
        self._client: Optional[AsyncClient] = None

    async def _get_client(self) -> AsyncClient:
        """获取或创建httpx客户端.

        Returns:
            AsyncClient实例
        """
        if self._client is None:
            self._client = AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.headers,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> Response:
        """执行带重试的HTTP请求.

        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 传递给httpx的参数

        Returns:
            Response对象

        Raises:
            ExternalAPIError: API调用失败
        """
        client = await self._get_client()

        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                # 执行请求
                response = await client.request(method, url, **kwargs)

                # 记录响应日志
                logger.info(
                    f"HTTP {method} request completed",
                    extra={
                        "method": method,
                        "url": str(response.url),
                        "status_code": response.status_code,
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                    },
                )

                return response

            except (TimeoutException, ConnectionError, httpx.HTTPError) as e:
                last_exception = e

                if attempt >= self.max_retries:
                    logger.error(
                        f"HTTP {method} request failed after {self.max_retries} attempts",
                        extra={
                            "method": method,
                            "url": url,
                            "attempts": self.max_retries,
                            "exception_type": type(e).__name__,
                        },
                    )
                    raise

                # 记算重试延迟
                delay = min(1.0 * (2 ** (attempt - 1)), 30.0)

                logger.info(
                    f"Retrying HTTP {method} request (attempt {attempt + 1}/{self.max_retries})",
                    extra={
                        "method": method,
                        "url": url,
                        "attempt": attempt,
                        "delay_seconds": delay,
                    },
                )

                import asyncio
                await asyncio.sleep(delay)

        # 理论上不会到这里
        raise ExternalAPIError(
            message=f"HTTP request failed: {str(last_exception)}",
            service_name=self.base_url or "unknown",
        )

    async def _execute_request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> Response:
        """执行请求（支持熔断器）。

        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 传递给httpx的参数

        Returns:
            Response对象
        """
        if self._circuit_breaker:
            # 使用熔断器保护
            return await self._circuit_breaker.call(
                self._request_with_retry,
                method,
                url,
                **kwargs,
            )
        else:
            # 直接请求
            return await self._request_with_retry(method, url, **kwargs)

    async def get(self, url: str, params: Optional[Dict] = None, **kwargs) -> Response:
        """GET请求.

        Args:
            url: 请求URL
            params: 查询参数
            **kwargs: 其他参数

        Returns:
            Response对象
        """
        return await self._execute_request("GET", url, params=params, **kwargs)

    async def post(
        self,
        url: str,
        json: Optional[Dict] = None,
        data: Optional[Any] = None,
        **kwargs,
    ) -> Response:
        """POST请求.

        Args:
            url: 请求URL
            json: JSON数据
            data: 表单数据
            **kwargs: 其他参数

        Returns:
            Response对象
        """
        return await self._execute_request("POST", url, json=json, data=data, **kwargs)

    async def put(
        self,
        url: str,
        json: Optional[Dict] = None,
        data: Optional[Any] = None,
        **kwargs,
    ) -> Response:
        """PUT请求.

        Args:
            url: 请求URL
            json: JSON数据
            data: 表单数据
            **kwargs: 其他参数

        Returns:
            Response对象
        """
        return await self._execute_request("PUT", url, json=json, data=data, **kwargs)

    async def delete(self, url: str, **kwargs) -> Response:
        """DELETE请求.

        Args:
            url: 请求URL
            **kwargs: 其他参数

        Returns:
            Response对象
        """
        return await self._execute_request("DELETE", url, **kwargs)

    async def patch(
        self,
        url: str,
        json: Optional[Dict] = None,
        data: Optional[Any] = None,
        **kwargs,
    ) -> Response:
        """PATCH请求.

        Args:
            url: 请求URL
            json: JSON数据
            data: 表单数据
            **kwargs: 其他参数

        Returns:
            Response对象
        """
        return await self._execute_request("PATCH", url, json=json, data=data, **kwargs)


async def get_http_client(
    base_url: Optional[str] = None,
    **kwargs,
) -> HttpClient:
    """获取或创建HTTP客户端（工厂函数）。

    Args:
        base_url: 基础URL
        **kwargs: 其他配置参数

    Returns:
        HttpClient实例
    """
    return HttpClient(base_url=base_url, **kwargs)


__all__ = [
    "HttpClient",
    "get_http_client",
]
