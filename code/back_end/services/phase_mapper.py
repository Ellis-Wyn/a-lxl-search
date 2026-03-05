"""
=====================================================
Pipeline Phase 状态映射器
=====================================================

功能：
- 将各种 Phase 表示映射到统一标准
- 支持 Preclinical/Phase I/II/III/Approved 等阶段
- 识别中文/英文/缩写等各种表示
- 提供阶段顺序比较功能

使用示例：
    mapper = PhaseMapper()

    # 标准化阶段
    phase = mapper.normalize("Phase II")
    # -> "Phase 2"

    # 比较阶段
    if mapper.is_later_phase("Phase 3", "Phase 2"):
        print("Phase 3 is later")
=====================================================
"""

from typing import Optional, Dict, List, Set
from enum import Enum
from core.logger import get_logger

logger = get_logger(__name__)


# 标准阶段枚举
class StandardPhase(Enum):
    """标准研发阶段"""
    DISCOVERY = "Discovery"           # 发现阶段
    PRECLINICAL = "Preclinical"       # 临床前
    PHASE_1 = "Phase 1"              # 一期临床
    PHASE_1_2 = "Phase 1/2"          # 一/二期临床
    PHASE_2 = "Phase 2"              # 二期临床
    PHASE_2_3 = "Phase 2/3"          # 二/三期临床
    PHASE_3 = "Phase 3"              # 三期临床
    REGISTRATION = "Registration"     # 注册申报
    APPROVED = "Approved"            # 已批准
    LAUNCHED = "Launched"            # 已上市
    DISCONTINUED = "Discontinued"    # 已终止
    UNKNOWN = "Unknown"              # 未知


# 阶段顺序（数字越大，阶段越靠后）
PHASE_ORDER = {
    StandardPhase.DISCOVERY: 0,
    StandardPhase.PRECLINICAL: 1,
    StandardPhase.PHASE_1: 2,
    StandardPhase.PHASE_1_2: 3,
    StandardPhase.PHASE_2: 4,
    StandardPhase.PHASE_2_3: 5,
    StandardPhase.PHASE_3: 6,
    StandardPhase.REGISTRATION: 7,
    StandardPhase.APPROVED: 8,
    StandardPhase.LAUNCHED: 9,
    StandardPhase.DISCONTINUED: -1,  # 特殊处理
    StandardPhase.UNKNOWN: -2,
}


# 各种 Phase 表示到标准阶段的映射
PHASE_MAPPING = {
    # ===== Phase 1 =====
    "Phase I": StandardPhase.PHASE_1,
    "Phase 1": StandardPhase.PHASE_1,
    "Phase I trial": StandardPhase.PHASE_1,
    "Phase 1 trial": StandardPhase.PHASE_1,
    "I期": StandardPhase.PHASE_1,
    "I期临床": StandardPhase.PHASE_1,
    "一期": StandardPhase.PHASE_1,
    "一期临床": StandardPhase.PHASE_1,
    "Ⅰ期": StandardPhase.PHASE_1,  # 罗马数字
    "Ⅰ期临床": StandardPhase.PHASE_1,  # 罗马数字
    "Phase I/II": StandardPhase.PHASE_1_2,
    "Phase 1/2": StandardPhase.PHASE_1_2,
    "I/II期": StandardPhase.PHASE_1_2,
    "一/二期": StandardPhase.PHASE_1_2,

    # ===== Phase 2 =====
    "Phase II": StandardPhase.PHASE_2,
    "Phase 2": StandardPhase.PHASE_2,
    "Phase II trial": StandardPhase.PHASE_2,
    "Phase 2 trial": StandardPhase.PHASE_2,
    "II期": StandardPhase.PHASE_2,
    "II期临床": StandardPhase.PHASE_2,
    "二期": StandardPhase.PHASE_2,
    "二期临床": StandardPhase.PHASE_2,
    "Ⅱ期": StandardPhase.PHASE_2,  # 罗马数字
    "Ⅱ期临床": StandardPhase.PHASE_2,  # 罗马数字
    "Phase II/III": StandardPhase.PHASE_2_3,
    "Phase 2/3": StandardPhase.PHASE_2_3,
    "II/III期": StandardPhase.PHASE_2_3,
    "二/三期": StandardPhase.PHASE_2_3,

    # ===== Phase 3 =====
    "Phase III": StandardPhase.PHASE_3,
    "Phase 3": StandardPhase.PHASE_3,
    "Phase III trial": StandardPhase.PHASE_3,
    "Phase 3 trial": StandardPhase.PHASE_3,
    "III期": StandardPhase.PHASE_3,
    "III期临床": StandardPhase.PHASE_3,
    "三期": StandardPhase.PHASE_3,
    "三期临床": StandardPhase.PHASE_3,
    "Ⅲ期": StandardPhase.PHASE_3,  # 罗马数字
    "Ⅲ期临床": StandardPhase.PHASE_3,  # 罗马数字

    # ===== Preclinical =====
    "Preclinical": StandardPhase.PRECLINICAL,
    "Pre-clinical": StandardPhase.PRECLINICAL,
    "Pre-IND": StandardPhase.PRECLINICAL,
    "临床前": StandardPhase.PRECLINICAL,
    "临床前研究": StandardPhase.PRECLINICAL,
    "Discovery": StandardPhase.DISCOVERY,
    "发现阶段": StandardPhase.DISCOVERY,
    "研究阶段": StandardPhase.DISCOVERY,

    # ===== Registration/Approved =====
    "NDA": StandardPhase.REGISTRATION,
    "BLA": StandardPhase.REGISTRATION,
    "MAA": StandardPhase.REGISTRATION,
    "Registration": StandardPhase.REGISTRATION,
    "注册申报": StandardPhase.REGISTRATION,
    "上市申请": StandardPhase.REGISTRATION,
    "Approved": StandardPhase.APPROVED,
    "EUA": StandardPhase.APPROVED,  # Emergency Use Authorization
    "已批准": StandardPhase.APPROVED,
    "获批": StandardPhase.APPROVED,
    "Launched": StandardPhase.LAUNCHED,
    "Marketed": StandardPhase.LAUNCHED,
    "已上市": StandardPhase.LAUNCHED,
    "上市": StandardPhase.LAUNCHED,

    # ===== Discontinued =====
    "Discontinued": StandardPhase.DISCONTINUED,
    "Terminated": StandardPhase.DISCONTINUED,
    "Withdrawn": StandardPhase.DISCONTINUED,
    "Suspended": StandardPhase.DISCONTINUED,
    "已终止": StandardPhase.DISCONTINUED,
    "终止": StandardPhase.DISCONTINUED,
    "暂停": StandardPhase.DISCONTINUED,
    "已退场": StandardPhase.DISCONTINUED,
}


class PhaseMapper:
    """
    Phase 状态映射器

    核心功能：
    1. normalize(): 标准化阶段字符串
    2. get_order(): 获取阶段顺序值
    3. is_later_phase(): 比较阶段顺序
    4. get_phase_group(): 获取阶段分组
    """

    def __init__(self):
        """初始化映射器"""
        self.mapping = PHASE_MAPPING
        self.phase_order = PHASE_ORDER

        # 构建反向映射（小写，用于模糊匹配）
        self._lower_mapping: Dict[str, StandardPhase] = {}
        for key, value in self.mapping.items():
            self._lower_mapping[key.lower()] = value

        logger.info(
            "PhaseMapper initialized",
            extra={
                "mapping_count": len(self.mapping),
            }
        )

    def normalize(self, phase_str: Optional[str]) -> str:
        """
        标准化阶段字符串

        Args:
            phase_str: 原始阶段字符串

        Returns:
            标准化的阶段名称

        Examples:
            >>> mapper = PhaseMapper()
            >>> mapper.normalize("Phase II")
            'Phase 2'
            >>> mapper.normalize("二期临床")
            'Phase 2'
        """
        if not phase_str:
            return StandardPhase.UNKNOWN.value

        # 去除首尾空格
        phase_str = phase_str.strip()

        # 精确匹配
        if phase_str in self.mapping:
            return self.mapping[phase_str].value

        # 模糊匹配（小写）
        phase_lower = phase_str.lower()
        if phase_lower in self._lower_mapping:
            return self._lower_mapping[phase_lower].value

        # 关键词匹配
        for key, standard_phase in self.mapping.items():
            if key.lower() in phase_lower or phase_lower in key.lower():
                return standard_phase.value

        # 无法识别，记录日志并返回 Unknown
        logger.debug(
            f"Unknown phase: {phase_str}",
            extra={"phase_str": phase_str}
        )

        return StandardPhase.UNKNOWN.value

    def get_order(self, phase_str: Optional[str]) -> int:
        """
        获取阶段顺序值

        Args:
            phase_str: 阶段字符串

        Returns:
            顺序值（数字越大越靠后）
        """
        normalized = self.normalize(phase_str)

        for phase_enum, order in self.phase_order.items():
            if phase_enum.value == normalized:
                return order

        return self.phase_order[StandardPhase.UNKNOWN]

    def is_later_phase(
        self,
        phase1: str,
        phase2: str,
        allow_equal: bool = False,
    ) -> bool:
        """
        判断 phase1 是否比 phase2 更靠后

        Args:
            phase1: 阶段1
            phase2: 阶段2
            allow_equal: 是否认为相等也算更靠后

        Returns:
            True if phase1 >= phase2 (with allow_equal)

        Examples:
            >>> mapper = PhaseMapper()
            >>> mapper.is_later_phase("Phase 3", "Phase 2")
            True
            >>> mapper.is_later_phase("Phase 2", "Phase 3")
            False
        """
        order1 = self.get_order(phase1)
        order2 = self.get_order(phase2)

        if allow_equal:
            return order1 >= order2
        else:
            return order1 > order2

    def get_phase_group(self, phase_str: Optional[str]) -> str:
        """
        获取阶段分组

        分组规则：
        - early: Discovery + Preclinical + Phase 1
        - mid: Phase 1/2 + Phase 2 + Phase 2/3
        - late: Phase 3 + Registration
        - approved: Approved + Launched
        - terminated: Discontinued

        Args:
            phase_str: 阶段字符串

        Returns:
            分组名称
        """
        normalized = self.normalize(phase_str)

        phase_groups = {
            # Early stages
            StandardPhase.DISCOVERY.value: "early",
            StandardPhase.PRECLINICAL.value: "early",
            StandardPhase.PHASE_1.value: "early",

            # Mid stages
            StandardPhase.PHASE_1_2.value: "mid",
            StandardPhase.PHASE_2.value: "mid",
            StandardPhase.PHASE_2_3.value: "mid",

            # Late stages
            StandardPhase.PHASE_3.value: "late",
            StandardPhase.REGISTRATION.value: "late",

            # Approved
            StandardPhase.APPROVED.value: "approved",
            StandardPhase.LAUNCHED.value: "approved",

            # Terminated
            StandardPhase.DISCONTINUED.value: "terminated",
            StandardPhase.UNKNOWN.value: "unknown",
        }

        return phase_groups.get(normalized, "unknown")

    def get_phase_confidence(self, phase_str: Optional[str]) -> float:
        """
        获取阶段识别置信度

        置信度规则：
        - 1.0: 精确匹配
        - 0.8: 标准变体（如 Phase I vs Phase 1）
        - 0.6: 关键词匹配
        - 0.0: 无法识别

        Args:
            phase_str: 阶段字符串

        Returns:
            置信度（0-1）
        """
        if not phase_str:
            return 0.0

        phase_str = phase_str.strip()

        # 精确匹配
        if phase_str in self.mapping:
            return 1.0

        # 标准变体（忽略大小写）
        if phase_str.lower() in self._lower_mapping:
            return 0.8

        # 关键词匹配
        for key in self.mapping.keys():
            if key.lower() in phase_str.lower() or phase_str.lower() in key.lower():
                return 0.6

        return 0.0

    def get_similar_phases(self, phase_str: Optional[str], limit: int = 5) -> List[str]:
        """
        获取相似的标准阶段（用于错误提示）

        Args:
            phase_str: 原始阶段字符串
            limit: 返回数量限制

        Returns:
            相似的标准阶段列表
        """
        if not phase_str:
            return []

        similar = []
        phase_lower = phase_str.lower()

        for standard_phase in StandardPhase:
            # 跳过 Unknown
            if standard_phase == StandardPhase.UNKNOWN:
                continue

            # 计算相似度（简单字符串包含）
            if standard_phase.value.lower() in phase_lower or phase_lower in standard_phase.value.lower():
                similar.append(standard_phase.value)

        return similar[:limit]


# 单例实例
_default_mapper: Optional[PhaseMapper] = None


def get_phase_mapper() -> PhaseMapper:
    """
    获取 PhaseMapper 单例

    Returns:
        PhaseMapper 实例
    """
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = PhaseMapper()
    return _default_mapper


__all__ = [
    "PhaseMapper",
    "StandardPhase",
    "get_phase_mapper",
]
