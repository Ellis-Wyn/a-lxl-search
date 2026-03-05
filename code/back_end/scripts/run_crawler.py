"""
=====================================================
药企爬虫运行脚本
=====================================================

运行药企爬虫，抓取管线数据并入库。

使用方式：
    # 运行恒瑞医药爬虫（手动配置版本）
    python scripts/run_crawler.py --company hengrui

    # 运行所有爬虫
    python scripts/run_crawler.py --all

    # 仅分析网站，不抓取数据
    python scripts/run_crawler.py --company hengrui --analyze-only
=====================================================
"""

import sys
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawlers.company_crawlers.hengrui_spider import HengruiManualSpider, HengruiSpider
from scripts.analyze_company_website import WebsiteAnalyzer
from core.logger import setup_logger, get_logger

# 初始化日志
setup_logger(app_name="crawler_runner", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


# =====================================================
# 爬虫注册
# =====================================================

AVAILABLE_SPIDERS = {
    "hengrui": {
        "name": "恒瑞医药",
        "class": HengruiManualSpider,  # 默认使用手动版用于测试
        "description": "恒瑞医药管线爬虫（手动配置版）",
    },
    "hengrui-real": {
        "name": "恒瑞医药(真实)",
        "class": HengruiSpider,  # 使用HengruiSpider而不是HengruiManualSpider
        "description": "恒瑞医药管线爬虫（真实网页版）",
    },
}


# =====================================================
# 主程序
# =====================================================

def run_spider(company_code: str, analyze_only: bool = False) -> int:
    """
    运行爬虫

    Args:
        company_code: 公司代码
        analyze_only: 是否仅分析网站

    Returns:
        退出码（0=成功，1=失败）
    """
    logger.info("=" * 60)
    logger.info(f"药企爬虫 - {company_code}")
    logger.info("=" * 60)

    # 1. 分析网站
    if analyze_only:
        logger.info("仅分析网站模式")
        analyzer = WebsiteAnalyzer(company_code)
        results = analyzer.analyze()
        return 0

    # 2. 运行爬虫
    spider_info = AVAILABLE_SPIDERS.get(company_code)
    if not spider_info:
        logger.error(f"未找到爬虫: {company_code}")
        logger.info(f"可用的爬虫: {', '.join(AVAILABLE_SPIDERS.keys())}")
        return 1

    logger.info(f"爬虫: {spider_info['description']}")

    try:
        # 创建爬虫实例
        spider = spider_info["class"]()

        # 运行爬虫
        logger.info("开始爬取数据...")
        stats = spider.run()

        # 输出统计
        logger.info("=" * 60)
        logger.info("爬取完成")
        logger.info("=" * 60)
        logger.info(f"总计: {stats.total_fetched} 条")
        logger.info(f"成功: {stats.success} 条")
        logger.info(f"失败: {stats.failed} 条")
        logger.info(f"跳过: {stats.skipped} 条")

        if stats.errors:
            logger.warning(f"错误列表: {stats.errors}")

        return 0 if stats.failed == 0 else 1

    except Exception as e:
        logger.error(f"爬虫运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def run_all_spiders() -> int:
    """
    运行所有爬虫

    Returns:
        退出码
    """
    logger.info("运行所有爬虫...")

    total_success = 0
    total_failed = 0

    for company_code in AVAILABLE_SPIDERS.keys():
        logger.info(f"\n{'=' * 60}")
        logger.info(f"运行爬虫: {company_code}")
        logger.info(f"{'=' * 60}\n")

        exit_code = run_spider(company_code)

        if exit_code == 0:
            total_success += 1
        else:
            total_failed += 1

    logger.info("\n" + "=" * 60)
    logger.info("所有爬虫运行完成")
    logger.info("=" * 60)
    logger.info(f"成功: {total_success}/{len(AVAILABLE_SPIDERS)}")
    logger.info(f"失败: {total_failed}/{len(AVAILABLE_SPIDERS)}")

    return 0 if total_failed == 0 else 1


def main():
    """主程序"""
    parser = argparse.ArgumentParser(
        description="运行药企爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行恒瑞医药爬虫
  python scripts/run_crawler.py --company hengrui

  # 仅分析网站
  python scripts/run_crawler.py --company hengrui --analyze-only

  # 运行所有爬虫
  python scripts/run_crawler.py --all
        """
    )

    parser.add_argument(
        "--company",
        choices=list(AVAILABLE_SPIDERS.keys()),
        help="公司代码"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="运行所有爬虫"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="仅分析网站，不抓取数据"
    )

    args = parser.parse_args()

    # 检查参数
    if not args.company and not args.all:
        parser.print_help()
        logger.error("\n请指定 --company 或 --all")
        return 1

    # 运行爬虫
    if args.all:
        return run_all_spiders()
    else:
        return run_spider(args.company, args.analyze_only)


if __name__ == "__main__":
    sys.exit(main())
