"""
=====================================================
爬虫调度器 - Crawler Scheduler
=====================================================

功能：
1. 定时执行所有爬虫（Cron调度）
2. 并发控制（限制最大并发数）
3. 运行状态管理
4. 错误处理和统计

集成方式：
    from crawlers.scheduler import init_scheduler, get_scheduler

    # 在FastAPI lifespan中启动
    scheduler = init_scheduler()
    await scheduler.start()

    # 在FastAPI lifespan中关闭
    scheduler = get_scheduler()
    await scheduler.shutdown()

作者：A_lxl_search Team
创建日期：2026-02-03
=====================================================
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from crawlers import list_spiders, run_spider
from core.logger import get_logger
from config import settings
from services.crawler_execution_service import CrawlerExecutionService
from services.crawler_retry_service import CrawlerRetryService

logger = get_logger(__name__)


class CrawlerScheduler:
    """
    爬虫调度器

    功能：
    - 定时触发所有爬虫（Cron调度）
    - 并发控制（Semaphore限制并发数）
    - 运行统计（成功/失败计数）
    - 手动触发和状态查询

    使用方式：
        scheduler = CrawlerScheduler()
        await scheduler.start()
    """

    def __init__(
        self,
        max_concurrent: int = None,
        scheduled_time: str = None,
        enabled: bool = None
    ):
        """
        初始化调度器

        Args:
            max_concurrent: 最大并发数（默认从配置读取）
            scheduled_time: 调度时间，格式"HH:MM"（默认从配置读取）
            enabled: 是否启用调度（默认从配置读取）
        """
        # 从配置读取参数
        self.max_concurrent = max_concurrent or settings.CRAWLER_SCHEDULER_MAX_CONCURRENT
        self.scheduled_time = scheduled_time or settings.CRAWLER_SCHEDULER_TIME
        self.enabled = enabled or settings.CRAWLER_SCHEDULER_ENABLED

        # 并发控制信号量
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        # APScheduler实例
        self.scheduler: Optional[AsyncIOScheduler] = None

        # 执行历史服务
        self.execution_service = CrawlerExecutionService()

        # 重试服务
        self.retry_service = CrawlerRetryService()

        # 统计信息（简单dict，不过度设计）
        self.stats: Dict[str, Any] = {
            "runs": 0,
            "success": 0,
            "failed": 0,
            "last_run_time": None,
            "current_run_status": "idle"  # idle, running
        }

        # 当前运行的任务列表
        self._current_tasks: List[asyncio.Task] = []

        logger.info(
            f"CrawlerScheduler initialized: "
            f"max_concurrent={self.max_concurrent}, "
            f"scheduled_time={self.scheduled_time}, "
            f"enabled={self.enabled}"
        )

    async def start(self):
        """
        启动调度器

        在FastAPI lifespan的启动阶段调用
        """
        if not self.enabled:
            logger.info("Crawler scheduler is disabled in configuration")
            return

        if self.scheduler and self.scheduler.running:
            logger.warning("Scheduler already running")
            return

        try:
            # 配置APScheduler
            self.scheduler = AsyncIOScheduler(timezone='Asia/Shanghai')

            # 解析调度时间
            hour, minute = self._parse_time(self.scheduled_time)

            # 添加定时任务
            self.scheduler.add_job(
                self._run_all,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='daily_crawl',
                name='Daily crawl all spiders',
                replace_existing=True
            )

            # 启动调度器
            self.scheduler.start()

            logger.info(
                f"✓ Crawler scheduler started: "
                f"scheduled at {self.scheduled_time} daily "
                f"(max_concurrent={self.max_concurrent})"
            )

        except Exception as e:
            logger.error(f"Scheduler start failed: {e}")
            # 不抛出异常，允许应用继续运行

    async def shutdown(self):
        """
        关闭调度器

        在FastAPI lifespan的关闭阶段调用
        """
        if not self.scheduler:
            return

        logger.info("Shutting down crawler scheduler...")

        try:
            # 等待当前运行的任务完成
            if self._current_tasks:
                logger.info(f"Waiting for {len(self._current_tasks)} running tasks to complete...")
                await asyncio.gather(*self._current_tasks, return_exceptions=True)
                self._current_tasks.clear()

            # 关闭调度器
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)

            logger.info("✓ Crawler scheduler stopped")

        except Exception as e:
            logger.error(f"Scheduler shutdown error: {e}")
            # 继续关闭流程

    async def trigger_now(self) -> Dict[str, Any]:
        """
        立即触发所有爬虫运行（手动触发）

        Returns:
            统计信息字典
        """
        logger.info("Manual trigger: running all crawlers now")
        return await self._run_all()

    async def trigger_spider(self, spider_name: str) -> Dict[str, Any]:
        """
        触发单个爬虫运行

        Args:
            spider_name: 爬虫名称（如"hengrui"）

        Returns:
            运行结果字典
        """
        # 检查爬虫是否存在
        available_spiders = list_spiders()
        if spider_name not in available_spiders:
            raise ValueError(
                f"Spider '{spider_name}' not found. "
                f"Available: {', '.join(available_spiders)}"
            )

        logger.info(f"Manual trigger: running spider '{spider_name}'")
        return await self._run_one(spider_name, trigger_type="manual")

    def pause(self):
        """暂停调度器（不影响当前运行的任务）"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.pause()
            logger.info("Scheduler paused")

    def resume(self):
        """恢复调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.resume()
            logger.info("Scheduler resumed")

    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态

        Returns:
            状态字典
        """
        job = None
        next_run_time = None
        if self.scheduler:
            job = self.scheduler.get_job('daily_crawl')
            if job:
                next_run_time = job.next_run_time

        return {
            "enabled": self.enabled,
            "scheduled_time": self.scheduled_time,
            "max_concurrent": self.max_concurrent,
            "running": self.scheduler.running if self.scheduler else False,
            "next_run_time": next_run_time.isoformat() if next_run_time else None,
            "stats": self.stats.copy()
        }

    async def _run_all(self) -> Dict[str, Any]:
        """
        运行所有爬虫（内部方法，Cron触发）

        Returns:
            统计信息字典
        """
        logger.info("=" * 60)
        logger.info("🚀 Starting scheduled crawler run...")
        logger.info("=" * 60)

        self.stats["current_run_status"] = "running"
        start_time = datetime.now()

        # 发现所有爬虫
        spider_names = list_spiders()
        logger.info(f"Found {len(spider_names)} spiders: {', '.join(spider_names)}")

        # 创建爬虫任务
        tasks = [
            self._run_one(name, trigger_type="scheduler")
            for name in spider_names
        ]

        # 等待所有任务完成（受信号量限制并发）
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for result in results:
            if isinstance(result, Exception):
                self.stats["failed"] += 1
            elif isinstance(result, dict) and result.get("success"):
                self.stats["success"] += 1
            else:
                self.stats["failed"] += 1

        # 更新统计
        self.stats["runs"] += 1
        self.stats["last_run_time"] = datetime.now().isoformat()
        self.stats["current_run_status"] = "completed"

        # 日志汇总
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(
            f"✓ Scheduled run completed: "
            f"{self.stats['success']} succeeded, "
            f"{self.stats['failed']} failed"
        )
        logger.info(f"  Total time: {duration:.2f}s")
        logger.info("=" * 60)

        return self.stats.copy()

    async def _run_one(self, spider_name: str, trigger_type: str = "scheduler") -> Dict[str, Any]:
        """
        运行单个爬虫（内部方法，带并发控制和重试）

        Args:
            spider_name: 爬虫名称
            trigger_type: 触发方式（scheduler/manual/api）

        Returns:
            运行结果字典
        """
        start_time = datetime.now()
        logger.info(f"🕷️  Starting spider: {spider_name}")

        # 创建执行日志
        execution_log = self.execution_service.create_execution_log(
            spider_name=spider_name,
            trigger_type=trigger_type,
            max_retries=settings.CRAWLER_RETRY_MAX_ATTEMPTS
        )
        execution_id = execution_log.execution_id

        # 使用信号量控制并发
        async with self.semaphore:
            try:
                # 使用重试服务执行爬虫
                if settings.CRAWLER_RETRY_ENABLED:
                    logger.info(f"Using retry service for {spider_name} (max_attempts={settings.CRAWLER_RETRY_MAX_ATTEMPTS})")
                    result = await self.retry_service.execute_with_retry(
                        spider_name=spider_name,
                        execute_func=lambda: run_spider(spider_name),
                        execution_service=self.execution_service,
                        trigger_type=trigger_type,
                        execution_id=execution_id
                    )
                else:
                    # 不使用重试，直接执行
                    loop = asyncio.get_event_loop()
                    stats = await loop.run_in_executor(None, run_spider, spider_name)

                    if stats is None:
                        raise Exception("Spider execution returned None")

                    result = {
                        "spider_name": spider_name,
                        "success": True,
                        "attempt": 1,
                        "result": stats
                    }

                end_time = datetime.now()
                total_duration = (end_time - start_time).total_seconds()

                # 更新执行日志（最终状态）
                if result["success"]:
                    stats = result.get("result")
                    logger.info(
                        f"✓ Spider {spider_name} completed: "
                        f"{stats.success if stats else 0} items in {total_duration:.2f}s "
                        f"(attempts={result.get('attempt', 1)})"
                    )

                    self.execution_service.update_execution_log(
                        execution_id=execution_id,
                        status="completed",
                        stats={
                            "items_fetched": stats.total_fetched if stats else 0,
                            "items_succeeded": stats.success if stats else 0,
                            "items_failed": stats.failed if stats else 0,
                            "items_skipped": stats.skipped if stats else 0,
                        }
                    )

                    return {
                        "spider_name": spider_name,
                        "success": True,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "duration_seconds": total_duration,
                        "attempts": result.get("attempt", 1),
                        "stats": {
                            "total_fetched": stats.total_fetched if stats else 0,
                            "success": stats.success if stats else 0,
                            "failed": stats.failed if stats else 0,
                            "skipped": stats.skipped if stats else 0,
                        }
                    }
                else:
                    # 所有重试都失败
                    logger.error(
                        f"✗ Spider {spider_name} failed after {result.get('attempt', 0)} attempts: "
                        f"{result.get('last_error', 'Unknown error')}"
                    )

                    self.execution_service.update_execution_log(
                        execution_id=execution_id,
                        status="failed",
                        error=Exception(result.get("last_error", "Unknown error"))
                    )

                    return {
                        "spider_name": spider_name,
                        "success": False,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "duration_seconds": total_duration,
                        "attempts": result.get("attempt", 0),
                        "error": result.get("last_error", "Unknown error"),
                        "error_type": result.get("error_type")
                    }

            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.error(f"✗ Spider {spider_name} raised unexpected exception: {e}", exc_info=True)

                # 更新执行日志
                self.execution_service.update_execution_log(
                    execution_id=execution_id,
                    status="failed",
                    error=e
                )

                return {
                    "spider_name": spider_name,
                    "success": False,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "error": str(e),
                    "error_type": e.__class__.__name__
                }

    @staticmethod
    def _parse_time(time_str: str) -> tuple:
        """
        解析时间字符串

        Args:
            time_str: 时间字符串，格式"HH:MM"

        Returns:
            (hour, minute) 元组
        """
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time range")
            return hour, minute
        except Exception as e:
            logger.warning(f"Invalid time format '{time_str}', using default 02:00: {e}")
            return 2, 0


# =====================================================
# 全局单例
# =====================================================

_scheduler_instance: Optional[CrawlerScheduler] = None


def get_scheduler() -> Optional[CrawlerScheduler]:
    """
    获取调度器单例

    Returns:
        调度器实例或None（如果未初始化）
    """
    return _scheduler_instance


def init_scheduler() -> CrawlerScheduler:
    """
    初始化调度器单例

    Returns:
        调度器实例
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CrawlerScheduler()
    return _scheduler_instance


# =====================================================
# 导出
# =====================================================

__all__ = [
    "CrawlerScheduler",
    "get_scheduler",
    "init_scheduler",
]
