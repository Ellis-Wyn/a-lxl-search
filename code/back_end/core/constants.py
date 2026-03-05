"""
=====================================================
项目常量定义
=====================================================

定义项目中使用的常量，避免硬编码，提高可维护性。

使用方式：
    from core.constants import (
        Phase,
        Modality,
        RelationType,
        DEFAULT_LIMIT,
        MAX_LIMIT
    )
=====================================================
"""

from enum import Enum
from typing import List

# =====================================================
# 通用常量
# =====================================================

DEFAULT_LIMIT: int = 50  # 默认分页大小
MAX_LIMIT: int = 200     # 最大分页大小
MIN_LIMIT: int = 1       # 最小分页大小

DEFAULT_OFFSET: int = 0   # 默认偏移量

# =====================================================
# Phase 阶段常量
# =====================================================

class Phase(str, Enum):
    """标准化的阶段名称"""
    PRECLINICAL = "Preclinical"
    PHASE_1 = "Phase 1"
    PHASE_1_2 = "Phase 1/2"
    PHASE_2 = "Phase 2"
    PHASE_2_3 = "Phase 2/3"
    PHASE_3 = "Phase 3"
    APPROVED = "Approved"
    DISCONTINUED = "Discontinued"
    UNKNOWN = "Unknown"

    @classmethod
    def all_phases(cls) -> List[str]:
        """获取所有阶段列表"""
        return [phase.value for phase in cls]

    @classmethod
    def clinical_phases(cls) -> List[str]:
        """获取临床阶段列表"""
        return [
            cls.PHASE_1.value,
            cls.PHASE_1_2.value,
            cls.PHASE_2.value,
            cls.PHASE_2_3.value,
            cls.PHASE_3.value,
        ]


# =====================================================
# Modality 药物类型常量
# =====================================================

class Modality(str, Enum):
    """药物类型（Modality）"""
    SMALL_MOLECULE = "小分子"
    MONOCLONAL_ANTIBODY = "单抗"
    ADC = "ADC"
    BISPECIFIC_ANTIBODY = "双抗"
    CAR_T = "CAR-T"
    VACCINE = "疫苗"
    GENE_THERAPY = "基因治疗"
    CELL_THERAPY = "细胞治疗"
    RNA_THERAPY = "RNA治疗"
    PEPTIDE = "多肽"
    OTHER = "其他"

    @classmethod
    def all_modalities(cls) -> List[str]:
        """获取所有药物类型列表"""
        return [modality.value for modality in cls]


# =====================================================
# RelationType 关系类型常量
# =====================================================

class RelationType(str, Enum):
    """靶点与文献/管线的关系类型"""
    MENTIONS = "mentions"           # 提及
    REPORTS = "reports"             # 报道
    ANALYZES = "analyzes"           # 分析
    TARGETS = "targets"             # 靶向
    INHIBITS = "inhibits"           # 抑制
    ACTIVATES = "activates"         # 激活
    MODULATES = "modulates"         # 调节
    BINDS = "binds"                 # 结合

    @classmethod
    def target_publication_relations(cls) -> List[str]:
        """靶点-文献关系类型"""
        return [
            cls.MENTIONS.value,
            cls.REPORTS.value,
            cls.ANALYZES.value,
        ]

    @classmethod
    def target_pipeline_relations(cls) -> List[str]:
        """靶点-管线关系类型"""
        return [
            cls.TARGETS.value,
            cls.INHIBITS.value,
            cls.ACTIVATES.value,
            cls.MODULATES.value,
            cls.BINDS.value,
        ]


# =====================================================
# PublicationType 文献类型常量
# =====================================================

class PublicationType(str, Enum):
    """文献类型"""
    CLINICAL_TRIAL = "Clinical Trial"
    CLINICAL_TRIAL_PHASE_I = "Clinical Trial, Phase I"
    CLINICAL_TRIAL_PHASE_II = "Clinical Trial, Phase II"
    CLINICAL_TRIAL_PHASE_III = "Clinical Trial, Phase III"
    CLINICAL_TRIAL_PHASE_1_2 = "Clinical Trial, Phase 1/2"
    CLINICAL_TRIAL_PHASE_2_3 = "Clinical Trial, Phase 2/3"
    REVIEW = "Review"
    META_ANALYSIS = "Meta-Analysis"
    RESEARCH_SUPPORT = "Research Support, U.S. Gov't"
    JOURNAL_ARTICLE = "Journal Article"
    LETTER = "Letter"
    EDITORIAL = "Editorial"
    NEWS = "News"


# =====================================================
# SourceType 来源类型常量
# =====================================================

class SourceType(str, Enum):
    """文献来源类型"""
    PUBMED = "pubmed"
    ASCO = "asco"
    AACR = "aacr"
    ESMO = "esmo"
    NEJM = "nejm"
    LANCET = "lancet"
    JCO = "jco"
    COMPANY_WEBSITE = "company_website"
    CDE = "cde"
    CTR = "ctr"


# =====================================================
# HTTP 状态码常量
# =====================================================

class HTTPStatus:
    """HTTP 状态码"""
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500


# =====================================================
# 错误消息常量
# =====================================================

class ErrorMessage:
    """错误消息"""
    TARGET_NOT_FOUND = "Target not found"
    PUBLICATION_NOT_FOUND = "Publication not found"
    PIPELINE_NOT_FOUND = "Pipeline not found"
    INVALID_UUID_FORMAT = "Invalid UUID format"
    INVALID_DATE_FORMAT = "Invalid date format, expected YYYY-MM-DD"
    DATABASE_ERROR = "Database operation failed"
    VALIDATION_ERROR = "Validation failed"


# =====================================================
# API 文档常量
# =====================================================

class APIDescription:
    """API 文档描述"""
    TARGET_LIST = "获取靶点列表，支持搜索、过滤和分页"
    TARGET_DETAIL = "获取靶点详细信息"
    TARGET_STATS = "获取靶点统计信息"
    PUBLICATION_LIST = "获取文献列表，支持搜索、过滤和分页"
    PUBLICATION_DETAIL = "获取文献详细信息"
    PIPELINE_LIST = "获取管线列表，支持搜索、过滤和分页"
    PIPELINE_STATS = "获取管线统计信息"


# =====================================================
# 导出所有常量
# =====================================================

__all__ = [
    # 通用
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "MIN_LIMIT",
    "DEFAULT_OFFSET",
    # 枚举类
    "Phase",
    "Modality",
    "RelationType",
    "PublicationType",
    "SourceType",
    # 其他
    "HTTPStatus",
    "ErrorMessage",
    "APIDescription",
]
