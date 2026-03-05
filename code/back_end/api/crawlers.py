"""
=====================================================
爬虫调度器管理 API
=====================================================

提供以下端点：
- GET  /api/crawlers/status              - 获取调度器状态
- POST /api/crawlers/trigger             - 立即触发所有爬虫
- POST /api/crawlers/trigger/{name}      - 触发单个爬虫
- POST /api/crawlers/pause               - 暂停调度器
- POST /api/crawlers/resume              - 恢复调度器
- GET  /api/crawlers/list                - 列出所有爬虫

作者：A_lxl_search Team
创建日期：2026-02-03
=====================================================
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime

from crawlers.scheduler import get_scheduler
from crawlers import list_spiders, get_spider
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/crawlers", tags=["爬虫管理"])


@router.get("/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """
    获取调度器状态

    返回信息：
    - enabled: 是否启用
    - running: 是否运行中
    - scheduled_time: 调度时间
    - max_concurrent: 最大并发数
    - next_run_time: 下次运行时间
    - stats: 运行统计
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    return scheduler.get_status()


@router.post("/trigger")
async def trigger_all_crawlers():
    """
    立即触发所有爬虫运行（异步任务）

    注意：此接口立即返回，爬虫在后台运行
    可以通过 /api/crawlers/status 查看运行状态
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    # 异步触发
    import asyncio
    asyncio.create_task(scheduler.trigger_now())

    return {
        "message": "Crawlers triggered successfully",
        "triggered_at": datetime.now().isoformat(),
        "note": "Running in background, check /api/crawlers/status for progress"
    }


@router.post("/trigger/{spider_name}")
async def trigger_single_crawler(spider_name: str) -> Dict[str, Any]:
    """
    触发单个爬虫运行

    Args:
        spider_name: 爬虫名称（如 hengrui, beigene）

    Returns:
        爬虫运行结果
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    # 检查爬虫是否存在
    available_spiders = list_spiders()
    if spider_name not in available_spiders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spider '{spider_name}' not found. Available: {', '.join(available_spiders)}"
        )

    # 运行爬虫
    try:
        result = await scheduler.trigger_spider(spider_name)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error triggering spider {spider_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering spider: {str(e)}"
        )


@router.post("/pause")
async def pause_scheduler():
    """
    暂停调度器（不影响当前运行的任务）
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    scheduler.pause()
    return {"message": "Scheduler paused"}


@router.post("/resume")
async def resume_scheduler():
    """
    恢复调度器
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized"
        )

    scheduler.resume()
    return {"message": "Scheduler resumed"}


@router.get("/list")
async def list_available_crawlers():
    """
    列出所有可用的爬虫

    Returns:
        爬虫列表及详细信息
    """
    spiders = list_spiders()

    # 获取每个爬虫的详细信息
    spider_details = []
    for name in spiders:
        SpiderClass = get_spider(name)
        if SpiderClass:
            try:
                spider_instance = SpiderClass()
                spider_details.append({
                    "name": name,
                    "company_name": getattr(spider_instance, 'company_name', name),
                    "base_url": getattr(spider_instance, 'base_url', None)
                })
            except Exception as e:
                logger.warning(f"Error instantiating spider {name}: {e}")
                spider_details.append({
                    "name": name,
                    "company_name": name,
                    "base_url": None,
                    "error": str(e)
                })

    return {
        "total": len(spiders),
        "spiders": spider_details
    }


__all__ = ["router"]
