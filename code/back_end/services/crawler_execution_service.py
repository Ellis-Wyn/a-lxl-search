"""
=====================================================
爬虫执行历史服务
=====================================================

核心功能：
- 记录每次爬虫执行的详细信息
- 查询执行历史（分页、过滤）
- 统计成功率
- 检测连续失败
- 更新统计数据

作者：A_lxl_search Team
创建日期：2026-02-04
=====================================================
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import uuid4
import traceback

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func

from models.crawler_execution_log import CrawlerExecutionLog
from models.crawler_statistics import CrawlerStatistics
from utils.database import SessionLocal
from core.logger import get_logger
from config import settings

logger = get_logger(__name__)


class CrawlerExecutionService:
    """
    爬虫执行历史服务

    功能：
    - 记录执行历史
    - 查询执行历史
    - 统计分析
    - 连续失败检测
    """

    def __init__(self, db: Session = None):
        """
        初始化服务

        Args:
            db: 数据库会话（可选，默认创建新的）
        """
        self.db = db or SessionLocal()
        self._should_close_db = db is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """关闭数据库连接"""
        if self._should_close_db and self.db:
            self.db.close()

    # =====================================================
    # 创建执行记录
    # =====================================================

    def create_execution_log(
        self,
        spider_name: str,
        trigger_type: str = "scheduler",
        scheduled_for: datetime = None,
        max_retries: int = 3
    ) -> CrawlerExecutionLog:
        """
        创建新的执行记录

        Args:
            spider_name: 爬虫名称
            trigger_type: 触发方式（scheduler/manual/api）
            scheduled_for: 计划执行时间
            max_retries: 最大重试次数

        Returns:
            CrawlerExecutionLog: 执行日志对象
        """
        execution_id = self._generate_execution_id(spider_name)

        log = CrawlerExecutionLog(
            execution_id=execution_id,
            spider_name=spider_name,
            trigger_type=trigger_type,
            started_at=datetime.utcnow(),
            status="running",
            max_retries=max_retries,
            scheduled_for=scheduled_for
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        logger.info(
            f"Created execution log: {execution_id} "
            f"(spider={spider_name}, trigger={trigger_type})"
        )

        return log

    # =====================================================
    # 更新执行记录
    # =====================================================

    def update_execution_log(
        self,
        execution_id: str,
        status: str = None,
        stats: Dict[str, Any] = None,
        error: Exception = None
    ) -> Optional[CrawlerExecutionLog]:
        """
        更新执行记录

        Args:
            execution_id: 执行ID
            status: 状态（completed/failed/retry）
            stats: 统计信息字典
            error: 异常对象（失败时）

        Returns:
            更新后的日志对象，如果未找到返回None
        """
        log = self.db.query(CrawlerExecutionLog).filter(
            CrawlerExecutionLog.execution_id == execution_id
        ).first()

        if not log:
            logger.warning(f"Execution log not found: {execution_id}")
            return None

        # 更新状态
        if status:
            log.status = status

        # 更新统计信息
        if stats:
            log.items_fetched = stats.get("items_fetched", 0)
            log.items_succeeded = stats.get("items_succeeded", 0)
            log.items_failed = stats.get("items_failed", 0)
            log.items_skipped = stats.get("items_skipped", 0)

            # 性能指标
            if "total_requests" in stats:
                log.total_requests = stats["total_requests"]
            if "successful_requests" in stats:
                log.successful_requests = stats["successful_requests"]
            if "failed_requests" in stats:
                log.failed_requests = stats["failed_requests"]
            if "cached_requests" in stats:
                log.cached_requests = stats["cached_requests"]
            if "avg_response_time" in stats:
                log.avg_response_time = stats["avg_response_time"]

        # 更新时间
        log.finished_at = datetime.utcnow()
        if log.started_at:
            log.duration_seconds = (log.finished_at - log.started_at).total_seconds()

        # 处理错误
        if error:
            log.error_message = str(error)
            log.error_type = error.__class__.__name__
            log.error_stack = traceback.format_exc()

        self.db.commit()
        self.db.refresh(log)

        # 更新统计数据
        self._update_stats_after_execution(log)

        return log

    # =====================================================
    # 查询执行历史
    # =====================================================

    def get_execution_history(
        self,
        spider_name: str = None,
        trigger_type: str = None,
        status: str = None,
        days: int = 7,
        limit: int = 50,
        offset: int = 0
    ) -> List[CrawlerExecutionLog]:
        """
        查询执行历史

        Args:
            spider_name: 爬虫名称过滤
            trigger_type: 触发方式过滤
            status: 状态过滤
            days: 最近N天
            limit: 每页数量
            offset: 偏移量

        Returns:
            执行日志列表
        """
        query = self.db.query(CrawlerExecutionLog)

        # 时间过滤
        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(CrawlerExecutionLog.started_at >= cutoff_date)

        # 爬虫名称过滤
        if spider_name:
            query = query.filter(CrawlerExecutionLog.spider_name == spider_name)

        # 触发方式过滤
        if trigger_type:
            query = query.filter(CrawlerExecutionLog.trigger_type == trigger_type)

        # 状态过滤
        if status:
            query = query.filter(CrawlerExecutionLog.status == status)

        # 排序和分页
        query = query.order_by(desc(CrawlerExecutionLog.started_at))
        query = query.limit(limit).offset(offset)

        return query.all()

    def get_execution_log(self, execution_id: str) -> Optional[CrawlerExecutionLog]:
        """
        获取单个执行记录

        Args:
            execution_id: 执行ID

        Returns:
            执行日志对象，未找到返回None
        """
        return self.db.query(CrawlerExecutionLog).filter(
            CrawlerExecutionLog.execution_id == execution_id
        ).first()

    def get_recent_executions(
        self,
        spider_name: str,
        hours: int = 24,
        limit: int = 10
    ) -> List[CrawlerExecutionLog]:
        """
        获取最近N小时的执行记录

        Args:
            spider_name: 爬虫名称
            hours: 小时数
            limit: 最大数量

        Returns:
            执行日志列表
        """
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)

        return self.db.query(CrawlerExecutionLog).filter(
            and_(
                CrawlerExecutionLog.spider_name == spider_name,
                CrawlerExecutionLog.started_at >= cutoff_date
            )
        ).order_by(desc(CrawlerExecutionLog.started_at)).limit(limit).all()

    def get_failed_executions(
        self,
        spider_name: str = None,
        hours: int = 24,
        limit: int = 50
    ) -> List[CrawlerExecutionLog]:
        """
        获取失败的执行记录

        Args:
            spider_name: 爬虫名称（可选）
            hours: 最近N小时
            limit: 最大数量

        Returns:
            失败的执行日志列表
        """
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(CrawlerExecutionLog).filter(
            and_(
                CrawlerExecutionLog.status == "failed",
                CrawlerExecutionLog.started_at >= cutoff_date
            )
        )

        if spider_name:
            query = query.filter(CrawlerExecutionLog.spider_name == spider_name)

        return query.order_by(desc(CrawlerExecutionLog.started_at)).limit(limit).all()

    # =====================================================
    # 统计分析
    # =====================================================

    def get_failure_stats(
        self,
        spider_name: str = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取失败统计

        Args:
            spider_name: 爬虫名称（可选）
            days: 最近N天

        Returns:
            统计字典
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(
            func.count(CrawlerExecutionLog.log_id).label("total"),
            func.sum(
                func.case(
                    (CrawlerExecutionLog.status == "completed", 1),
                    else_=0
                )
            ).label("success"),
            func.sum(
                func.case(
                    (CrawlerExecutionLog.status == "failed", 1),
                    else_=0
                )
            ).label("failed")
        ).filter(CrawlerExecutionLog.started_at >= cutoff_date)

        if spider_name:
            query = query.filter(CrawlerExecutionLog.spider_name == spider_name)

        result = query.first()

        return {
            "spider_name": spider_name or "all",
            "days": days,
            "total_runs": result.total or 0,
            "success_count": result.success or 0,
            "failed_count": result.failed or 0,
            "success_rate": (result.success / result.total * 100) if result.total > 0 else 0
        }

    def get_spider_summary(self, spider_name: str, days: int = 30) -> Dict[str, Any]:
        """
        获取爬虫执行摘要

        Args:
            spider_name: 爬虫名称
            days: 最近N天

        Returns:
            摘要字典
        """
        logs = self.get_execution_history(spider_name=spider_name, days=days, limit=10000)

        if not logs:
            return {
                "spider_name": spider_name,
                "total_runs": 0,
                "success_rate": 0,
                "avg_duration": 0,
                "last_run": None
            }

        total = len(logs)
        success_count = sum(1 for log in logs if log.status == "completed")
        durations = [log.duration_seconds for log in logs if log.duration_seconds]

        return {
            "spider_name": spider_name,
            "total_runs": total,
            "success_count": success_count,
            "failed_count": total - success_count,
            "success_rate": (success_count / total * 100) if total > 0 else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "last_run": logs[0].started_at.isoformat() if logs else None
        }

    # =====================================================
    # 连续失败检测
    # =====================================================

    def check_consecutive_failures(
        self,
        spider_name: str,
        threshold: int = 3
    ) -> bool:
        """
        检查是否连续失败N次

        Args:
            spider_name: 爬虫名称
            threshold: 阈值

        Returns:
            是否达到阈值
        """
        # 获取最近的执行记录
        recent_logs = self.get_recent_executions(spider_name, hours=168, limit=threshold + 1)  # 7天

        if len(recent_logs) < threshold:
            return False

        # 检查最近N次是否都失败
        recent_failures = sum(1 for log in recent_logs[:threshold] if log.status == "failed")

        return recent_failures >= threshold

    def get_consecutive_failure_count(self, spider_name: str) -> int:
        """
        获取连续失败次数

        Args:
            spider_name: 爬虫名称

        Returns:
            连续失败次数
        """
        recent_logs = self.get_recent_executions(spider_name, hours=168, limit=100)  # 7天

        count = 0
        for log in recent_logs:
            if log.status == "failed":
                count += 1
            else:
                break

        return count

    # =====================================================
    # 内部方法
    # =====================================================

    def _generate_execution_id(self, spider_name: str) -> str:
        """
        生成执行ID

        Args:
            spider_name: 爬虫名称

        Returns:
            执行ID（格式：timestamp_uuid）
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid4())[:8]
        return f"{timestamp}_{unique_id}"

    def _send_failure_alert(self, log: CrawlerExecutionLog, stats: CrawlerStatistics):
        """
        发送爬虫失败告警

        Args:
            log: 执行日志对象
            stats: 统计数据对象
        """
        try:
            from services.alert_service import get_alert_service

            alert_service = get_alert_service()

            # 创建告警
            alert = alert_service.create_crawler_failure_alert(
                spider_name=log.spider_name,
                consecutive_failures=stats.consecutive_failures,
                last_error=log.error_message or "Unknown error",
                last_failure_time=log.finished_at or datetime.utcnow(),
                total_attempts=stats.total_runs
            )

            # 发送告警
            alert_service.send_alert(alert)

            # 标记告警已发送
            stats.mark_alert_sent()
            self.db.commit()

            logger.info(
                f"✓ Alert sent for spider '{log.spider_name}' "
                f"(consecutive_failures={stats.consecutive_failures})"
            )

        except Exception as e:
            logger.error(f"Failed to send alert for spider '{log.spider_name}': {e}")

    def _update_stats_after_execution(self, log: CrawlerExecutionLog):
        """
        执行完成后更新统计数据

        Args:
            log: 执行日志对象
        """
        # 获取或创建统计记录
        stats = self.db.query(CrawlerStatistics).filter(
            CrawlerStatistics.spider_name == log.spider_name
        ).first()

        if not stats:
            stats = CrawlerStatistics(spider_name=log.spider_name)
            self.db.add(stats)
            self.db.commit()
            self.db.refresh(stats)

        # 更新统计
        duration = log.duration_seconds or 0

        if log.status == "completed":
            stats.record_success(duration, log.items_succeeded)
        elif log.status == "failed":
            error_msg = log.error_message or "Unknown error"
            stats.record_failure(duration, error_msg)

        self.db.commit()

        # 检查是否需要告警
        if stats.should_alert():
            logger.warning(
                f"⚠️  Spider {log.spider_name} has {stats.consecutive_failures} "
                f"consecutive failures!"
            )

            # 发送告警通知
            if settings.CRAWLER_ALERT_ENABLED:
                self._send_failure_alert(log, stats)


__all__ = ["CrawlerExecutionService"]
