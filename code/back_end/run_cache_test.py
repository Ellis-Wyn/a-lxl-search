"""
运行缓存测试的简单脚本
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.cache_service import CacheService

def test_cache_basic():
    """基础缓存测试"""
    print("=" * 60)
    print("Redis 缓存服务测试")
    print("=" * 60)

    # Redis 连接
    redis_url = "redis://localhost:6379/0"
    cache = CacheService(redis_url=redis_url, key_prefix="test_pathology")

    try:
        # 测试连接
        result = cache.redis.ping()
        print(f"[OK] Redis 连接: {'成功' if result else '失败'}")

        # 测试写入
        test_data = {
            "query": "EGFR",
            "results": [{"id": 1, "name": "Drug A"}],
            "total": 1
        }
        cache.set("test_key", test_data, ttl=60)
        print("[OK] 缓存写入: 成功")

        # 测试读取
        cached_data = cache.get("test_key")
        assert cached_data is not None
        assert cached_data["query"] == "EGFR"
        print("[OK] 缓存读取: 成功")
        print(f"   读取数据: {cached_data}")

        # 测试键生成
        search_key = CacheService.generate_search_cache_key(
            entity_type="pipeline",
            query="EGFR",
            filters={"phase": "Phase 3"}
        )
        print(f"[OK] 搜索缓存键: {search_key}")

        pubmed_key = CacheService.generate_pubmed_cache_key(
            target="EGFR",
            keywords=["inhibitor"]
        )
        print(f"[OK] PubMed缓存键: {pubmed_key}")

        # 测试删除
        cache.delete("test_key")
        assert not cache.exists("test_key")
        print("[OK] 缓存删除: 成功")

        # 测试统计
        stats = cache.get_stats()
        print(f"[OK] 缓存统计:")
        print(f"   总键数: {stats['total_keys']}")
        print(f"   内存使用: {stats.get('memory_used_human', 'N/A')}")
        print(f"   连接数: {stats.get('connected_clients', 'N/A')}")

        print("\n" + "=" * 60)
        print("[SUCCESS] 所有测试通过!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cache_basic()
    sys.exit(0 if success else 1)
