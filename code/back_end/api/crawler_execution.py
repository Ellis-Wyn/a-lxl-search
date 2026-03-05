"""
=====================================================
爬虫执行历史管理 API
=====================================================

提供以下端点：
- GET  /api/crawlers/executions           - 查询执行历史
- GET  /api/crawlers/executions/{id}       - 查询执行详情
- GET  /api/crawlers/{name}/history        - 查询单个爬虫历史
- GET  /api/crawlers/stats                 - 查询统计信息
- GET  /api/crawlers/health                - 查询健康状态
- GET  /api/crawlers/failures              - 查询失败记录

作者：A_lxl_search Team
创建日期：2026-02-04
=====================================================
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.crawler_execution_service import CrawlerExecutionService
from crawlers import list_spiders
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/crawlers", tags=["爬虫执行历史"])


# =====================================================
# Pydantic 数据模型
# =====================================================

class ExecutionLogResponse(BaseModel):
    """执行日志响应模型"""
    log_id: str
    execution_id: str
    spider_name: str
    trigger_type: str
    started_at: str
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: str
    retry_count: int
    items_fetched: int
    items_succeeded: int
    items_failed: int
    items_skipped: int
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """统计信息响应模型"""
    spider_name: str
    total_runs: int
    success_count: int
    failed_count: int
    success_rate: float
    avg_duration: float
    last_run: Optional[str] = None
    consecutive_failures: int
    health_status: str


class HealthResponse(BaseModel):
    """健康状态响应模型"""
    healthy: List[str]
    degraded: List[str]
    unhealthy: List[str]


# =====================================================
# API 端点
# =====================================================

@router.get("/executions", response_model=Dict[str, Any])
async def get_executions(
    spider_name: Optional[str] = Query(None, description="爬虫名称过滤"),
    trigger_type: Optional[str] = Query(None, description="触发方式过滤（scheduler/manual/api）"),
    status_filter: Optional[str] = Query(None, description="状态过滤（running/completed/failed）", alias="status"),
    days: int = Query(7, description="最近N天", ge=1, le=365),
    limit: int = Query(50, description="每页数量", ge=1, le=1000),
    offset: int = Query(0, description="偏移量", ge=0)
):
    """
    查询执行历史

    返回信息：
    - total: 总数量
    - executions: 执行日志列表
    - summary: 汇总统计
    """
    service = CrawlerExecutionService()

    try:
        executions = service.get_execution_history(
            spider_name=spider_name,
            trigger_type=trigger_type,
            status=status_filter,
            days=days,
            limit=limit,
            offset=offset
        )

        # 转换为响应格式
        executions_data = [log.to_dict() for log in executions]

        # 计算汇总统计
        total = len(executions)
        success_count = sum(1 for e in executions if e.status == "completed")
        failed_count = sum(1 for e in executions if e.status == "failed")
        durations = [e.duration_seconds for e in executions if e.duration_seconds]

        summary = {
            "total_runs": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "success_rate": (success_count / total * 100) if total > 0 else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0
        }

        return {
            "total": total,
            "executions": executions_data,
            "summary": summary
        }

    finally:
        service.close()


@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_execution_detail(execution_id: str):
    """
    查询单个执行记录详情

    Args:
        execution_id: 执行ID

    Returns:
        执行记录详情
    """
    service = CrawlerExecutionService()

    try:
        log = service.get_execution_log(execution_id)

        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution log not found: {execution_id}"
            )

        return log.to_dict()

    finally:
        service.close()


@router.get("/{spider_name}/history", response_model=Dict[str, Any])
async def get_spider_history(
    spider_name: str,
    days: int = Query(30, description="最近N天", ge=1, le=365),
    limit: int = Query(100, description="最大数量", ge=1, le=1000)
):
    """
    查询单个爬虫的执行历史

    Args:
        spider_name: 爬虫名称
        days: 最近N天
        limit: 最大数量

    Returns:
        执行历史列表
    """
    service = CrawlerExecutionService()

    try:
        # 检查爬虫是否存在
        available_spiders = list_spiders()
        if spider_name not in available_spiders:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Spider '{spider_name}' not found. Available: {', '.join(available_spiders)}"
            )

        executions = service.get_execution_history(
            spider_name=spider_name,
            days=days,
            limit=limit
        )

        return {
            "spider_name": spider_name,
            "total": len(executions),
            "executions": [log.to_dict() for log in executions]
        }

    finally:
        service.close()


@router.get("/stats", response_model=Dict[str, Any])
async def get_crawlers_stats(
    spider_name: Optional[str] = Query(None, description="爬虫名称（不填则返回所有）")
):
    """
    查询爬虫统计信息

    返回信息：
    - spider_name: 爬虫名称
    - total_runs: 总运行次数
    - success_rate: 成功率
    - avg_duration: 平均执行时长
    - consecutive_failures: 连续失败次数
    - health_status: 健康状态
    - last_run: 最后运行时间

    如果不指定spider_name，返回所有爬虫的统计信息
    """
    service = CrawlerExecutionService()

    try:
        if spider_name:
            # 返回单个爬虫的统计
            summary = service.get_spider_summary(spider_name)

            # 获取连续失败次数
            consecutive_failures = service.get_consecutive_failure_count(spider_name)

            # 获取健康状态
            if consecutive_failures == 0:
                health_status = "healthy"
            elif consecutive_failures < 3:
                health_status = "degraded"
            else:
                health_status = "unhealthy"

            summary["consecutive_failures"] = consecutive_failures
            summary["health_status"] = health_status

            return summary

        else:
            # 返回所有爬虫的统计
            spiders = list_spiders()
            stats_list = []

            for spider in spiders:
                summary = service.get_spider_summary(spider, days=30)
                consecutive_failures = service.get_consecutive_failure_count(spider)

                if consecutive_failures == 0:
                    health_status = "healthy"
                elif consecutive_failures < 3:
                    health_status = "degraded"
                else:
                    health_status = "unhealthy"

                summary["consecutive_failures"] = consecutive_failures
                summary["health_status"] = health_status

                stats_list.append(summary)

            return {
                "total": len(stats_list),
                "stats": stats_list
            }

    finally:
        service.close()


@router.get("/health", response_model=HealthResponse)
async def get_crawlers_health():
    """
    查询所有爬虫的健康状态

    返回信息：
    - healthy: 健康的爬虫（连续失败0次）
    - degraded: 降级的爬虫（连续失败1-2次）
    - unhealthy: 不健康的爬虫（连续失败3次及以上）
    """
    service = CrawlerExecutionService()

    try:
        spiders = list_spiders()
        healthy = []
        degraded = []
        unhealthy = []

        for spider in spiders:
            consecutive_failures = service.get_consecutive_failure_count(spider)

            if consecutive_failures == 0:
                healthy.append(spider)
            elif consecutive_failures < 3:
                degraded.append(spider)
            else:
                unhealthy.append(spider)

        return {
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy
        }

    finally:
        service.close()


@router.get("/failures", response_model=Dict[str, Any])
async def get_recent_failures(
    spider_name: Optional[str] = Query(None, description="爬虫名称（可选）"),
    hours: int = Query(24, description="最近N小时", ge=1, le=168),
    limit: int = Query(50, description="最大数量", ge=1, le=1000)
):
    """
    查询最近的失败记录

    Args:
        spider_name: 爬虫名称（可选，不填则返回所有）
        hours: 最近N小时
        limit: 最大数量

    Returns:
        失败记录列表
    """
    service = CrawlerExecutionService()

    try:
        failures = service.get_failed_executions(
            spider_name=spider_name,
            hours=hours,
            limit=limit
        )

        # 获取失败统计
        failure_stats = service.get_failure_stats(spider_name=spider_name, days=max(1, hours // 24))

        return {
            "total": len(failures),
            "failures": [log.to_dict() for log in failures],
            "summary": failure_stats
        }

    finally:
        service.close()


__all__ = ["router"]
