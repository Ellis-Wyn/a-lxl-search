"""
依赖注入容器.

提供：
- 服务注册与获取
- 单例模式支持
- 生命周期管理
- FastAPI依赖注入集成
"""

import asyncio
from typing import Any, Callable, Dict, Optional, TypeVar, Type

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ServiceContainer:
    """服务容器.

    管理应用中的服务实例，支持单例和工厂模式。

    Example:
        container = ServiceContainer()

        # 注册单例服务
        container.register_singleton("db", lambda: create_db_session())

        # 注册工厂服务（每次调用创建新实例）
        container.register_factory("http_client", lambda: HttpClient())

        # 获取服务
        db = container.get("db")
        client = container.get("http_client")
    """

    def __init__(self):
        """初始化容器."""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Callable] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def register_singleton(
        self,
        name: str,
        factory: Callable,
        lazy: bool = True,
    ) -> None:
        """注册单例服务.

        Args:
            name: 服务名称
            factory: 工厂函数（返回服务实例）
            lazy: 是否延迟加载（True表示首次使用时才初始化）
        """
        self._singletons[name] = factory

        if not lazy:
            # 立即初始化
            self._services[name] = factory()
            logger.info(f"Singleton service initialized: {name}")
        else:
            logger.info(f"Singleton service registered (lazy): {name}")

    def register_factory(self, name: str, factory: Callable) -> None:
        """注册工厂服务（每次调用创建新实例）。

        Args:
            name: 服务名称
            factory: 工厂函数
        """
        self._factories[name] = factory
        logger.info(f"Factory service registered: {name}")

    def register_instance(self, name: str, instance: Any) -> None:
        """注册已存在的实例.

        Args:
            name: 服务名称
            instance: 服务实例
        """
        self._services[name] = instance
        logger.info(f"Instance registered: {name}")

    async def get_async(self, name: str) -> Any:
        """异步获取服务.

        Args:
            name: 服务名称

        Returns:
            服务实例

        Raises:
            KeyError: 服务不存在
        """
        # 如果已存在实例，直接返回
        if name in self._services:
            return self._services[name]

        # 单例服务（延迟加载）
        if name in self._singletons:
            # 使用锁确保只初始化一次
            if name not in self._locks:
                self._locks[name] = asyncio.Lock()

            async with self._locks[name]:
                # 双重检查
                if name not in self._services:
                    factory = self._singletons[name]
                    instance = factory()
                    # 如果工厂函数是协程，需要await
                    if asyncio.iscoroutine(instance):
                        instance = await instance
                    self._services[name] = instance
                    logger.info(f"Singleton service initialized: {name}")

            return self._services[name]

        # 工厂服务
        if name in self._factories:
            factory = self._factories[name]
            instance = factory()
            # 如果工厂函数是协程，需要await
            if asyncio.iscoroutine(instance):
                instance = await instance
            return instance

        raise KeyError(f"Service not found: {name}")

    def get(self, name: str) -> Any:
        """同步获取服务.

        Args:
            name: 服务名称

        Returns:
            服务实例

        Raises:
            KeyError: 服务不存在
        """
        # 如果已存在实例，直接返回
        if name in self._services:
            return self._services[name]

        # 单例服务（延迟加载）
        if name in self._singletons:
            # 双重检查
            if name not in self._services:
                factory = self._singletons[name]
                self._services[name] = factory()
                logger.info(f"Singleton service initialized: {name}")

            return self._services[name]

        # 工厂服务
        if name in self._factories:
            factory = self._factories[name]
            return factory()

        raise KeyError(f"Service not found: {name}")

    def has(self, name: str) -> bool:
        """检查服务是否存在.

        Args:
            name: 服务名称

        Returns:
            是否存在
        """
        return (
            name in self._services
            or name in self._singletons
            or name in self._factories
        )

    async def close_async(self) -> None:
        """异步关闭所有服务.

        清理资源，调用服务的close()方法（如果存在）。
        """
        for name, instance in self._services.items():
            if hasattr(instance, "close"):
                close_method = getattr(instance, "close")
                # 如果close方法是协程
                if asyncio.iscoroutinefunction(close_method):
                    await close_method()
                else:
                    close_method()
                logger.info(f"Service closed: {name}")

        self._services.clear()
        logger.info("All services closed")

    def close(self) -> None:
        """同步关闭所有服务.

        清理资源，调用服务的close()方法（如果存在）。
        """
        for name, instance in list(self._services.items()):
            if hasattr(instance, "close"):
                close_method = getattr(instance, "close")
                # 如果close方法是协程，使用run运行
                if asyncio.iscoroutinefunction(close_method):
                    asyncio.run(close_method())
                else:
                    close_method()
                logger.info(f"Service closed: {name}")

        self._services.clear()
        logger.info("All services closed")


# 全局容器实例
_global_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """获取全局服务容器.

    Returns:
        ServiceContainer实例
    """
    global _global_container
    if _global_container is None:
        _global_container = ServiceContainer()
    return _global_container


def init_container(app) -> ServiceContainer:
    """初始化服务容器并注册核心服务.

    Args:
        app: FastAPI应用实例

    Returns:
        ServiceContainer实例
    """
    container = get_container()

    # 尝试注册数据库会话工厂（懒加载）
    try:
        from utils.database import get_db_factory
        container.register_singleton("db", get_db_factory, lazy=True)
        logger.info("Database service registered")
    except Exception as e:
        logger.warning(f"Database service not available: {e}")

    # 注册 Redis 缓存服务
    try:
        from services.cache_service import CacheService
        from config import settings

        if settings.REDIS_ENABLED:
            cache_service = CacheService(
                redis_url=settings.redis_url,
                key_prefix=settings.REDIS_KEY_PREFIX
            )
            container.register_instance("cache", cache_service)
            logger.info("Redis cache service registered")
        else:
            logger.info("Redis cache disabled")
    except Exception as e:
        logger.warning(f"Cache service not available: {e}")

    logger.info("Service container initialized")

    return container


__all__ = [
    "ServiceContainer",
    "get_container",
    "init_container",
]
