"""
=====================================================
Pipeline Event Model - 管线事件历史表
=====================================================

记录管线全生命周期的所有变更事件：
- 创建事件：管线首次被发现
- Phase 变更：研发阶段变化
- 适应症变更：indication 内容变化
- 靶点变更：targets 新增或移除
- 终止事件：status 变为 discontinued
- 重新激活：从 discontinued 恢复为 active

设计模式：事件溯源（Event Sourcing）
- 存储事件而非差异
- 可重放任意时间点状态
- 支持完整的审计追溯

作者：A_lxl_search Team
创建日期：2026-03-12
=====================================================
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from utils.database import Base


class PipelineEvent(Base):
    """
    管线事件表

    记录管线的所有状态变更事件，支持：
    1. 完整的审计追溯
    2. 研发速度分析
    3. 竞品对比分析
    4. 异常检测（Phase Jump 等）
    """

    __tablename__ = "pipeline_event"

    # =====================================================
    # 主键
    # =====================================================
    event_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="事件唯一标识"
    )

    # =====================================================
    # 关联管线
    # =====================================================
    pipeline_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pipeline.pipeline_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的管线ID"
    )

    # =====================================================
    # 事件类型
    # =====================================================
    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="""
        事件类型：
        - CREATED: 管线首次创建
        - PHASE_CHANGED: 研发阶段变更
        - INDICATION_CHANGED: 适应症变更
        - TARGET_ADDED: 新增靶点
        - TARGET_REMOVED: 移除靶点
        - MODALITY_CHANGED: 药物类型变更
        - DISCONTINUED: 管线终止
        - REACTIVATED: 重新激活
        - COMBINATION_CHANGED: 联合用药变更
        """
    )

    # =====================================================
    # 事件数据（JSONB，灵活存储）
    # =====================================================
    event_data = Column(
        JSONB,
        nullable=False,
        comment="""
        事件详细数据（JSON格式）：

        CREATED:
          {"initial_phase": "I", "initial_indication": "...", "initial_targets": [...]}

        PHASE_CHANGED:
          {"old_phase": "I", "new_phase": "II", "is_forward": true,
           "days_in_old_phase": 180, "jumped": false}

        INDICATION_CHANGED:
          {"old_indication": "非小细胞肺癌", "new_indication": "肺癌"}

        TARGET_ADDED:
          {"target_name": "EGFR", "is_primary": true}

        TARGET_REMOVED:
          {"target_name": "PD-1", "reason": "..."}

        DISCONTINUED:
          {"reason": "not_found_on_website", "days_active": 425,
           "last_phase": "III"}

        REACTIVATED:
          {"days_discontinued": 30, "reason": "reappeared_on_website"}
        """
    )

    # =====================================================
    # 时间线
    # =====================================================
    occurred_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="事件发生时间"
    )

    # =====================================================
    # 数据来源
    # =====================================================
    source = Column(
        String(50),
        nullable=False,
        default="crawler",
        comment="数据来源：crawler/manual/api/import"
    )

    source_detail = Column(
        String(255),
        comment="""
        来源详情：
        - crawler: hengrui_spider, beigene_spider, ...
        - manual: 用户ID
        - api: API endpoint
        - import: 导入批次ID
        """
    )

    # =====================================================
    # 审计字段
    # =====================================================
    version = Column(
        Integer,
        nullable=False,
        default=1,
        comment="版本号，用于审计追踪"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="记录创建时间"
    )

    # =====================================================
    # 关系
    # =====================================================
    pipeline = relationship(
        "Pipeline",
        back_populates="events",
        lazy="joined"
    )

    # =====================================================
    # 复合索引（优化查询）
    # =====================================================
    __table_args__ = (
        Index("ix_pipeline_event_timeline", "pipeline_id", "occurred_at"),
        Index("ix_pipeline_event_type_timeline", "event_type", "occurred_at"),
    )

    # =====================================================
    # 类方法：创建事件
    # =====================================================

    @classmethod
    def create(
        cls,
        db,
        pipeline_id: str,
        event_type: str,
        event_data: dict,
        source: str = "crawler",
        source_detail: str = None
    ) -> "PipelineEvent":
        """
        创建新事件

        Args:
            db: 数据库会话
            pipeline_id: 管线ID
            event_type: 事件类型
            event_data: 事件数据（字典）
            source: 数据来源
            source_detail: 来源详情

        Returns:
            PipelineEvent: 创建的事件对象
        """
        event = cls(
            pipeline_id=pipeline_id,
            event_type=event_type,
            event_data=event_data,
            source=source,
            source_detail=source_detail
        )
        db.add(event)
        return event

    # =====================================================
    # 实例方法
    # =====================================================

    def to_dict(self) -> dict:
        """
        转换为字典

        Returns:
            dict: 事件信息
        """
        return {
            "event_id": str(self.event_id),
            "pipeline_id": str(self.pipeline_id),
            "event_type": self.event_type,
            "event_data": self.event_data,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "source": self.source,
            "source_detail": self.source_detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<PipelineEvent({self.event_type} at {self.occurred_at})>"


# =====================================================
# 事件类型常量
# =====================================================

class EventType:
    """事件类型常量"""
    CREATED = "CREATED"
    PHASE_CHANGED = "PHASE_CHANGED"
    INDICATION_CHANGED = "INDICATION_CHANGED"
    TARGET_ADDED = "TARGET_ADDED"
    TARGET_REMOVED = "TARGET_REMOVED"
    MODALITY_CHANGED = "MODALITY_CHANGED"
    DISCONTINUED = "DISCONTINUED"
    REACTIVATED = "REACTIVATED"
    COMBINATION_CHANGED = "COMBINATION_CHANGED"

    @classmethod
    def all(cls) -> list:
        """获取所有事件类型"""
        return [
            cls.CREATED,
            cls.PHASE_CHANGED,
            cls.INDICATION_CHANGED,
            cls.TARGET_ADDED,
            cls.TARGET_REMOVED,
            cls.MODALITY_CHANGED,
            cls.DISCONTINUED,
            cls.REACTIVATED,
            cls.COMBINATION_CHANGED,
        ]


__all__ = ["PipelineEvent", "EventType"]
