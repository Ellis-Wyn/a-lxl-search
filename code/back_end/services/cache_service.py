"""
=====================================================
Redis 缓存服务
=====================================================

提供统一的缓存接口，支持 Redis 缓存操作
主要功能：
- 缓存读写
- 缓存过期管理
- 缓存键生成
- 缓存装饰器
=====================================================
"""

import json
import hashlib
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
import redis
from redis.asyncio import Redis as AsyncRedis
from core.logger import logger


class CacheService:
    """
    Redis 缓存服务类

    提供统一的缓存操作接口，支持同步和异步操作
    """

    def __init__(self, redis_url: str, key_prefix: str = "pathology_ai"):
        """
        初始化缓存服务

        Args:
            redis_url: Redis 连接 URL (redis://localhost:6379/0)
            key_prefix: 缓存键前缀
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix

        # 创建同步 Redis 客户端（用于兼容）
        self.redis = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )

        # 创建异步 Redis 客户端
        self.async_redis = None

        logger.info(f"CacheService initialized with prefix: {key_prefix}")

    async def get_async_redis(self) -> AsyncRedis:
        """获取异步 Redis 客户端（懒加载）"""
        if self.async_redis is None:
            self.async_redis = await AsyncRedis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        return self.async_redis

    def _make_key(self, key: str) -> str:
        """生成带前缀的缓存键"""
        return f"{self.key_prefix}:{key}"

    # =====================================================
    # 同步方法（用于兼容）
    # =====================================================

    def get(self, key: str) -> Optional[Dict]:
        """
        获取缓存（同步）

        Args:
            key: 缓存键

        Returns:
            缓存数据，如果不存在返回 None
        """
        try:
            full_key = self._make_key(key)
            data = self.redis.get(full_key)

            if data:
                logger.debug(f"Cache hit: {key}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: dict, ttl: int = 3600) -> bool:
        """
        设置缓存（同步）

        Args:
            key: 缓存键
            value: 缓存值（字典）
            ttl: 过期时间（秒），默认 1 小时

        Returns:
            是否设置成功
        """
        try:
            full_key = self._make_key(key)
            data = json.dumps(value, ensure_ascii=False)

            self.redis.setex(full_key, ttl, data)
            logger.debug(f"Cache set: {key}, TTL: {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        try:
            full_key = self._make_key(key)
            self.redis.delete(full_key)
            logger.debug(f"Cache deleted: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        try:
            full_key = self._make_key(key)
            return self.redis.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        批量删除缓存（按模式匹配）

        Args:
            pattern: 键模式，例如 "search:*"

        Returns:
            删除的缓存数量
        """
        try:
            full_pattern = self._make_key(pattern)
            keys = self.redis.keys(full_pattern)

            if keys:
                count = self.redis.delete(*keys)
                logger.info(f"Cleared {count} cache keys matching: {pattern}")
                return count
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0

    # =====================================================
    # 异步方法（推荐使用）
    # =====================================================

    async def async_get(self, key: str) -> Optional[dict]:
        """获取缓存（异步）"""
        try:
            redis_client = await self.get_async_redis()
            full_key = self._make_key(key)
            data = await redis_client.get(full_key)

            if data:
                logger.debug(f"Cache hit: {key}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache async get error: {e}")
            return None

    async def async_set(self, key: str, value: dict, ttl: int = 3600) -> bool:
        """设置缓存（异步）"""
        try:
            redis_client = await self.get_async_redis()
            full_key = self._make_key(key)
            data = json.dumps(value, ensure_ascii=False)

            await redis_client.setex(full_key, ttl, data)
            logger.debug(f"Cache set: {key}, TTL: {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Cache async set error: {e}")
            return False

    async def async_delete(self, key: str) -> bool:
        """删除缓存（异步）"""
        try:
            redis_client = await self.get_async_redis()
            full_key = self._make_key(key)
            await redis_client.delete(full_key)
            logger.debug(f"Cache deleted: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache async delete error: {e}")
            return False

    # =====================================================
    # 缓存键生成器
    # =====================================================

    @staticmethod
    def generate_search_cache_key(entity_type: str, query: str, filters: dict = None) -> str:
        """
        生成搜索缓存键

        Args:
            entity_type: 实体类型 (pipeline/publication/target/all)
            query: 搜索关键词
            filters: 筛选条件

        Returns:
            缓存键
        """
        # 创建筛选条件的哈希
        filter_str = json.dumps(filters or {}, sort_keys=True)
        filter_hash = hashlib.md5(filter_str.encode()).hexdigest()[:8]

        # 创建查询的哈希
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]

        return f"search:{entity_type}:{query_hash}:{filter_hash}"

    @staticmethod
    def generate_pubmed_cache_key(target: str, keywords: List[str] = None) -> str:
        """
        生成 PubMed 缓存键

        Args:
            target: 靶点名称
            keywords: 关键词列表

        Returns:
            缓存键
        """
        keywords_str = ",".join(sorted(keywords or []))
        key_str = f"{target}:{keywords_str}"

        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:8]
        return f"pubmed:{key_hash}"

    @staticmethod
    def generate_pipeline_cache_key(company: str, phase: str = None, indication: str = None) -> str:
        """
        生成管线缓存键

        Args:
            company: 公司名称
            phase: 阶段（可选）
            indication: 适应症（可选）

        Returns:
            缓存键
        """
        parts = [f"company:{company}"]

        if phase:
            parts.append(f"phase:{phase}")

        if indication:
            indication_hash = hashlib.md5(indication.encode()).hexdigest()[:8]
            parts.append(f"indication:{indication_hash}")

        return f"pipeline:{':'.join(parts)}"

    @staticmethod
    def generate_cde_cache_key(event_type: str = None, applicant: str = None) -> str:
        """
        生成 CDE 缓存键

        Args:
            event_type: 事件类型（IND/NDA等）
            applicant: 申请人

        Returns:
            缓存键
        """
        parts = ["cde"]

        if event_type:
            parts.append(f"type:{event_type}")

        if applicant:
            parts.append(f"applicant:{applicant}")

        return ":".join(parts)

    # =====================================================
    # 工具方法
    # =====================================================

    def flush_all(self) -> bool:
        """
        清空所有缓存（危险操作）

        Returns:
            是否清空成功
        """
        try:
            # 只清空带前缀的键
            pattern = f"{self.key_prefix}:*"
            keys = self.redis.keys(pattern)

            if keys:
                self.redis.delete(*keys)
                logger.warning(f"Flushed all cache: {len(keys)} keys deleted")

            return True
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return False

    def get_stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        try:
            info = self.redis.info()
            pattern = f"{self.key_prefix}:*"
            keys = self.redis.keys(pattern)

            return {
                "total_keys": len(keys),
                "memory_used_human": info.get("used_memory_human", "N/A"),
                "memory_used_bytes": info.get("used_memory", 0),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "key_prefix": self.key_prefix
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {
                "total_keys": 0,
                "error": str(e)
            }

    def close(self):
        """关闭 Redis 连接"""
        try:
            self.redis.close()
            logger.info("CacheService closed")
        except Exception as e:
            logger.error(f"Cache close error: {e}")


# =====================================================
# 缓存装饰器
# =====================================================

def cache_result(ttl: int = 3600, key_prefix: str = "", cache_service: CacheService = None):
    """
    缓存装饰器

    用于缓存函数的返回值

    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
        cache_service: 缓存服务实例

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            """异步包装器"""
            if cache_service is None:
                # 如果没有提供缓存服务，直接执行函数
                return await func(*args, **kwargs)

            # 生成缓存键
            key_parts = [key_prefix, func.__name__]

            # 添加参数到键（使用参数的哈希值）
            args_str = f"{args}:{sorted(kwargs.items())}"
            args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
            key_parts.append(args_hash)

            cache_key = ":".join(filter(None, key_parts))

            # 尝试从缓存获取
            cached_result = await cache_service.async_get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数
            result = await func(*args, **kwargs)

            # 写入缓存
            if result is not None:
                await cache_service.async_set(cache_key, result, ttl=ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            """同步包装器"""
            if cache_service is None:
                return func(*args, **kwargs)

            # 生成缓存键
            key_parts = [key_prefix, func.__name__]

            args_str = f"{args}:{sorted(kwargs.items())}"
            args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
            key_parts.append(args_hash)

            cache_key = ":".join(filter(None, key_parts))

            # 尝试从缓存获取
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数
            result = func(*args, **kwargs)

            # 写入缓存
            if result is not None:
                cache_service.set(cache_key, result, ttl=ttl)

            return result

        # 根据函数类型返回对应的包装器
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
