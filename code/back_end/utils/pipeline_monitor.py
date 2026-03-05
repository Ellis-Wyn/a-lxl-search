"""
=====================================================
管线状态监控器（Pipeline Status Monitor）
=====================================================

监控管线状态变化，检测关键事件：
- Phase Jump（阶段跃迁）: Phase I → Phase II → Phase III
- Disappeared Pipeline（消失管线）: 90天未更新
- New Entry（新进场）: 首次出现的管线
- Regulatory Milestone（监管里程碑）: NDA/BLA提交、批准

使用示例：
    from utils.pipeline_monitor import PipelineMonitor, detect_phase_jump

    monitor = PipelineMonitor()

    # 检测Phase Jump
    result = monitor.check_phase_jump(
        old_phase="Phase I",
        new_phase="Phase II",
        company="Hengrui",
        drug_code="SHR-1210"
    )
    print(result.is_jump)  # True

    # 检测消失管线
    disappeared = monitor.check_disappeared(
        last_update_date="2024-10-01",
        threshold_days=90
    )
    print(disappeared)  # True
=====================================================
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from services.phase_mapper import PhaseMapper, StandardPhase


class ChangeType(Enum):
    """变化类型"""

    PHASE_JUMP = "Phase Jump"
    DISAPPEARED = "Disappeared"
    NEW_ENTRY = "New Entry"
    REGULATORY_MILESTONE = "Regulatory Milestone"
    NO_CHANGE = "No Change"


@dataclass
class PhaseChangeEvent:
    """阶段变化事件"""

    pipeline_id: str
    drug_code: str
    company_name: str
    old_phase: str
    new_phase: str
    change_type: ChangeType
    event_date: date
    description: str
    phase_jump_level: int = 0  # 跃迁级别（1=Phase I→II, 2=Phase II→III, 3=Phase III→Approved）

    def to_dict(self) -> Dict[str, any]:
        """转换为字典"""
        return {
            "pipeline_id": self.pipeline_id,
            "drug_code": self.drug_code,
            "company_name": self.company_name,
            "old_phase": self.old_phase,
            "new_phase": self.new_phase,
            "change_type": self.change_type.value,
            "event_date": self.event_date.isoformat(),
            "description": self.description,
            "phase_jump_level": self.phase_jump_level,
        }


@dataclass
class DisappearedPipelineEvent:
    """消失管线事件"""

    pipeline_id: str
    drug_code: str
    company_name: str
    last_phase: str
    last_seen_date: date
    days_since_update: int
    threshold_days: int
    is_disappeared: bool
    description: str

    def to_dict(self) -> Dict[str, any]:
        """转换为字典"""
        return {
            "pipeline_id": self.pipeline_id,
            "drug_code": self.drug_code,
            "company_name": self.company_name,
            "last_phase": self.last_phase,
            "last_seen_date": self.last_seen_date.isoformat(),
            "days_since_update": self.days_since_update,
            "threshold_days": self.threshold_days,
            "is_disappeared": self.is_disappeared,
            "description": self.description,
        }


@dataclass
class NewEntryEvent:
    """新进场事件"""

    pipeline_id: str
    drug_code: str
    company_name: str
    phase: str
    entry_date: date
    is_new: bool
    description: str

    def to_dict(self) -> Dict[str, any]:
        """转换为字典"""
        return {
            "pipeline_id": self.pipeline_id,
            "drug_code": self.drug_code,
            "company_name": self.company_name,
            "phase": self.phase,
            "entry_date": self.entry_date.isoformat(),
            "is_new": self.is_new,
            "description": self.description,
        }


class PipelineMonitor:
    """
    管线状态监控器

    检测Phase Jump、消失管线、新进场等关键事件
    """

    # 标准阶段顺序（用于判断Phase Jump）
    PHASE_ORDER = {
        StandardPhase.PRECLINICAL: 0,
        StandardPhase.PHASE_1: 1,
        StandardPhase.PHASE_2: 2,
        StandardPhase.PHASE_3: 3,
        StandardPhase.REGISTRATION: 4,
        StandardPhase.APPROVED: 5,
    }

    # 监管里程碑关键词
    REGULATORY_MILESTONES = [
        "nda",
        "bla",
        "filing",
        "submitted",
        "approved",
        "marketing authorization",
        "ema",
        "fda",
    ]

    def __init__(
        self,
        disappeared_threshold_days: int = 90,
        phase_mapper: Optional[PhaseMapper] = None,
    ):
        """
        初始化监控器

        Args:
            disappeared_threshold_days: 消失管线阈值（默认90天）
            phase_mapper: PhaseMapper实例（可选）
        """
        self.disappeared_threshold_days = disappeared_threshold_days
        self.phase_mapper = phase_mapper or PhaseMapper()

    def check_phase_jump(
        self,
        old_phase: str,
        new_phase: str,
        pipeline_id: str,
        drug_code: str,
        company_name: str,
        event_date: Optional[date | str] = None,
    ) -> PhaseChangeEvent:
        """
        检测Phase Jump（阶段跃迁）

        Args:
            old_phase: 旧阶段
            new_phase: 新阶段
            pipeline_id: 管线ID
            drug_code: 药物代码
            company_name: 公司名称
            event_date: 事件日期

        Returns:
            PhaseChangeEvent 对象

        Example:
            >>> monitor = PipelineMonitor()
            >>> event = monitor.check_phase_jump(
            ...     old_phase="Phase I",
            ...     new_phase="Phase II",
            ...     pipeline_id="123",
            ...     drug_code="SHR-1210",
            ...     company_name="Hengrui"
            ... )
            >>> print(event.is_jump)
            True
        """
        if event_date is None:
            event_date = date.today()
        elif isinstance(event_date, str):
            event_date = datetime.strptime(event_date, "%Y-%m-%d").date()

        # 标准化阶段
        old_standard = self.phase_mapper.map_to_standard(old_phase)
        new_standard = self.phase_mapper.map_to_standard(new_phase)

        # 获取阶段等级
        old_level = self.PHASE_ORDER.get(old_standard, -1)
        new_level = self.PHASE_ORDER.get(new_standard, -1)

        # 判断是否为Phase Jump（正向跃迁且等级提升）
        is_jump = new_level > old_level and old_level >= 0
        jump_level = new_level - old_level if is_jump else 0

        # 构建描述
        if is_jump:
            description = (
                f"Phase Jump detected: {old_phase} → {new_phase} "
                f"(+{jump_level} level)"
            )

            # 检查是否为监管里程碑
            if new_standard in [StandardPhase.FILING, StandardPhase.APPROVED]:
                description += f" [REGULATORY MILESTONE]"
        else:
            description = f"No phase jump: {old_phase} → {new_phase}"

        # 确定变化类型
        if is_jump:
            if jump_level >= 1:
                change_type = ChangeType.PHASE_JUMP
            else:
                change_type = ChangeType.NO_CHANGE
        else:
            change_type = ChangeType.NO_CHANGE

        return PhaseChangeEvent(
            pipeline_id=pipeline_id,
            drug_code=drug_code,
            company_name=company_name,
            old_phase=old_phase,
            new_phase=new_phase,
            change_type=change_type,
            event_date=event_date,
            description=description,
            phase_jump_level=jump_level,
        )

    def check_disappeared(
        self,
        pipeline_id: str,
        drug_code: str,
        company_name: str,
        last_phase: str,
        last_update_date: date | str,
        threshold_days: Optional[int] = None,
    ) -> DisappearedPipelineEvent:
        """
        检测消失管线

        Args:
            pipeline_id: 管线ID
            drug_code: 药物代码
            company_name: 公司名称
            last_phase: 最后已知阶段
            last_update_date: 最后更新日期
            threshold_days: 阈值天数（可选，默认使用实例值）

        Returns:
            DisappearedPipelineEvent 对象

        Example:
            >>> monitor = PipelineMonitor()
            >>> event = monitor.check_disappeared(
            ...     pipeline_id="123",
            ...     drug_code="SHR-1210",
            ...     company_name="Hengrui",
            ...     last_phase="Phase II",
            ...     last_update_date="2024-10-01"
            ... )
            >>> print(event.is_disappeared)
            True
        """
        if threshold_days is None:
            threshold_days = self.disappeared_threshold_days

        if isinstance(last_update_date, str):
            last_update_date = datetime.strptime(
                last_update_date, "%Y-%m-%d"
            ).date()

        # 计算距离今天的天数
        days_since_update = (date.today() - last_update_date).days

        # 判断是否消失
        is_disappeared = days_since_update >= threshold_days

        # 构建描述
        if is_disappeared:
            description = (
                f"Pipeline disappeared: Last seen {days_since_update} days ago "
                f"(threshold: {threshold_days} days)"
            )
        else:
            description = (
                f"Pipeline active: Last updated {days_since_update} days ago "
                f"(threshold: {threshold_days} days)"
            )

        return DisappearedPipelineEvent(
            pipeline_id=pipeline_id,
            drug_code=drug_code,
            company_name=company_name,
            last_phase=last_phase,
            last_seen_date=last_update_date,
            days_since_update=days_since_update,
            threshold_days=threshold_days,
            is_disappeared=is_disappeared,
            description=description,
        )

    def check_new_entry(
        self,
        pipeline_id: str,
        drug_code: str,
        company_name: str,
        phase: str,
        entry_date: Optional[date | str] = None,
        existing_pipelines: Optional[List[str]] = None,
    ) -> NewEntryEvent:
        """
        检测新进场管线

        Args:
            pipeline_id: 管线ID
            drug_code: 药物代码
            company_name: 公司名称
            phase: 当前阶段
            entry_date: 进场日期
            existing_pipelines: 现有管线ID列表

        Returns:
            NewEntryEvent 对象

        Example:
            >>> monitor = PipelineMonitor()
            >>> event = monitor.check_new_entry(
            ...     pipeline_id="123",
            ...     drug_code="SHR-1210",
            ...     company_name="Hengrui",
            ...     phase="Phase I",
            ...     existing_pipelines=["456", "789"]
            ... )
            >>> print(event.is_new)
            True
        """
        if entry_date is None:
            entry_date = date.today()
        elif isinstance(entry_date, str):
            entry_date = datetime.strptime(entry_date, "%Y-%m-%d").date()

        # 判断是否为新管线
        is_new = False
        if existing_pipelines is None:
            # 如果没有提供现有管线列表，假设为新管线
            is_new = True
        else:
            is_new = pipeline_id not in existing_pipelines

        # 构建描述
        if is_new:
            description = (
                f"New entry: {company_name} - {drug_code} "
                f"entered in {phase} on {entry_date.isoformat()}"
            )
        else:
            description = (
                f"Existing pipeline: {company_name} - {drug_code} "
                f"in {phase}"
            )

        return NewEntryEvent(
            pipeline_id=pipeline_id,
            drug_code=drug_code,
            company_name=company_name,
            phase=phase,
            entry_date=entry_date,
            is_new=is_new,
            description=description,
        )

    def check_regulatory_milestone(
        self,
        old_phase: str,
        new_phase: str,
        pipeline_id: str,
        drug_code: str,
        company_name: str,
        event_date: Optional[date | str] = None,
    ) -> Optional[PhaseChangeEvent]:
        """
        检测监管里程碑（NDA/BLA提交、批准等）

        Args:
            old_phase: 旧阶段
            new_phase: 新阶段
            pipeline_id: 管线ID
            drug_code: 药物代码
            company_name: 公司名称
            event_date: 事件日期

        Returns:
            PhaseChangeEvent 对象（如果不是里程碑则返回None）
        """
        # 标准化阶段
        old_standard = self.phase_mapper.map_to_standard(old_phase)
        new_standard = self.phase_mapper.map_to_standard(new_phase)

        # 检查是否为监管里程碑
        is_milestone = new_standard in [
            StandardPhase.FILING,
            StandardPhase.APPROVED,
        ]

        if not is_milestone:
            return None

        if event_date is None:
            event_date = date.today()
        elif isinstance(event_date, str):
            event_date = datetime.strptime(event_date, "%Y-%m-%d").date()

        # 构建描述
        if new_standard == StandardPhase.FILING:
            description = (
                f"Regulatory milestone: {drug_code} filed for marketing approval "
                f"({old_phase} → {new_phase})"
            )
        elif new_standard == StandardPhase.APPROVED:
            description = (
                f"Regulatory milestone: {drug_code} received marketing approval "
                f"({old_phase} → {new_phase})"
            )
        else:
            description = f"Regulatory milestone: {old_phase} → {new_phase}"

        return PhaseChangeEvent(
            pipeline_id=pipeline_id,
            drug_code=drug_code,
            company_name=company_name,
            old_phase=old_phase,
            new_phase=new_phase,
            change_type=ChangeType.REGULATORY_MILESTONE,
            event_date=event_date,
            description=description,
            phase_jump_level=0,
        )

    def analyze_pipeline_changes(
        self,
        old_pipelines: List[Dict[str, any]],
        new_pipelines: List[Dict[str, any]],
    ) -> List[PhaseChangeEvent | DisappearedPipelineEvent | NewEntryEvent]:
        """
        分析两次爬取之间的管线变化

        Args:
            old_pipelines: 旧管线列表（每个元素包含pipeline_id, phase, update_date等）
            new_pipelines: 新管线列表

        Returns:
            事件列表（PhaseChangeEvent, DisappearedPipelineEvent, NewEntryEvent）

        Example:
            >>> old_data = [
            ...     {"pipeline_id": "1", "drug_code": "SHR-1210", "phase": "Phase I"},
            ...     {"pipeline_id": "2", "drug_code": "SHR-1316", "phase": "Phase II"}
            ... ]
            >>> new_data = [
            ...     {"pipeline_id": "1", "drug_code": "SHR-1210", "phase": "Phase II"},
            ...     {"pipeline_id": "3", "drug_code": "SHR-1410", "phase": "Phase I"}
            ... ]
            >>> monitor = PipelineMonitor()
            >>> events = monitor.analyze_pipeline_changes(old_data, new_data)
            >>> for event in events:
            ...     print(event.description)
        """
        events = []

        # 构建管线字典
        old_dict = {p["pipeline_id"]: p for p in old_pipelines}
        new_dict = {p["pipeline_id"]: p for p in new_pipelines}

        # 检测Phase Jump和监管里程碑
        for pipeline_id, new_pipeline in new_dict.items():
            if pipeline_id in old_dict:
                # 管线已存在，检查Phase Jump
                old_pipeline = old_dict[pipeline_id]

                # 检查监管里程碑
                regulatory_event = self.check_regulatory_milestone(
                    old_phase=old_pipeline.get("phase", "Unknown"),
                    new_phase=new_pipeline.get("phase", "Unknown"),
                    pipeline_id=pipeline_id,
                    drug_code=new_pipeline.get("drug_code", ""),
                    company_name=new_pipeline.get("company_name", ""),
                )

                if regulatory_event:
                    events.append(regulatory_event)
                else:
                    # 检查普通Phase Jump
                    phase_event = self.check_phase_jump(
                        old_phase=old_pipeline.get("phase", "Unknown"),
                        new_phase=new_pipeline.get("phase", "Unknown"),
                        pipeline_id=pipeline_id,
                        drug_code=new_pipeline.get("drug_code", ""),
                        company_name=new_pipeline.get("company_name", ""),
                    )
                    if phase_event.change_type == ChangeType.PHASE_JUMP:
                        events.append(phase_event)
            else:
                # 新进场
                entry_event = self.check_new_entry(
                    pipeline_id=pipeline_id,
                    drug_code=new_pipeline.get("drug_code", ""),
                    company_name=new_pipeline.get("company_name", ""),
                    phase=new_pipeline.get("phase", "Unknown"),
                    existing_pipelines=list(old_dict.keys()),
                )
                if entry_event.is_new:
                    events.append(entry_event)

        # 检测消失管线
        for pipeline_id, old_pipeline in old_dict.items():
            if pipeline_id not in new_dict:
                # 管线消失
                disappeared_event = self.check_disappeared(
                    pipeline_id=pipeline_id,
                    drug_code=old_pipeline.get("drug_code", ""),
                    company_name=old_pipeline.get("company_name", ""),
                    last_phase=old_pipeline.get("phase", "Unknown"),
                    last_update_date=old_pipeline.get(
                        "update_date", date.today().isoformat()
                    ),
                )
                if disappeared_event.is_disappeared:
                    events.append(disappeared_event)

        return events

    def get_phase_jump_summary(
        self, events: List[PhaseChangeEvent]
    ) -> Dict[str, any]:
        """
        统计Phase Jump摘要

        Args:
            events: 事件列表

        Returns:
            摘要字典
        """
        summary = {
            "total_phase_jumps": 0,
            "phase_i_to_ii": 0,
            "phase_ii_to_iii": 0,
            "phase_iii_to_filing": 0,
            "filing_to_approved": 0,
            "companies": {},
        }

        for event in events:
            if (
                isinstance(event, PhaseChangeEvent)
                and event.change_type == ChangeType.PHASE_JUMP
            ):
                summary["total_phase_jumps"] += 1

                # 统计公司
                company = event.company_name
                summary["companies"][company] = (
                    summary["companies"].get(company, 0) + 1
                )

                # 统计跃迁类型
                if (
                    event.old_phase in ["Phase I", "Phase 1"]
                    and event.new_phase in ["Phase II", "Phase 2"]
                ):
                    summary["phase_i_to_ii"] += 1
                elif (
                    event.old_phase in ["Phase II", "Phase 2"]
                    and event.new_phase in ["Phase III", "Phase 3"]
                ):
                    summary["phase_ii_to_iii"] += 1
                elif (
                    "III" in event.old_phase or "3" in event.old_phase
                ) and "filing" in event.new_phase.lower():
                    summary["phase_iii_to_filing"] += 1
                elif "filing" in event.old_phase.lower() and (
                    "approved" in event.new_phase.lower()
                ):
                    summary["filing_to_approved"] += 1

        return summary


# =====================================================
# 便捷函数
# =====================================================

def detect_phase_jump(
    old_phase: str,
    new_phase: str,
    drug_code: str,
    company_name: str,
) -> Tuple[bool, int]:
    """
    便捷函数：检测是否为Phase Jump

    Args:
        old_phase: 旧阶段
        new_phase: 新阶段
        drug_code: 药物代码
        company_name: 公司名称

    Returns:
        (is_jump, jump_level) 元组

    Example:
        >>> is_jump, level = detect_phase_jump("Phase I", "Phase II", "SHR-1210", "Hengrui")
        >>> print(is_jump)
        True
        >>> print(level)
        1
    """
    monitor = PipelineMonitor()
    event = monitor.check_phase_jump(
        old_phase=old_phase,
        new_phase=new_phase,
        pipeline_id="",
        drug_code=drug_code,
        company_name=company_name,
    )
    return (event.change_type == ChangeType.PHASE_JUMP, event.phase_jump_level)


def check_disappeared_pipeline(
    last_update_date: date | str,
    threshold_days: int = 90,
) -> bool:
    """
    便捷函数：检查管线是否消失

    Args:
        last_update_date: 最后更新日期
        threshold_days: 阈值天数

    Returns:
        是否消失

    Example:
        >>> is_gone = check_disappeared_pipeline("2024-10-01", threshold_days=90)
        >>> print(is_gone)
        True
    """
    monitor = PipelineMonitor()
    event = monitor.check_disappeared(
        pipeline_id="",
        drug_code="",
        company_name="",
        last_phase="",
        last_update_date=last_update_date,
        threshold_days=threshold_days,
    )
    return event.is_disappeared


# =====================================================
# 导出
# =====================================================

__all__ = [
    "ChangeType",
    "PhaseChangeEvent",
    "DisappearedPipelineEvent",
    "NewEntryEvent",
    "PipelineMonitor",
    "detect_phase_jump",
    "check_disappeared_pipeline",
]
