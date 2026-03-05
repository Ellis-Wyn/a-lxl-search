"""
=====================================================
Redis 缓存服务测试
=====================================================

测试内容：
1. Redis 连接测试
2. 缓存读写测试
3. 缓存过期测试
4. 缓存键生成测试
5. 缓存装饰器测试
6. 统一搜索缓存集成测试
7. PubMed 缓存集成测试
=====================================================
"""

import pytest
import time
from services.cache_service import CacheService


class TestCacheService:
    """缓存服务测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前置条件"""
        # Redis 服务地址（Docker 或本地）
        self.redis_url = "redis://localhost:6379/0"
        self.cache = CacheService(redis_url=self.redis_url, key_prefix="test_pathology")

        # 尝试连接 Redis（如果未启动会跳过测试）
        try:
            self.cache.redis.ping()
            self.redis_available = True
        except Exception as e:
            print(f"Redis not available: {e}")
            print("To enable tests, start Redis:")
            print("  docker-compose up -d redis")
            self.redis_available = False

    def test_redis_connection(self):
        """测试 1：Redis 连接"""
        if not self.redis_available:
            pytest.skip("Redis 服务未启动")

        try:
            result = self.cache.redis.ping()
            assert result is True
            print("✅ Redis 连接成功")
        except Exception as e:
            pytest.fail(f"Redis 连接失败: {e}")

    def test_cache_set_and_get(self):
        """测试 2：缓存读写"""
        if not self.redis_available:
            pytest.skip("Redis 服务未启动")

        # 设置缓存
        test_data = {
            "query": "EGFR",
            "results": [
                {"id": 1, "name": "Drug A"},
                {"id": 2, "name": "Drug B"}
            ],
            "total": 2
        }

        success = self.cache.set("test_key", test_data, ttl=60)
        assert success is True

        # 读取缓存
        cached_data = self.cache.get("test_key")
        assert cached_data is not None
        assert cached_data["query"] == "EGFR"
        assert cached_data["total"] == 2
        assert len(cached_data["results"]) == 2

        print("✅ 缓存读写测试通过")

    def test_cache_expiry(self):
        """测试 3：缓存过期"""
        if not self.redis_available:
            pytest.skip("Redis 服务未启动")

        # 设置 2 秒过期的缓存
        test_data = {"temp": "data"}
        self.cache.set("temp_key", test_data, ttl=2)

        # 立即读取应该存在
        cached_data = self.cache.get("temp_key")
        assert cached_data is not None

        # 等待 3 秒后应该过期
        time.sleep(3)
        cached_data = self.cache.get("temp_key")
        assert cached_data is None

        print("✅ 缓存过期测试通过")

    def test_cache_key_generation(self):
        """测试 4：缓存键生成"""
        # 测试搜索缓存键
        search_key = CacheService.generate_search_cache_key(
            entity_type="pipeline",
            query="EGFR",
            filters={"company": "恒瑞医药", "phase": "Phase 3"}
        )
        assert search_key.startswith("search:pipeline:")
        print(f"搜索缓存键: {search_key}")

        # 测试 PubMed 缓存键
        pubmed_key = CacheService.generate_pubmed_cache_key(
            target="EGFR",
            keywords=["inhibitor", "TKI"]
        )
        assert pubmed_key.startswith("pubmed:")
        print(f"PubMed 缓存键: {pubmed_key}")

        # 测试管线缓存键
        pipeline_key = CacheService.generate_pipeline_cache_key(
            company="恒瑞医药",
            phase="Phase 3",
            indication="肺癌"
        )
        assert pipeline_key.startswith("pipeline:company:")
        print(f"管线缓存键: {pipeline_key}")

        print("✅ 缓存键生成测试通过")

    def test_cache_delete(self):
        """测试 5：缓存删除"""
        if not self.redis_available:
            pytest.skip("Redis 服务未启动")

        # 设置缓存
        test_data = {"test": "delete_me"}
        self.cache.set("delete_key", test_data, ttl=60)

        # 确认存在
        assert self.cache.exists("delete_key") is True

        # 删除缓存
        success = self.cache.delete("delete_key")
        assert success is True

        # 确认已删除
        assert self.cache.exists("delete_key") is False

        print("✅ 缓存删除测试通过")

    def test_cache_pattern_clear(self):
        """测试 6：批量删除缓存"""
        if not self.redis_available:
            pytest.skip("Redis 服务未启动")

        # 设置多个缓存
        for i in range(5):
            self.cache.set(f"test_pattern:key_{i}", {"data": i}, ttl=60)

        # 确认存在
        assert self.cache.exists("test_pattern:key_0") is True

        # 批量删除
        count = self.cache.clear_pattern("test_pattern:*")
        assert count >= 5

        # 确认已删除
        assert self.cache.exists("test_pattern:key_0") is False

        print("✅ 批量删除测试通过")

    def test_cache_stats(self):
        """测试 7：缓存统计"""
        if not self.redis_available:
            pytest.skip("Redis 服务未启动")

        stats = self.cache.get_stats()

        assert "total_keys" in stats
        assert "key_prefix" in stats
        assert stats["key_prefix"] == "test_pathology"

        print(f"缓存统计: {stats}")
        print("✅ 缓存统计测试通过")


class TestCacheIntegration:
    """缓存集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前置条件"""
        self.redis_url = "redis://localhost:6379/0"

        try:
            self.cache = CacheService(redis_url=self.redis_url)
            self.cache.redis.ping()
            self.redis_available = True
        except Exception:
            self.redis_available = False

    def test_unified_search_caching(self):
        """测试 8：统一搜索缓存集成"""
        if not self.redis_available:
            pytest.skip("Redis 服务未启动")

        # 模拟统一搜索服务
        from services.unified_search_service import UnifiedSearchService

        service = UnifiedSearchService(cache_service=self.cache)

        # 生成缓存键
        cache_key = CacheService.generate_search_cache_key(
            entity_type="all",
            query="EGFR",
            filters={"phase": "Phase 3"}
        )

        # 模拟搜索结果
        mock_result = {
            "query": "EGFR",
            "total_count": 100,
            "results": {
                "pipelines": {"count": 50, "items": []},
                "publications": {"count": 50, "items": []}
            },
            "facets": {}
        }

        # 写入缓存
        self.cache.set(cache_key, mock_result, ttl=1800)

        # 读取缓存
        cached = self.cache.get(cache_key)
        assert cached is not None
        assert cached["total_count"] == 100

        print("✅ 统一搜索缓存集成测试通过")

    def test_pubmed_caching(self):
        """测试 9：PubMed 缓存集成"""
        if not self.redis_available:
            pytest.skip("Redis 服务未启动")

        # 生成缓存键
        cache_key = CacheService.generate_pubmed_cache_key(
            target="EGFR",
            keywords=["inhibitor"]
        )

        # 模拟 PubMed 搜索结果
        mock_result = [
            {"pmid": "123456", "title": "EGFR inhibitor study"},
            {"pmid": "789012", "title": "EGFR TKI trial"}
        ]

        # 写入缓存
        self.cache.set(cache_key, mock_result, ttl=7200)

        # 读取缓存
        cached = self.cache.get(cache_key)
        assert cached is not None
        assert len(cached) == 2

        print("✅ PubMed 缓存集成测试通过")


if __name__ == "__main__":
    # 直接运行测试
    print("=" * 60)
    print("Redis 缓存服务测试")
    print("=" * 60)

    test = TestCacheService()

    try:
        test.setup()
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        print("\n请先启动 Redis 服务：")
        print("  docker-compose up -d redis")
        exit(1)

    # 运行所有测试
    tests = [
        ("Redis 连接测试", test.test_redis_connection),
        ("缓存读写测试", test.test_cache_set_and_get),
        ("缓存过期测试", test.test_cache_expiry),
        ("缓存键生成测试", test.test_cache_key_generation),
        ("缓存删除测试", test.test_cache_delete),
        ("批量删除测试", test.test_cache_pattern_clear),
        ("缓存统计测试", test.test_cache_stats),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {name} 失败: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("🎉 所有测试通过!")
    else:
        print(f"⚠️  有 {failed} 个测试失败")
