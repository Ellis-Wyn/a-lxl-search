"""
爬虫功能测试指南
"""

import sys
import io
import requests

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def test_get_status():
    """测试1: 获取调度器状态"""
    print_section("测试1: 获取调度器状态")

    response = requests.get(f"{BASE_URL}/api/crawlers/status")
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 调度器状态:")
        print(f"  - 启用: {data.get('enabled')}")
        print(f"  - 运行中: {data.get('running')}")
        print(f"  - 调度时间: {data.get('scheduled_time')}")
        print(f"  - 最大并发: {data.get('max_concurrent')}")
        print(f"  - 下次运行: {data.get('next_run_time')}")
    else:
        print(f"❌ 请求失败: {response.text}")


def test_list_crawlers():
    """测试2: 列出所有可用的爬虫"""
    print_section("测试2: 列出所有可用的爬虫")

    response = requests.get(f"{BASE_URL}/api/crawlers/list")
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 总共有 {data['total']} 个爬虫:")
        for spider in data['spiders']:
            print(f"  - {spider['name']:20s} | {spider['company_name']:30s} | {spider.get('base_url', 'N/A')}")
    else:
        print(f"❌ 请求失败: {response.text}")


def test_get_stats():
    """测试3: 获取爬虫统计信息"""
    print_section("测试3: 获取爬虫统计信息")

    response = requests.get(f"{BASE_URL}/api/crawlers/stats")
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 统计信息（共 {data['total']} 个爬虫）:")
        print(f"\n{'爬虫名称':<20} {'总次数':<8} {'成功率':<10} {'健康状态':<10} {'最后运行':<20}")
        print("-" * 80)
        for stat in data['stats']:
            spider_name = stat.get('spider_name', 'N/A')
            total_runs = stat.get('total_runs', 0)
            success_rate = stat.get('success_rate', 0)
            health_status = stat.get('health_status', 'unknown')
            last_run = stat.get('last_run', 'N/A')[:19] if stat.get('last_run') else 'N/A'

            print(f"{spider_name:<20} {total_runs:<8} {success_rate:<9.1f}% {health_status:<10} {last_run:<20}")
    else:
        print(f"❌ 请求失败: {response.text}")


def test_get_health():
    """测试4: 获取爬虫健康状态"""
    print_section("测试4: 获取爬虫健康状态")

    response = requests.get(f"{BASE_URL}/api/crawlers/health")
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 健康状态:")
        print(f"  - 健康 ({len(data['healthy'])}): {', '.join(data['healthy']) if data['healthy'] else '无'}")
        print(f"  - 降级 ({len(data['degraded'])}): {', '.join(data['degraded']) if data['degraded'] else '无'}")
        print(f"  - 不健康 ({len(data['unhealthy'])}): {', '.join(data['unhealthy']) if data['unhealthy'] else '无'}")
    else:
        print(f"❌ 请求失败: {response.text}")


def test_get_executions():
    """测试5: 查询执行历史"""
    print_section("测试5: 查询执行历史（最近7天）")

    params = {
        "days": 7,
        "limit": 10
    }
    response = requests.get(f"{BASE_URL}/api/crawlers/executions", params=params)
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        summary = data['summary']
        print(f"✅ 执行历史:")
        print(f"  - 总次数: {summary['total_runs']}")
        print(f"  - 成功: {summary['success_count']}")
        print(f"  - 失败: {summary['failed_count']}")
        print(f"  - 成功率: {summary['success_rate']:.1f}%")
        print(f"  - 平均时长: {summary['avg_duration']:.2f}秒")

        if data['executions']:
            print(f"\n最近 {len(data['executions'])} 次执行:")
            for i, exe in enumerate(data['executions'][:5], 1):
                print(f"  {i}. {exe['spider_name']} | {exe['trigger_type']} | "
                      f"{exe['status']} | {exe['items_fetched']} 条 | {exe['started_at']}")
    else:
        print(f"❌ 请求失败: {response.text}")


def test_trigger_single_crawler():
    """测试6: 触发单个爬虫（手动执行）"""
    print_section("测试6: 触发单个爬虫（手动执行）")

    print("\n⚠️  注意：此操作将实际运行爬虫，可能需要几秒钟到几分钟")
    print("可用的爬虫名称:")
    response = requests.get(f"{BASE_URL}/api/crawlers/list")
    if response.status_code == 200:
        spiders = response.json()['spiders']
        for spider in spiders:
            print(f"  - {spider['name']}")

    print("\n" + "-" * 80)
    print("如需测试，请取消注释下面的代码并指定爬虫名称:")
    print('spider_name = "hengrui"  # 修改这里')
    print('response = requests.post(f"{BASE_URL}/api/crawlers/trigger/{spider_name}")')
    # spider_name = "hengrui"  # 修改这里测试
    # response = requests.post(f"{BASE_URL}/api/crawlers/trigger/{spider_name}")
    # print(f"状态码: {response.status_code}")
    # if response.status_code == 200:
    #     print(f"✅ 爬虫 {spider_name} 触发成功")
    # else:
    #     print(f"❌ 触发失败: {response.text}")


def main():
    """运行所有测试"""
    print("=" * 80)
    print("🕷️  爬虫功能测试")
    print("=" * 80)

    # 测试1-5: 只读测试（安全）
    test_get_status()
    test_list_crawlers()
    test_get_stats()
    test_get_health()
    test_get_executions()

    # 测试6: 写操作（需要用户确认）
    test_trigger_single_crawler()

    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)

    print("\n💡 使用 Swagger UI 测试爬虫:")
    print("   1. 打开浏览器访问: http://localhost:8000/docs")
    print("   2. 找到 '爬虫管理' 和 '爬虫执行历史' 标签")
    print("   3. 尝试以下操作:")
    print("      - GET /api/crawlers/list - 查看所有爬虫")
    print("      - GET /api/crawlers/status - 查看调度器状态")
    print("      - GET /api/crawlers/stats - 查看统计信息")
    print("      - POST /api/crawlers/trigger/{spider_name} - 触发单个爬虫")
    print("      - GET /api/crawlers/executions - 查看执行历史")
    print("=" * 80)


if __name__ == "__main__":
    main()
