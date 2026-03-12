"""
=====================================================
Pipeline History API - 管线历史记录 API
=====================================================

提供管线事件历史查询接口：
- GET /api/pipeline-history/{pipeline_id} - 获取管线完整时间线
- GET /api/pipeline-history/{pipeline_id}/events - 获取原始事件列表
- GET /api/pipeline-history/{pipeline_id}/statistics - 获取变更统计

作者：A_lxl_search Team
创建日期：2026-03-12
=====================================================
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from utils.database import get_db
from models.pipeline import Pipeline
from models.pipeline_event import PipelineEvent, EventType
from core.logger import get_logger

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/api/pipeline-history", tags=["Pipeline History"])


# =====================================================
# 请求/响应模型
# =====================================================


class EventResponse(BaseModel):
    """单个事件响应"""
    event_id: str
    event_type: str
    event_data: dict
    occurred_at: str
    source: str
    source_detail: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "a1b2c3d4-...",
                "event_type": "PHASE_CHANGED",
                "event_data": {
                    "old_phase": "I",
                    "new_phase": "II",
                    "is_forward": True,
                    "jumped": False,
                    "days_in_old_phase": 180
                },
                "occurred_at": "2025-06-15T10:30:00",
                "source": "crawler",
                "source_detail": "hengrui_spider"
            }
        }


class TimelineResponse(BaseModel):
    """时间线响应"""
    pipeline_id: str
    drug_code: str
    company_name: str
    indication: str
    current_phase: str
    current_status: str
    first_seen_at: Optional[str] = None
    timeline: List[EventResponse]
    statistics: dict

    class Config:
        json_schema_extra = {
            "example": {
                "pipeline_id": "xxx-xxx-xxx",
                "drug_code": "HRS-1234",
                "company_name": "恒瑞医药",
                "indication": "非小细胞肺癌",
                "current_phase": "III",
                "current_status": "active",
                "first_seen_at": "2025-01-01T00:00:00",
                "timeline": [],
                "statistics": {
                    "total_events": 5,
                    "phase_changes": 2,
                    "days_since_first_seen": 425,
                    "current_phase_duration_days": 90
                }
            }
        }


class PhaseVelocityResponse(BaseModel):
    """研发速度分析响应"""
    pipeline_id: str
    drug_code: str
    company_name: str
    phase_history: List[dict]
    total_days_active: Optional[int] = None
    avg_days_per_phase: dict
    phase_velocity_summary: str

    class Config:
        json_schema_extra = {
            "example": {
                "pipeline_id": "xxx-xxx-xxx",
                "drug_code": "HRS-1234",
                "company_name": "恒瑞医药",
                "phase_history": [
                    {"phase": "I", "started_at": "2025-01-01", "duration_days": 165},
                    {"phase": "II", "started_at": "2025-06-15", "duration_days": 168},
                    {"phase": "III", "started_at": "2025-12-01", "duration_days": 92}
                ],
                "total_days_active": 425,
                "avg_days_per_phase": {"I": 165, "II": 168, "III": 92},
                "phase_velocity_summary": "研发进度稳定，平均每个阶段约165天"
            }
        }


class HistoryStatisticsResponse(BaseModel):
    """历史统计响应"""
    total_events: int
    events_by_type: dict
    first_event_at: Optional[str] = None
    last_event_at: Optional[str] = None
    phase_changes_count: int
    target_changes_count: int
    status_changes_count: int


# =====================================================
# 辅助函数
# =====================================================


def _calculate_timeline_statistics(
    pipeline: Pipeline,
    events: List[PipelineEvent]
) -> dict:
    """
    计算时间线统计数据

    Args:
        pipeline: 管线对象
        events: 事件列表

    Returns:
        统计数据字典
    """
    stats = {
        "total_events": len(events),
        "phase_changes": 0,
        "target_added": 0,
        "target_removed": 0,
        "discontinued_count": 0,
        "reactivated_count": 0,
        "days_since_first_seen": None,
        "current_phase_duration_days": None,
    }

    # 统计各类型事件数量
    event_type_counts = {}
    for event in events:
        event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1

        if event.event_type == EventType.PHASE_CHANGED:
            stats["phase_changes"] += 1
        elif event.event_type == EventType.TARGET_ADDED:
            stats["target_added"] += 1
        elif event.event_type == EventType.TARGET_REMOVED:
            stats["target_removed"] += 1
        elif event.event_type == EventType.DISCONTINUED:
            stats["discontinued_count"] += 1
        elif event.event_type == EventType.REACTIVATED:
            stats["reactivated_count"] += 1

    stats["events_by_type"] = event_type_counts

    # 计算天数
    if pipeline.first_seen_at:
        stats["days_since_first_seen"] = (datetime.utcnow() - pipeline.first_seen_at).days

    # 计算当前阶段持续时间（通过最后一次 phase_changed 事件）
    last_phase_change = None
    for event in reversed(events):
        if event.event_type == EventType.PHASE_CHANGED:
            last_phase_change = event.occurred_at
            break

    if last_phase_change:
        stats["current_phase_duration_days"] = (datetime.utcnow() - last_phase_change).days

    return stats


def _build_phase_velocity(
    events: List[PipelineEvent],
    first_seen_at: datetime
) -> dict:
    """
    构建阶段速度分析

    Args:
        events: 事件列表（按时间排序）
        first_seen_at: 首次发现时间

    Returns:
        阶段速度分析数据
    """
    phase_history = []
    phase_start_times = {}
    current_phase = None
    phase_start = first_seen_at

    # 获取 CREATED 事件的初始 phase
    for event in events:
        if event.event_type == EventType.CREATED:
            initial_phase = event.event_data.get("initial_phase")
            if initial_phase:
                current_phase = initial_phase
                phase_start_times[current_phase] = first_seen_at
                phase_history.append({
                    "phase": current_phase,
                    "started_at": first_seen_at.isoformat(),
                    "duration_days": None
                })
            break

    # 处理 PHASE_CHANGED 事件
    for event in events:
        if event.event_type == EventType.PHASE_CHANGED:
            old_phase = event.event_data.get("old_phase")
            new_phase = event.event_data.get("new_phase")
            occurred_at = event.occurred_at

            # 更新前一阶段的持续时间
            if phase_history and old_phase:
                phase_history[-1]["duration_days"] = (
                    occurred_at - phase_start_times.get(old_phase, occurred_at)
                ).days

            # 添加新阶段
            current_phase = new_phase
            phase_start_times[new_phase] = occurred_at
            phase_history.append({
                "phase": new_phase,
                "started_at": occurred_at.isoformat(),
                "duration_days": None
            })

    # 计算当前阶段持续时间
    if phase_history:
        last_phase = phase_history[-1]
        if last_phase["duration_days"] is None:
            started_at = datetime.fromisoformat(last_phase["started_at"])
            last_phase["duration_days"] = (datetime.utcnow() - started_at).days

    # 计算平均天数
    avg_days_per_phase = {}
    for item in phase_history:
        phase = item["phase"]
        duration = item.get("duration_days")
        if duration is not None:
            if phase not in avg_days_per_phase:
                avg_days_per_phase[phase] = []
            avg_days_per_phase[phase].append(duration)

    # 汇总平均
    for phase in avg_days_per_phase:
        durations = avg_days_per_phase[phase]
        avg_days_per_phase[phase] = sum(durations) // len(durations)

    return {
        "phase_history": phase_history,
        "avg_days_per_phase": avg_days_per_phase
    }


# =====================================================
# API 端点
# =====================================================


@router.get("/{pipeline_id}", response_model=TimelineResponse)
def get_pipeline_timeline(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    获取管线完整时间线

    返回管线的所有历史事件，按时间倒序排列
    """
    # 获取管线
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id
    ).first()

    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

    # 获取所有事件
    events = db.query(PipelineEvent).filter(
        PipelineEvent.pipeline_id == pipeline_id
    ).order_by(desc(PipelineEvent.occurred_at)).all()

    # 转换为响应格式
    timeline_events = [
        EventResponse(
            event_id=str(event.event_id),
            event_type=event.event_type,
            event_data=event.event_data,
            occurred_at=event.occurred_at.isoformat() if event.occurred_at else None,
            source=event.source,
            source_detail=event.source_detail
        )
        for event in events
    ]

    # 计算统计数据
    statistics = _calculate_timeline_statistics(pipeline, events)

    return TimelineResponse(
        pipeline_id=str(pipeline.pipeline_id),
        drug_code=pipeline.drug_code,
        company_name=pipeline.company_name,
        indication=pipeline.indication,
        current_phase=pipeline.phase,
        current_status=pipeline.status,
        first_seen_at=pipeline.first_seen_at.isoformat() if pipeline.first_seen_at else None,
        timeline=timeline_events,
        statistics=statistics
    )


@router.get("/{pipeline_id}/events", response_model=List[EventResponse])
def get_pipeline_events(
    pipeline_id: str,
    event_type: Optional[str] = Query(None, description="筛选事件类型"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    获取管线的原始事件列表

    支持按事件类型筛选和分页
    """
    # 验证管线存在
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id
    ).first()

    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

    # 构建查询
    query = db.query(PipelineEvent).filter(
        PipelineEvent.pipeline_id == pipeline_id
    )

    # 事件类型筛选
    if event_type:
        valid_types = EventType.all()
        if event_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event_type. Valid types: {valid_types}"
            )
        query = query.filter(PipelineEvent.event_type == event_type)

    # 排序和分页
    events = query.order_by(desc(PipelineEvent.occurred_at)).offset(offset).limit(limit).all()

    return [
        EventResponse(
            event_id=str(event.event_id),
            event_type=event.event_type,
            event_data=event.event_data,
            occurred_at=event.occurred_at.isoformat() if event.occurred_at else None,
            source=event.source,
            source_detail=event.source_detail
        )
        for event in events
    ]


@router.get("/{pipeline_id}/velocity", response_model=PhaseVelocityResponse)
def get_phase_velocity(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    获取管线研发速度分析

    分析各阶段持续时间，评估研发进度
    """
    # 获取管线
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id
    ).first()

    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

    # 获取所有事件（按时间正序）
    events = db.query(PipelineEvent).filter(
        PipelineEvent.pipeline_id == pipeline_id
    ).order_by(PipelineEvent.occurred_at.asc()).all()

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No events found for pipeline {pipeline_id}"
        )

    # 构建阶段速度数据
    velocity_data = _build_phase_velocity(events, pipeline.first_seen_at)

    # 计算总活跃天数
    total_days_active = None
    if pipeline.first_seen_at:
        if pipeline.status == "discontinued" and pipeline.discontinued_at:
            total_days_active = (pipeline.discontinued_at - pipeline.first_seen_at).days
        else:
            total_days_active = (datetime.utcnow() - pipeline.first_seen_at).days

    # 生成速度摘要
    phase_count = len(velocity_data["phase_history"])
    avg_days_per_phase = velocity_data["avg_days_per_phase"]
    if avg_days_per_phase:
        avg_duration = sum(avg_days_per_phase.values()) // len(avg_days_per_phase)
        summary = f"经过 {phase_count} 个阶段，平均每个阶段约 {avg_duration} 天"
    else:
        summary = f"经过 {phase_count} 个阶段"

    return PhaseVelocityResponse(
        pipeline_id=str(pipeline.pipeline_id),
        drug_code=pipeline.drug_code,
        company_name=pipeline.company_name,
        phase_history=velocity_data["phase_history"],
        total_days_active=total_days_active,
        avg_days_per_phase=velocity_data["avg_days_per_phase"],
        phase_velocity_summary=summary
    )


@router.get("/{pipeline_id}/statistics", response_model=HistoryStatisticsResponse)
def get_history_statistics(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    获取管线历史统计

    返回事件数量统计和分类汇总
    """
    # 验证管线存在
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id
    ).first()

    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

    # 获取所有事件
    events = db.query(PipelineEvent).filter(
        PipelineEvent.pipeline_id == pipeline_id
    ).all()

    # 统计事件类型
    events_by_type = {}
    for event in events:
        events_by_type[event.event_type] = events_by_type.get(event.event_type, 0) + 1

    # 统计各类变更
    phase_changes = events_by_type.get(EventType.PHASE_CHANGED, 0)
    target_changes = (
        events_by_type.get(EventType.TARGET_ADDED, 0) +
        events_by_type.get(EventType.TARGET_REMOVED, 0)
    )
    status_changes = (
        events_by_type.get(EventType.DISCONTINUED, 0) +
        events_by_type.get(EventType.REACTIVATED, 0)
    )

    return HistoryStatisticsResponse(
        total_events=len(events),
        events_by_type=events_by_type,
        first_event_at=events[-1].occurred_at.isoformat() if events else None,
        last_event_at=events[0].occurred_at.isoformat() if events else None,
        phase_changes_count=phase_changes,
        target_changes_count=target_changes,
        status_changes_count=status_changes
    )


@router.get("/{pipeline_id}/summary")
def get_timeline_summary(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    获取管线时间线摘要（简化版，用于前端悬停提示）

    返回格式化的阶段进展时间线，适用于 Tooltip 显示
    """
    # 获取管线
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_id == pipeline_id
    ).first()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # 获取 Phase 变更事件（按时间正序）
    phase_events = db.query(PipelineEvent).filter(
        PipelineEvent.pipeline_id == pipeline_id,
        PipelineEvent.event_type == EventType.PHASE_CHANGED
    ).order_by(PipelineEvent.occurred_at.asc()).all()

    # 获取创建事件
    created_event = db.query(PipelineEvent).filter(
        PipelineEvent.pipeline_id == pipeline_id,
        PipelineEvent.event_type == EventType.CREATED
    ).first()

    # 构建时间线
    timeline = []

    # 添加初始阶段
    if created_event:
        initial_phase = created_event.event_data.get("initial_phase", "Unknown")
        start_date = created_event.occurred_at.strftime("%Y-%m")
        timeline.append({
            "phase": initial_phase,
            "date": start_date,
            "is_current": len(phase_events) == 0
        })

    # 添加阶段变更
    for event in phase_events:
        new_phase = event.event_data.get("new_phase", "Unknown")
        date = event.occurred_at.strftime("%Y-%m")
        timeline.append({
            "phase": new_phase,
            "date": date,
            "is_current": event == phase_events[-1] if phase_events else False
        })

    # 如果没有任何历史事件，至少返回当前状态
    if not timeline and pipeline.first_seen_at:
        timeline.append({
            "phase": pipeline.phase,
            "date": pipeline.first_seen_at.strftime("%Y-%m"),
            "is_current": True
        })

    # 计算总活跃天数
    total_days = None
    if pipeline.first_seen_at:
        if pipeline.status == "discontinued" and pipeline.discontinued_at:
            total_days = (pipeline.discontinued_at - pipeline.first_seen_at).days
        else:
            total_days = (datetime.utcnow() - pipeline.first_seen_at).days

    return {
        "drug_code": pipeline.drug_code,
        "current_phase": pipeline.phase,
        "timeline": timeline,
        "total_days_active": total_days,
        "has_history": len(timeline) > 1
    }


__all__ = ["router"]
