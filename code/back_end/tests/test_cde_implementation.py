"""
=====================================================
CDE 实现验证测试
=====================================================

功能：
1. 验证所有模块导入正确
2. 验证数据模型定义正确
3. 验证API路由定义正确
4. 基础功能检查（不依赖数据库）

运行方式：
    cd D:\26初寒假实习\A_lxl_search\code\back_end
    python tests\test_cde_implementation.py
=====================================================
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("CDE 爬虫实现验证测试")
print("=" * 70)
print()

# 测试 1: 导入 CDEEvent 模型
print("测试 1: 导入 CDEEvent 模型...")
try:
    from models.cde_event import CDEEvent
    print("✅ CDEEvent 模型导入成功")

    # 检查关键字段
    required_fields = [
        'id', 'acceptance_no', 'event_type', 'drug_name', 'applicant',
        'public_page_url', 'source_urls', 'is_active',
        'first_seen_at', 'last_seen_at'
    ]

    for field in required_fields:
        if not hasattr(CDEEvent, field):
            print(f"❌ 缺少字段: {field}")
            sys.exit(1)

    print("✅ 所有必需字段存在")
    print()

except Exception as e:
    print(f"❌ CDEEvent 模型导入失败: {e}")
    sys.exit(1)

# 测试 2: 导入 CDESpider
print("测试 2: 导入 CDESpider...")
try:
    from crawlers.cde_spider import CDESpider, CDEEventData
    print("✅ CDESpider 和 CDEEventData 导入成功")

    # 检查关键方法
    required_methods = ['run', 'fetch_event_list', 'fetch_event_detail', 'save_to_database']

    for method in required_methods:
        if not hasattr(CDESpider, method):
            print(f"❌ 缺少方法: {method}")
            sys.exit(1)

    print("✅ 所有必需方法存在")
    print()

except Exception as e:
    print(f"❌ CDESpider 导入失败: {e}")
    sys.exit(1)

# 测试 3: 导入统一搜索服务
print("测试 3: 导入统一搜索服务...")
try:
    from services.unified_search_service import UnifiedSearchService
    print("✅ UnifiedSearchService 导入成功")

    # 检查 CDE 搜索方法
    if not hasattr(UnifiedSearchService, 'search_cde_events'):
        print("❌ 缺少方法: search_cde_events")
        sys.exit(1)

    if not hasattr(UnifiedSearchService, '_calculate_cde_event_relevance'):
        print("❌ 缺少方法: _calculate_cde_event_relevance")
        sys.exit(1)

    print("✅ CDE 搜索方法存在")
    print()

except Exception as e:
    print(f"❌ UnifiedSearchService 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 4: 导入 API 路由
print("测试 4: 导入 API 路由...")
try:
    from api.cde import router as cde_router
    from api.search import router as search_router
    print("✅ CDE 和 Search 路由导入成功")

    # 检查路由标签
    if cde_router.tags != ["CDE"]:
        print(f"❌ CDE 路由标签不正确: {cde_router.tags}")
        sys.exit(1)

    print("✅ 路由配置正确")
    print()

except Exception as e:
    print(f"❌ API 路由导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 5: 检查配置
print("测试 5: 检查配置...")
try:
    from config import settings

    required_configs = [
        'CDE_CRAWLER_ENABLED',
        'CDE_CRAWLER_BASE_URL',
        'CDE_CRAWLER_INFO_URL',
        'CDE_CRAWLER_INTERVAL_HOURS',
        'CDE_CRAWLER_RATE_LIMIT'
    ]

    for config in required_configs:
        if not hasattr(settings, config):
            print(f"❌ 缺少配置: {config}")
            sys.exit(1)

    print("✅ 所有 CDE 配置存在")
    print()

except Exception as e:
    print(f"❌ 配置检查失败: {e}")
    sys.exit(1)

# 测试 6: 验证数据类
print("测试 6: 验证 CDEEventData 数据类...")
try:
    from crawlers.cde_spider import CDEEventData
    from datetime import date

    # 创建测试实例
    test_event = CDEEventData(
        acceptance_no="TEST001",
        event_type="IND",
        drug_name="Test Drug",
        applicant="Test Company",
        public_page_url="https://example.com/test",
        source_urls=["https://example.com/list", "https://example.com/test"]
    )

    print("✅ CDEEventData 实例创建成功")
    print(f"  - 受理号: {test_event.acceptance_no}")
    print(f"  - 事件类型: {test_event.event_type}")
    print(f"  - 药品名称: {test_event.drug_name}")
    print(f"  - 申请人: {test_event.applicant}")
    print(f"  - Source URLs: {len(test_event.source_urls)} 个")
    print()

except Exception as e:
    print(f"❌ CDEEventData 验证失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 7: 验证工厂函数
print("测试 7: 验证工厂函数...")
try:
    from models import create_cde_event

    test_event = create_cde_event(
        acceptance_no="TEST002",
        event_type="NDA",
        drug_name="Test Drug 2",
        applicant="Test Company 2",
        public_page_url="https://example.com/test2"
    )

    print("✅ create_cde_event 工厂函数工作正常")
    print(f"  - 创建事件: {test_event.drug_name} - {test_event.event_type}")
    print()

except Exception as e:
    print(f"❌ 工厂函数验证失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# =====================================================
# 测试总结
# =====================================================

print("=" * 70)
print("✅ 所有测试通过！")
print("=" * 70)
print()
print("验证结果：")
print("  ✅ CDEEvent 数据模型定义正确")
print("  ✅ CDESpider 爬虫类定义正确")
print("  ✅ UnifiedSearchService 支持CDE搜索")
print("  ✅ API 路由配置正确")
print("  ✅ 配置项完整")
print("  ✅ 数据类可用")
print("  ✅ 工厂函数可用")
print()
print("下一步：")
print("  1. 运行数据库初始化：python scripts/init_db.py")
print("  2. 启动API服务：python main.py")
print("  3. 访问API文档：http://localhost:8000/docs")
print("  4. 测试CDE爬虫（需要手动探索CDE网站结构）")
print("=" * 70)
