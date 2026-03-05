"""
=====================================================
Crawlers Runner - 爬虫总控制程序
=====================================================

统一管理和运行所有爬虫：
- 自动发现所有爬虫
- 单独运行特定爬虫
- 批量运行所有爬虫
- 显示运行统计

使用示例：
    # 运行所有爬虫
    python -m crawlers.runner --all

    # 运行特定爬虫
    python -m crawlers.runner --spider hengrui

    # 列出所有可用爬虫
    python -m crawlers.runner --list

作者：A_lxl_search Team
创建日期：2026-02-02
=====================================================
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlers import (
    discover_spiders,
    get_spider,
    list_spiders,
    run_spider,
    run_all_spiders,
)
from core.logger import get_logger

logger = get_logger(__name__)


def list_available_spiders():
    """列出所有可用的爬虫"""
    spiders = list_spiders()

    print("\n" + "=" * 60)
    print("可用爬虫列表 (Available Spiders)")
    print("=" * 60)

    if not spiders:
        print("✗ 未发现任何爬虫")
        return

    print(f"\n共发现 {len(spiders)} 个爬虫：\n")

    for i, spider_name in enumerate(spiders, 1):
        SpiderClass = get_spider(spider_name)
        if SpiderClass:
            spider_instance = SpiderClass()
            company_name = getattr(spider_instance, 'company_name', spider_name)
            print(f"  {i}. {spider_name} - {company_name}")
        else:
            print(f"  {i}. {spider_name}")

    print("\n" + "=" * 60)


def run_single_spider(spider_name: str):
    """运行单个爬虫"""
    print("\n" + "=" * 60)
    print(f"运行爬虫: {spider_name}")
    print("=" * 60 + "\n")

    stats = run_spider(spider_name)

    if stats is None:
        print(f"✗ 爬虫 {spider_name} 运行失败")
        return

    # 显示统计信息
    print("\n" + "-" * 60)
    print("运行统计 (Crawler Statistics)")
    print("-" * 60)
    print(f"  总获取 (Total Fetched):            {stats.total_fetched}")
    print(f"  成功 (Success):                    {stats.success}")
    print(f"  失败 (Failed):                     {stats.failed}")
    print(f"  跳过 (Skipped):                    {stats.skipped}")
    print("-" * 60)

    if stats.errors:
        print("\n错误 (Errors):")
        for error in stats.errors:
            print(f"  ✗ {error}")

    print("\n" + "=" * 60)


def run_all():
    """运行所有爬虫"""
    spiders = list_spiders()

    if not spiders:
        print("✗ 未发现任何爬虫")
        return

    print("\n" + "=" * 60)
    print(f"批量运行 {len(spiders)} 个爬虫")
    print("=" * 60 + "\n")

    all_stats = run_all_spiders()

    # 显示汇总统计
    print("\n" + "=" * 60)
    print("批量运行汇总 (Batch Run Summary)")
    print("=" * 60)

    total_succeeded = 0
    total_failed = 0

    for spider_name, stats in all_stats.items():
        if stats is None:
            print(f"  ✗ {spider_name}: 运行失败")
            total_failed += 1
        else:
            succeeded = stats.success or 0
            total_succeeded += succeeded
            print(f"  ✓ {spider_name}: {succeeded} items")

    print("-" * 60)
    print(f"  总成功 (Total Succeeded):  {total_succeeded}")
    print(f"  总失败 (Total Failed):     {total_failed}")
    print("=" * 60 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="病理AI药研情报库 - 爬虫总控制程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python -m crawlers.runner --list              # 列出所有可用爬虫
  python -m crawlers.runner --spider hengrui    # 运行恒瑞医药爬虫
  python -m crawlers.runner --all               # 运行所有爬虫
        """
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用的爬虫"
    )

    parser.add_argument(
        "--spider",
        type=str,
        metavar="NAME",
        help="运行指定的爬虫（公司名称，如 hengrui, beigene）"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="运行所有爬虫"
    )

    args = parser.parse_args()

    # 如果没有参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # 执行相应的操作
    if args.list:
        list_available_spiders()
    elif args.spider:
        run_single_spider(args.spider)
    elif args.all:
        run_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ 用户中断 (Interrupted by user)")
        sys.exit(1)
    except Exception as e:
        logger.error(f"运行出错: {e}", exc_info=True)
        print(f"\n✗ 运行出错: {e}")
        sys.exit(1)
