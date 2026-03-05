"""
=====================================================
Crawlers Module - 爬虫模块
=====================================================

自动发现和管理所有爬虫：
- 自动发现所有 spider 类
- 提供统一的爬虫注册表
- 支持按公司名称查询爬虫

已注册爬虫：
- 药企爬虫：hengrui, beigene, xindaa, junshi, akeso, zailab, hutchmed,
            ascentage, wuxibiologics, simcere, cspc, fosun
- 监管爬虫：cde (药审中心)

使用示例：
    from crawlers import discover_spiders, get_spider

    # 发现所有爬虫
    spiders = discover_spiders()
    print(f"Found {len(spiders)} spiders")

    # 获取特定爬虫
    spider_class = get_spider("hengrui")
    spider = spider_class()
    spider.run()

作者：A_lxl_search Team
创建日期：2026-02-02
=====================================================
"""

import importlib
import inspect
import os
from typing import Dict, List, Type, Optional
from pathlib import Path

from core.logger import get_logger

logger = get_logger(__name__)


# 爬虫注册表
SPIDER_REGISTRY: Dict[str, Type] = {}


def discover_spiders() -> Dict[str, Type]:
    """
    自动发现所有爬虫类

    通过扫描 crawlers 目录下的所有 .py 文件，
    查找使用了 @spider_register 装饰器的类

    Returns:
        爬虫类字典 {company_name: spider_class}

    Example:
        >>> spiders = discover_spiders()
        >>> print(f"Found {len(spiders)} spiders")
        >>> for name, cls in spiders.items():
        ...     print(f"  - {name}")
    """
    global SPIDER_REGISTRY

    if SPIDER_REGISTRY:
        logger.debug(f"Returning cached spider registry with {len(SPIDER_REGISTRY)} spiders")
        return SPIDER_REGISTRY

    # 获取当前目录
    current_dir = Path(__file__).parent

    # 扫描所有 Python 文件
    python_files = [f for f in current_dir.glob("*.py")
                   if f.name not in ["__init__.py", "base_spider.py", "runner.py"]]

    logger.info(f"Scanning for spiders in {len(python_files)} files...")

    for py_file in python_files:
        # 动态导入模块
        module_name = f"crawlers.{py_file.stem}"

        try:
            module = importlib.import_module(module_name)

            # 查找模块中的所有类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # 检查是否是爬虫类（有 spider_register 装饰器的类）
                if hasattr(obj, '_spider_name'):
                    spider_name = obj._spider_name
                    SPIDER_REGISTRY[spider_name] = obj
                    logger.info(f"✓ Discovered spider: {spider_name} ({obj.__name__})")

        except Exception as e:
            logger.warning(f"✗ Failed to import {module_name}: {e}")

    logger.info(f"✓ Discovered {len(SPIDER_REGISTRY)} spiders total")

    return SPIDER_REGISTRY


def get_spider(company_name: str) -> Optional[Type]:
    """
    获取指定公司的爬虫类

    Args:
        company_name: 公司名称（如 "hengrui", "beigene"）

    Returns:
        爬虫类，如果未找到返回 None

    Example:
        >>> SpiderClass = get_spider("hengrui")
        >>> if SpiderClass:
        ...     spider = SpiderClass()
        ...     spider.run()
    """
    spiders = discover_spiders()
    return spiders.get(company_name)


def list_spiders() -> List[str]:
    """
    列出所有可用的爬虫

    Returns:
        公司名称列表

    Example:
        >>> spiders = list_spiders()
        >>> print("Available spiders:")
        >>> for spider in spiders:
        ...     print(f"  - {spider}")
    """
    spiders = discover_spiders()
    return list(spiders.keys())


def run_spider(company_name: str):
    """
    运行指定爬虫

    Args:
        company_name: 公司名称

    Returns:
        爬虫统计信息

    Example:
        >>> stats = run_spider("hengrui")
        >>> print(f"Fetched: {stats.items_fetched}")
        >>> print(f"Succeeded: {stats.items_succeeded}")
    """
    SpiderClass = get_spider(company_name)

    if not SpiderClass:
        logger.error(f"Spider not found: {company_name}")
        logger.info(f"Available spiders: {', '.join(list_spiders())}")
        return None

    spider = SpiderClass()
    return spider.run()


def run_all_spiders():
    """
    运行所有爬虫

    Returns:
        统计信息字典 {company_name: stats}

    Example:
        >>> stats = run_all_spiders()
        >>> for company, stat in stats.items():
        ...     print(f"{company}: {stat.items_succeeded} items")
    """
    spiders = discover_spiders()
    all_stats = {}

    for company_name, SpiderClass in spiders.items():
        logger.info(f"Running spider: {company_name}")

        try:
            spider = SpiderClass()
            stats = spider.run()
            all_stats[company_name] = stats
        except Exception as e:
            logger.error(f"✗ Spider {company_name} failed: {e}")
            all_stats[company_name] = None

    return all_stats


# =====================================================
# 导出
# =====================================================

__all__ = [
    "discover_spiders",
    "get_spider",
    "list_spiders",
    "run_spider",
    "run_all_spiders",
]
