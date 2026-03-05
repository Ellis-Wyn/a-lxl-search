"""
=====================================================
Core Intelligence Engine - 核心智能引擎
=====================================================

统一的核心业务逻辑模块，提供：
- 查询扩展（QueryExpander）
- 评分算法（ScoringEngine）
- 临床数据分析（ClinicalAnalyzer）
- Phase标准化（PhaseNormalizer）
- MoA识别（MoAClassifier）
- 管线解析（PipelineParser）
- 数据验证（DataValidator）

使用示例：
    from core.intelligence import QueryExpander, ScoringEngine

    expander = QueryExpander()
    expanded = expander.expand("EGFR")

    scorer = ScoringEngine()
    score = scorer.calculate_publication_score(...)

作者：A_lxl_search Team
创建日期：2026-02-02
=====================================================
"""

# 导入所有核心模块
from .query_expander import QueryExpander
from .scoring_engine import ScoringEngine
from .clinical_analyzer import ClinicalAnalyzer
from .phase_normalizer import PhaseNormalizer
from .moa_classifier import MoAClassifier
from .pipeline_parser import PipelineParser
from .data_validator import DataValidator

__all__ = [
    "QueryExpander",
    "ScoringEngine",
    "ClinicalAnalyzer",
    "PhaseNormalizer",
    "MoAClassifier",
    "PipelineParser",
    "DataValidator",
]
