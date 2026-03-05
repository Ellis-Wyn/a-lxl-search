"""
=====================================================
Pipeline 变化检测器（增量监控）
=====================================================

功能：
- 检测管线状态变化（新增/修改/消失）
- Phase Jump 预警（检测阶段升级）
- 批量更新 last_seen_at 时间戳
- 生成变化报告

使用示例：
    monitor = PipelineMonitor()

    # 检测变化
    report = await monitor.detect_changes(
        old_pipelines=[...],
        new_pipelines=[...]
    )

    # 处理变化
    for jump in report.phase_jumps:
        print(f"Phase Jump: {jump['drug_code']} {jump['old_phase']} -> {jump['new_phase']}")
=====================================================
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum

from services.phase_mapper import PhaseMapper, get_phase_mapper
from core.logger import get_logger

logger = get_logger(__name__)


class ChangeType(Enum):
    """变化类型"""
    NEW = "new"                    # 新增管线
    PHASE_JUMP = "phase_jump"     # 阶段升级
    DISAPPEARED = "disappeared"    # 管线消失（可能终止）
    REAPPEARED = "reappeared"     # 消失后重新出现
    INFO_UPDATE = "info_update"    # 信息更新（phase 未变）


@dataclass
class PhaseJump:
    """Phase Jump 事件"""
    pipeline_id: int
    drug_code: str
    company_name: str
    indication: str
    old_phase: str
    new_phase: str
    jump_days: int  # 距离上次更新的天数
    confidence: float  # 置信度（0-1）
    detected_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "pipeline_id": self.pipeline_id,
            "drug_code": self.drug_code,
            "company_name": self.company_name,
            "indication": self.indication,
            "old_phase": self.old_phase,
            "new_phase": self.new_phase,
            "jump_days": self.jump_days,
            "confidence": self.confidence,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class PipelineChange:
    """管线变化"""
    change_type: ChangeType
    pipeline: Dict[str, Any]
    previous: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ChangeReport:
    """变化报告"""
    total_changes: int
    new_pipelines: List[Dict[str, Any]]
    phase_jumps: List[PhaseJump]
    disappeared_pipelines: List[Dict[str, Any]]
    reappeared_pipelines: List[Dict[str, Any]]
    info_updates: int
    scan_date: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total_changes": self.total_changes,
            "new_pipelines": self.new_pipelines,
            "phase_jumps": [j.to_dict() for j in self.phase_jumps],
            "disappeared_pipelines": self.disappeared_pipelines,
            "reappeared_pipelines": self.reappeared_pipelines,
            "info_updates": self.info_updates,
            "scan_date": self.scan_date.isoformat(),
        }

    def has_significant_changes(self) -> bool:
        """是否有显著变化"""
        return (
            len(self.new_pipelines) > 0
            or len(self.phase_jumps) > 0
            or len(self.disappeared_pipelines) > 0
        )


class PipelineMonitor:
    """
    Pipeline 变化检测器

    核心功能：
    1. detect_changes(): 检测新旧数据的差异
    2. detect_phase_jumps(): 检测 Phase Jump
    3. detect_disappeared(): 检测消失的管线
    4. generate_report(): 生成变化报告
    """

    def __init__(self, phase_mapper: Optional[PhaseMapper] = None):
        """
        初始化检测器

        Args:
            phase_mapper: Phase 映射器（可选，默认使用单例）
        """
        self.phase_mapper = phase_mapper or get_phase_mapper()
        logger.info("PipelineMonitor initialized")

    def detect_changes(
        self,
        old_pipelines: List[Dict[str, Any]],
        new_pipelines: List[Dict[str, Any]],
        disappeared_threshold_days: int = 180,
    ) -> ChangeReport:
        """
        检测管线变化

        Args:
            old_pipelines: 旧管线数据（从数据库读取）
            new_pipelines: 新管线数据（爬虫获取）
            disappeared_threshold_days: 消失判定阈值（天）

        Returns:
            变化报告
        """
        logger.info(
            "Detecting pipeline changes",
            extra={
                "old_count": len(old_pipelines),
                "new_count": len(new_pipelines),
            }
        )

        # 构建唯一键映射
        old_map = self._build_pipeline_map(old_pipelines)
        new_map = self._build_pipeline_map(new_pipelines)

        # 检测各种变化
        new_items = self._detect_new(old_map, new_map)
        phase_jumps = self._detect_phase_jumps(old_map, new_map)
        disappeared = self._detect_disappeared(
            old_map,
            new_map,
            threshold_days=disappeared_threshold_days,
        )
        reappeared = self._detect_reappeared(old_map, new_map)
        info_updates = self._count_info_updates(old_map, new_map)

        # 生成报告
        report = ChangeReport(
            total_changes=len(new_items) + len(phase_jumps) + len(disappeared) + len(reappeared) + info_updates,
            new_pipelines=new_items,
            phase_jumps=phase_jumps,
            disappeared_pipelines=disappeared,
            reappeared_pipelines=reappeared,
            info_updates=info_updates,
        )

        logger.info(
            "Change detection completed",
            extra={
                "total_changes": report.total_changes,
                "new": len(new_items),
                "phase_jumps": len(phase_jumps),
                "disappeared": len(disappeared),
                "reappeared": len(reappeared),
                "info_updates": info_updates,
            }
        )

        return report

    def _build_pipeline_map(self, pipelines: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        构建管线映射（用唯一键作为索引）

        唯一键：(drug_code, company_name, indication)
        """
        pipeline_map = {}

        for pipeline in pipelines:
            unique_key = self._get_unique_key(pipeline)
            pipeline_map[unique_key] = pipeline

        return pipeline_map

    def _get_unique_key(self, pipeline: Dict[str, Any]) -> str:
        """
        获取管线唯一键

        Args:
            pipeline: 管线数据

        Returns:
            唯一键字符串
        """
        drug_code = pipeline.get("drug_code", "")
        company_name = pipeline.get("company_name", "")
        indication = pipeline.get("indication", "")

        return f"{drug_code}|{company_name}|{indication}"

    def _detect_new(
        self,
        old_map: Dict[str, Dict[str, Any]],
        new_map: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """检测新增管线"""
        new_items = []

        for key, pipeline in new_map.items():
            if key not in old_map:
                new_items.append(pipeline)

        return new_items

    def _detect_phase_jumps(
        self,
        old_map: Dict[str, Dict[str, Any]],
        new_map: Dict[str, Dict[str, Any]],
    ) -> List[PhaseJump]:
        """检测 Phase Jump"""
        jumps = []

        for key, new_pipeline in new_map.items():
            if key not in old_map:
                continue

            old_pipeline = old_map[key]

            # 获取阶段
            old_phase = old_pipeline.get("phase", "")
            new_phase = new_pipeline.get("phase", "")

            # 标准化阶段
            old_phase_normalized = self.phase_mapper.normalize(old_phase)
            new_phase_normalized = self.phase_mapper.normalize(new_phase)

            # 检查是否升级
            if self.phase_mapper.is_later_phase(new_phase_normalized, old_phase_normalized):
                # 计算距离上次更新的天数
                jump_days = self._calculate_days_since(old_pipeline)

                # 获取置信度
                confidence = self.phase_mapper.get_phase_confidence(new_phase)

                jump = PhaseJump(
                    pipeline_id=new_pipeline.get("pipeline_id", 0),
                    drug_code=new_pipeline.get("drug_code", ""),
                    company_name=new_pipeline.get("company_name", ""),
                    indication=new_pipeline.get("indication", ""),
                    old_phase=old_phase_normalized,
                    new_phase=new_phase_normalized,
                    jump_days=jump_days,
                    confidence=confidence,
                )

                jumps.append(jump)

                logger.info(
                    "Phase Jump detected",
                    extra={
                        "drug_code": jump.drug_code,
                        "company": jump.company_name,
                        "old_phase": jump.old_phase,
                        "new_phase": jump.new_phase,
                        "days": jump_days,
                    }
                )

        return jumps

    def _detect_disappeared(
        self,
        old_map: Dict[str, Dict[str, Any]],
        new_map: Dict[str, Dict[str, Any]],
        threshold_days: int = 180,
    ) -> List[Dict[str, Any]]:
        """
        检测消失的管线

        规则：
        - 在 old 中存在但 new 中不存在
        - last_seen_at 距今超过 threshold_days
        """
        disappeared = []

        for key, pipeline in old_map.items():
            if key not in new_map:
                # 检查是否超过阈值
                days_since = self._calculate_days_since(pipeline)

                if days_since >= threshold_days:
                    disappeared.append(pipeline)

                    logger.warning(
                        "Pipeline disappeared",
                        extra={
                            "drug_code": pipeline.get("drug_code"),
                            "company": pipeline.get("company_name"),
                            "days_since": days_since,
                        }
                    )

        return disappeared

    def _detect_reappeared(
        self,
        old_map: Dict[str, Dict[str, Any]],
        new_map: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        检测重新出现的管线

        规则：
        - 之前标记为 disappeared
        - 现在又出现了
        """
        # TODO: 需要结合数据库状态实现
        # 当前简化版：暂时不实现
        return []

    def _count_info_updates(
        self,
        old_map: Dict[str, Dict[str, Any]],
        new_map: Dict[str, Dict[str, Any]],
    ) -> int:
        """统计信息更新（Phase 未变但其他信息变化）"""
        count = 0

        for key, new_pipeline in new_map.items():
            if key not in old_map:
                continue

            old_pipeline = old_map[key]

            # 比较阶段
            old_phase = self.phase_mapper.normalize(old_pipeline.get("phase", ""))
            new_phase = self.phase_mapper.normalize(new_pipeline.get("phase", ""))

            # 如果阶段相同，检查其他字段
            if old_phase == new_phase:
                # 简化处理：认为都算更新
                count += 1

        return count

    def _calculate_days_since(self, pipeline: Dict[str, Any]) -> int:
        """
        计算距离上次更新的天数

        Args:
            pipeline: 管线数据

        Returns:
            天数
        """
        last_seen = pipeline.get("last_seen_at")

        if last_seen:
            if isinstance(last_seen, str):
                try:
                    last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                except ValueError:
                    pass
            elif isinstance(last_seen, datetime):
                pass
            else:
                return 999999

            if isinstance(last_seen, datetime):
                delta = datetime.utcnow() - last_seen
                return delta.days

        # 如果没有 last_seen_at，使用 first_seen_at
        first_seen = pipeline.get("first_seen_at")
        if first_seen:
            if isinstance(first_seen, str):
                try:
                    first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
                except ValueError:
                    pass
            elif isinstance(first_seen, datetime):
                pass

            if isinstance(first_seen, datetime):
                delta = datetime.utcnow() - first_seen
                return delta.days

        return 999999


# 单例实例
_default_monitor: Optional[PipelineMonitor] = None


def get_pipeline_monitor() -> PipelineMonitor:
    """
    获取 PipelineMonitor 单例

    Returns:
        PipelineMonitor 实例
    """
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = PipelineMonitor()
    return _default_monitor


__all__ = [
    "PipelineMonitor",
    "ChangeType",
    "PhaseJump",
    "PipelineChange",
    "ChangeReport",
    "get_pipeline_monitor",
]
