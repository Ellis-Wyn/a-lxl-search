"""
=====================================================
CrawlerStats ORM 模型（爬虫统计数据表）
=====================================================

汇总每个爬虫的统计数据：
- 累计统计（总运行次数、成功率）
- 最近执行信息
- 连续失败追踪
- 性能统计
- 告警状态

核心功能：
- 快速查询爬虫状态
- 连续失败检测
- 告警触发
- 性能基线

作者：A_lxl_search Team
创建日期：2026-02-04
=====================================================
"""

from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from utils.database import Base


class CrawlerStatistics(Base):
    """
    爬虫统计数据汇总表

    核心设计：
    - 每个爬虫一条记录（按spider_name唯一）
    - 累计统计数据（不删除历史）
    - 连续失败计数（用于告警）
    - 性能基线（平均值、最小值、最大值）
    """

    __tablename__ = "crawler_stats"

    # =====================================================
    # 主键
    # =====================================================
    stat_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="统计记录主键"
    )

    # =====================================================
    # 统计维度
    # =====================================================
    spider_name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="爬虫名称（唯一标识）"
    )

    # =====================================================
    # 累计统计
    # =====================================================
    total_runs = Column(
        Integer,
        default=0,
        comment="总运行次数"
    )
    total_success = Column(
        Integer,
        default=0,
        comment="成功次数"
    )
    total_failed = Column(
        Integer,
        default=0,
        comment="失败次数"
    )
    total_items_fetched = Column(
        Integer,
        default=0,
        comment="总抓取条目数"
    )
    total_items_succeeded = Column(
        Integer,
        default=0,
        comment="总成功条目数"
    )

    # =====================================================
    # 成功率
    # =====================================================
    success_rate = Column(
        Float,
        default=0.0,
        comment="成功率（百分比）"
    )

    # =====================================================
    # 最近执行
    # =====================================================
    last_run_time = Column(
        DateTime,
        nullable=True,
        comment="最后运行时间"
    )
    last_run_status = Column(
        String(20),
        nullable=True,
        comment="最后运行状态（completed/failed）"
    )
    last_run_duration = Column(
        Float,
        nullable=True,
        comment="最后运行时长（秒）"
    )

    # =====================================================
    # 连续失败追踪
    # =====================================================
    consecutive_failures = Column(
        Integer,
        default=0,
        index=True,
        comment="连续失败次数"
    )
    last_failure_time = Column(
        DateTime,
        nullable=True,
        comment="最后失败时间"
    )
    last_failure_reason = Column(
        Text,
        nullable=True,
        comment="最后失败原因"
    )

    # =====================================================
    # 性能统计
    # =====================================================
    avg_duration = Column(
        Float,
        nullable=True,
        comment="平均执行时长（秒）"
    )
    min_duration = Column(
        Float,
        nullable=True,
        comment="最短执行时长（秒）"
    )
    max_duration = Column(
        Float,
        nullable=True,
        comment="最长执行时长（秒）"
    )

    # =====================================================
    # 告警状态
    # =====================================================
    alert_sent = Column(
        Boolean,
        default=False,
        comment="是否已发送告警"
    )
    last_alert_time = Column(
        DateTime,
        nullable=True,
        comment="最后告警时间"
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
        Index('idx_crawler_stats_consecutive_failures', 'consecutive_failures'),
    )

    # =====================================================
    # 业务方法
    # =====================================================

    def record_success(self, duration: float, items_succeeded: int = 0):
        """
        记录一次成功执行

        Args:
            duration: 执行时长（秒）
            items_succeeded: 成功条目数
        """
        self.total_runs += 1
        self.total_success += 1
        self.total_items_succeeded += items_succeeded

        # 更新最近执行
        self.last_run_time = datetime.utcnow()
        self.last_run_status = "completed"
        self.last_run_duration = duration

        # 重置连续失败计数
        self.consecutive_failures = 0
        self.alert_sent = False

        # 更新成功率
        self._update_success_rate()

        # 更新性能统计
        self._update_performance_stats(duration)

    def record_failure(self, duration: float, error_message: str = None):
        """
        记录一次失败执行

        Args:
            duration: 执行时长（秒）
            error_message: 错误信息
        """
        self.total_runs += 1
        self.total_failed += 1

        # 更新最近执行
        self.last_run_time = datetime.utcnow()
        self.last_run_status = "failed"
        self.last_run_duration = duration

        # 更新连续失败
        self.consecutive_failures += 1
        self.last_failure_time = datetime.utcnow()
        if error_message:
            self.last_failure_reason = error_message

        # 更新成功率
        self._update_success_rate()

        # 更新性能统计（失败也算）
        self._update_performance_stats(duration)

    def should_alert(self, threshold: int = 3, cooldown_minutes: int = 60) -> bool:
        """
        判断是否应该发送告警

        Args:
            threshold: 连续失败阈值
            cooldown_minutes: 告警冷却时间（分钟）

        Returns:
            是否应该发送告警
        """
        # 检查连续失败次数
        if self.consecutive_failures < threshold:
            return False

        # 检查是否已在冷却期内
        if self.alert_sent and self.last_alert_time:
            cooldown_end = self.last_alert_time.timestamp() + (cooldown_minutes * 60)
            if datetime.utcnow().timestamp() < cooldown_end:
                return False

        return True

    def mark_alert_sent(self):
        """标记已发送告警"""
        self.alert_sent = True
        self.last_alert_time = datetime.utcnow()

    def reset_consecutive_failures(self):
        """重置连续失败计数"""
        self.consecutive_failures = 0
        self.alert_sent = False

    def get_health_status(self, failure_threshold: int = 3) -> str:
        """
        获取健康状态

        Args:
            failure_threshold: 失败阈值

        Returns:
            healthy/degraded/unhealthy
        """
        if self.consecutive_failures == 0:
            return "healthy"
        elif self.consecutive_failures < failure_threshold:
            return "degraded"
        else:
            return "unhealthy"

    def _update_success_rate(self):
        """更新成功率"""
        if self.total_runs > 0:
            self.success_rate = (self.total_success / self.total_runs) * 100
        else:
            self.success_rate = 0.0

    def _update_performance_stats(self, duration: float):
        """
        更新性能统计

        Args:
            duration: 执行时长（秒）
        """
        # 更新平均值
        if self.avg_duration is None:
            self.avg_duration = duration
        else:
            # 使用移动平均
            self.avg_duration = (self.avg_duration * (self.total_runs - 1) + duration) / self.total_runs

        # 更新最小值
        if self.min_duration is None or duration < self.min_duration:
            self.min_duration = duration

        # 更新最大值
        if self.max_duration is None or duration > self.max_duration:
            self.max_duration = duration

    def to_dict(self) -> dict:
        """
        序列化为字典

        Returns:
            字典格式的统计数据
        """
        return {
            "stat_id": str(self.stat_id),
            "spider_name": self.spider_name,
            "total_runs": self.total_runs,
            "total_success": self.total_success,
            "total_failed": self.total_failed,
            "total_items_fetched": self.total_items_fetched,
            "total_items_succeeded": self.total_items_succeeded,
            "success_rate": round(self.success_rate, 2),
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_run_status": self.last_run_status,
            "last_run_duration": self.last_run_duration,
            "consecutive_failures": self.consecutive_failures,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_failure_reason": self.last_failure_reason,
            "avg_duration": self.avg_duration,
            "min_duration": self.min_duration,
            "max_duration": self.max_duration,
            "alert_sent": self.alert_sent,
            "last_alert_time": self.last_alert_time.isoformat() if self.last_alert_time else None,
            "health_status": self.get_health_status(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<CrawlerStats("
            f"spider_name={self.spider_name}, "
            f"total_runs={self.total_runs}, "
            f"success_rate={self.success_rate:.1f}%, "
            f"consecutive_failures={self.consecutive_failures})>"
        )


__all__ = ["CrawlerStatistics"]
