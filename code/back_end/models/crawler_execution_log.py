"""
=====================================================
CrawlerExecutionLog ORM 模型（爬虫执行日志表）
=====================================================

记录每次爬虫执行的详细信息：
- 执行时间（开始、结束、时长）
- 执行状态（running/completed/failed/retry）
- 统计数据（成功/失败条目数）
- 性能指标（请求数、响应时间）
- 错误信息

核心功能：
- 执行历史追踪
- 问题排查
- 性能分析
作者：A_lxl_search Team
创建日期：2026-02-04
=====================================================
"""

from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from utils.database import Base


class CrawlerExecutionLog(Base):
    """
    爬虫执行日志表

    核心设计：
    - 每次爬虫执行创建一条记录
    - 记录完整的执行生命周期
    - 支持详细的性能指标和错误追踪
    """

    __tablename__ = "crawler_execution_log"

    # =====================================================
    # 主键和标识
    # =====================================================
    log_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="日志记录主键"
    )
    execution_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="执行唯一标识（timestamp_uuid格式）"
    )
    spider_name = Column(
        String(100),
        nullable=False,
        index=True,
        comment="爬虫名称（hengrui, beigene等）"
    )
    trigger_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="触发方式：scheduler/manual/api"
    )

    # =====================================================
    # 时间信息
    # =====================================================
    started_at = Column(
        DateTime,
        nullable=False,
        index=True,
        default=datetime.utcnow,
        comment="开始执行时间"
    )
    finished_at = Column(
        DateTime,
        nullable=True,
        comment="结束执行时间"
    )
    duration_seconds = Column(
        Float,
        nullable=True,
        comment="执行时长（秒）"
    )

    # =====================================================
    # 执行状态
    # =====================================================
    status = Column(
        String(20),
        nullable=False,
        index=True,
        default="running",
        comment="状态：running/completed/failed/retry"
    )
    retry_count = Column(
        Integer,
        default=0,
        comment="当前重试次数"
    )
    max_retries = Column(
        Integer,
        default=3,
        comment="最大重试次数"
    )

    # =====================================================
    # 统计数据（条目级别）
    # =====================================================
    items_fetched = Column(
        Integer,
        default=0,
        comment="抓取的条目总数"
    )
    items_succeeded = Column(
        Integer,
        default=0,
        comment="成功保存的条目数"
    )
    items_failed = Column(
        Integer,
        default=0,
        comment="失败的条目数"
    )
    items_skipped = Column(
        Integer,
        default=0,
        comment="跳过的条目数（已存在）"
    )

    # =====================================================
    # 性能指标（HTTP请求级别）
    # =====================================================
    total_requests = Column(
        Integer,
        default=0,
        comment="总HTTP请求数"
    )
    successful_requests = Column(
        Integer,
        default=0,
        comment="成功的HTTP请求数"
    )
    failed_requests = Column(
        Integer,
        default=0,
        comment="失败的HTTP请求数"
    )
    cached_requests = Column(
        Integer,
        default=0,
        comment="缓存的HTTP请求数"
    )
    avg_response_time = Column(
        Float,
        nullable=True,
        comment="平均响应时间（秒）"
    )

    # =====================================================
    # 错误信息
    # =====================================================
    error_message = Column(
        Text,
        nullable=True,
        comment="错误信息"
    )
    error_stack = Column(
        Text,
        nullable=True,
        comment="错误堆栈"
    )
    error_type = Column(
        String(100),
        nullable=True,
        comment="错误类型（类名）"
    )

    # =====================================================
    # 元数据
    # =====================================================
    extra_data = Column(
        JSONB,
        nullable=True,
        comment="额外元数据（JSON格式）"
    )
    scheduled_for = Column(
        DateTime,
        nullable=True,
        comment="计划执行时间（scheduler触发时）"
    )

    # =====================================================
    # 时间戳
    # =====================================================
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="记录创建时间"
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="记录更新时间"
    )

    # =====================================================
    # 索引
    # =====================================================
    __table_args__ = (
        Index('idx_crawler_log_spider_started', 'spider_name', 'started_at'),
        Index('idx_crawler_log_status_started', 'status', 'started_at'),
    )

    # =====================================================
    # 业务方法
    # =====================================================

    def mark_completed(self, items_succeeded: int = None, items_failed: int = None):
        """
        标记执行为完成状态

        Args:
            items_succeeded: 成功条目数（可选）
            items_failed: 失败条目数（可选）
        """
        self.status = "completed"
        self.finished_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.finished_at - self.started_at).total_seconds()
        if items_succeeded is not None:
            self.items_succeeded = items_succeeded
        if items_failed is not None:
            self.items_failed = items_failed

    def mark_failed(self, error: Exception = None):
        """
        标记执行为失败状态

        Args:
            error: 异常对象（可选）
        """
        self.status = "failed"
        self.finished_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.finished_at - self.started_at).total_seconds()
        if error:
            self.error_message = str(error)
            self.error_type = error.__class__.__name__
            import traceback
            self.error_stack = traceback.format_exc()

    def mark_retry(self, retry_count: int):
        """
        标记执行为重试状态

        Args:
            retry_count: 当前重试次数
        """
        self.status = "retry"
        self.retry_count = retry_count

    def is_completed(self) -> bool:
        """判断是否已完成"""
        return self.status == "completed"

    def is_failed(self) -> bool:
        """判断是否失败"""
        return self.status == "failed"

    def is_running(self) -> bool:
        """判断是否正在运行"""
        return self.status == "running"

    def get_success_rate(self) -> float:
        """
        计算成功率

        Returns:
            成功率（0-100），如果没有条目则返回0
        """
        total = self.items_succeeded + self.items_failed
        if total == 0:
            return 0.0
        return (self.items_succeeded / total) * 100

    def to_dict(self) -> dict:
        """
        序列化为字典

        Returns:
            字典格式的执行日志
        """
        return {
            "log_id": str(self.log_id),
            "execution_id": self.execution_id,
            "spider_name": self.spider_name,
            "trigger_type": self.trigger_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "items_fetched": self.items_fetched,
            "items_succeeded": self.items_succeeded,
            "items_failed": self.items_failed,
            "items_skipped": self.items_skipped,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "cached_requests": self.cached_requests,
            "avg_response_time": self.avg_response_time,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "extra_data": self.extra_data,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<CrawlerExecutionLog("
            f"execution_id={self.execution_id}, "
            f"spider_name={self.spider_name}, "
            f"status={self.status}, "
            f"started_at={self.started_at})>"
        )


__all__ = ["CrawlerExecutionLog"]
