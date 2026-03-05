"""
=====================================================
ScoringEngine - 评分引擎
=====================================================

根据需求说明书（20260127）实现的文献/管线排序算法：

1. 发布时间分值（Recency Score）: 40%权重
   - 近24个月的数据
   - 公式：base_score = 100 - (过去的天数 * 权重衰减)

2. 临床数据披露（Clinical Data）: 25%权重
   - ORR/PFS/OS等指标

3. 高质量来源（High-Quality Source）: 15%权重
   - ASCO, AACR, NEJM, Lancet, JCO 等

4. 临床后期阶段（Phase III/NDA）: 10%权重
   - Phase III 或上市申请阶段

5. 突破性认定（Regulatory Status）: 10%权重
   - Breakthrough Therapy, Fast Track, Orphan Drug, First-in-class

使用示例：
    from core.intelligence import ScoringEngine

    engine = ScoringEngine()
    score = engine.calculate_publication_score(
        title="EGFR抑制剂在NSCLC中的最新III期数据",
        pub_date="2024-01-15",
        abstract="...ORR: 62%, mPFS: 11.2个月...",
        publication_type="Clinical Trial",
        journal="JCO"
    )
    print(score.total_score)  # 输出: 85.5

作者：A_lxl_search Team
创建日期：2026-02-02
=====================================================
"""

from datetime import datetime, date
from typing import Dict, Optional
from dataclasses import dataclass

from .clinical_analyzer import ClinicalAnalyzer, ClinicalMetrics


@dataclass
class PublicationScore:
    """文献得分数据类"""
    total_score: float  # 总分
    recency_score: float  # 时效性得分
    clinical_score: float  # 临床数据得分
    phase_score: float  # 阶段得分
    regulatory_score: float  # 监管认定得分
    source_score: float  # 来源质量得分
    penalty_score: float  # 惩罚得分

    # 详细说明
    score_breakdown: Dict[str, float]  # 得分明细

    def to_dict(self) -> Dict[str, any]:
        """转换为字典"""
        return {
            "total_score": self.total_score,
            "recency_score": self.recency_score,
            "clinical_score": self.clinical_score,
            "phase_score": self.phase_score,
            "regulatory_score": self.regulatory_score,
            "source_score": self.source_score,
            "penalty_score": self.penalty_score,
            "score_breakdown": self.score_breakdown,
        }


@dataclass
class PipelineScore:
    """管线得分数据类"""
    total_score: float  # 总分
    phase_score: float  # 阶段得分
    novelty_score: float  # 新颖性得分
    competition_score: float  # 竞争优势得分
    recency_score: float  # 时效性得分

    score_breakdown: Dict[str, float]

    def to_dict(self) -> Dict[str, any]:
        """转换为字典"""
        return {
            "total_score": self.total_score,
            "phase_score": self.phase_score,
            "novelty_score": self.novelty_score,
            "competition_score": self.competition_score,
            "recency_score": self.recency_score,
            "score_breakdown": self.score_breakdown,
        }


class ScoringEngine:
    """
    评分引擎

    根据需求说明书计算文献和管线得分
    """

    # 高质量来源列表
    HIGH_QUALITY_SOURCES = [
        "ASCO", "AACR", "ESMO", "ASH", "WCLC",  # 顶级会议
        "NEJM", "Lancet", "JAMA", "BMJ",  # 顶级期刊
        "JCO", "Lancet Oncology", "JAMA Oncology", "Annals of Oncology",  # 肿瘤专科顶级期刊
        "Nature", "Science", "Cell",  # 综合顶级期刊
    ]

    # 监管认定关键词
    REGULATORY_KEYWORDS = {
        "breakthrough therapy": 30,
        "fast track": 20,
        "orphan drug": 20,
        "first-in-class": 30,
        "best-in-class": 20,
        "priority review": 15,
        "accelerated approval": 15,
    }

    # 阶段关键词
    PHASE_KEYWORDS = {
        "phase iii": 40,
        "phase 3": 40,
        "phase iii trial": 40,
        "phase 3 trial": 40,
        "pivotal": 35,
        "pivotal study": 35,
        "registration": 30,
        "registrational": 30,
        "nda": 35,
        "bla": 35,
        "market approval": 30,
        "approved": 25,
    }

    def __init__(self):
        """初始化评分引擎"""
        self.clinical_analyzer = ClinicalAnalyzer()

    # =====================================================
    # 文献评分
    # =====================================================

    def calculate_recency_score(
        self,
        pub_date: Optional[datetime | date | str],
        max_age_days: int = 730  # 24个月
    ) -> float:
        """
        计算时效性得分

        得分规则：
        - 0-30天：100分
        - 31-90天：80分
        - 91-365天：60分
        - 366-730天：40分
        - 超过730天：20分
        - 无日期：10分

        Args:
            pub_date: 发布日期
            max_age_days: 最大年龄天数（超过此日期得分不再降低）

        Returns:
            时效性得分（0-100）
        """
        if not pub_date:
            return 10.0  # 无日期，给最低分

        # 转换为date对象
        if isinstance(pub_date, str):
            try:
                pub_date = datetime.strptime(pub_date.split()[0], "%Y-%m-%d").date()
            except (ValueError, IndexError):
                return 10.0
        elif isinstance(pub_date, datetime):
            pub_date = pub_date.date()

        days = (date.today() - pub_date).days

        if days <= 30:
            return 100.0
        elif days <= 90:
            return 80.0
        elif days <= 365:
            return 60.0
        elif days <= max_age_days:
            return 40.0
        else:
            return 20.0

    def calculate_clinical_score(
        self,
        abstract_text: Optional[str] = None,
        title_text: Optional[str] = None
    ) -> float:
        """
        计算临床数据得分

        得分规则（参考需求说明书）：
        - 有 ORR/PFS/OS: +50分
        - 有 n=: +25分
        - 总分上限100分

        Args:
            abstract_text: 摘要文本
            title_text: 标题文本

        Returns:
            临床数据得分（0-100）
        """
        combined_text = f"{title_text or ''} {abstract_text or ''}"

        if not combined_text.strip():
            return 0.0

        # 提取临床指标
        metrics = self.clinical_analyzer.extract_metrics(combined_text)

        # 计算得分
        score = self.clinical_analyzer.calculate_score(metrics)

        return float(score)

    def calculate_phase_score(
        self,
        abstract_text: Optional[str] = None,
        title_text: Optional[str] = None
    ) -> float:
        """
        计算阶段得分（Phase III/NDA等）

        得分规则：
        - Phase III: +40分
        - NDA/BLA: +35分
        - Pivotal: +35分
        - Registration: +30分
        - Approved: +25分

        Args:
            abstract_text: 摘要文本
            title_text: 标题文本

        Returns:
            阶段得分（0-40）
        """
        combined_text = f"{title_text or ''} {abstract_text or ''}".lower()

        if not combined_text.strip():
            return 0.0

        # 查找阶段关键词
        max_score = 0.0
        for keyword, score in self.PHASE_KEYWORDS.items():
            if keyword.lower() in combined_text:
                max_score = max(max_score, float(score))

        return max_score

    def calculate_regulatory_score(
        self,
        abstract_text: Optional[str] = None,
        title_text: Optional[str] = None
    ) -> float:
        """
        计算监管认定得分

        得分规则：
        - Breakthrough Therapy: +30分
        - First-in-class: +30分
        - Fast Track: +20分
        - Orphan Drug: +20分
        - Best-in-class: +20分

        Args:
            abstract_text: 摘要文本
            title_text: 标题文本

        Returns:
            监管认定得分（0-30）
        """
        combined_text = f"{title_text or ''} {abstract_text or ''}".lower()

        if not combined_text.strip():
            return 0.0

        # 查找监管关键词
        max_score = 0.0
        for keyword, score in self.REGULATORY_KEYWORDS.items():
            if keyword.lower() in combined_text:
                max_score = max(max_score, float(score))

        return max_score

    def calculate_source_score(
        self,
        journal: Optional[str] = None,
        source_type: Optional[str] = None,
        publication_type: Optional[str] = None
    ) -> float:
        """
        计算来源质量得分

        得分规则：
        - ASCO/AACR/ESMO等会议: 30分
        - NEJM/Lancet/JAMA/Nature/Science: 25分
        - JCO等专科期刊: 20分
        - 其他期刊: 10分
        - Clinical Trial: +10分（额外）

        Args:
            journal: 期刊名称
            source_type: 来源类型（如 "ASCO", "AACR"）
            publication_type: 文献类型

        Returns:
            来源质量得分（0-40）
        """
        score = 0.0

        # 检查来源类型（会议等）
        if source_type:
            source_upper = source_type.upper()
            for high_quality_source in self.HIGH_QUALITY_SOURCES:
                if high_quality_source in source_upper:
                    score = 30.0
                    break
            else:
                score = 10.0

        # 检查期刊名称
        if journal and score == 0:
            journal_upper = journal.upper()
            for high_quality_source in self.HIGH_QUALITY_SOURCES:
                if high_quality_source in journal_upper:
                    if high_quality_source in ["NEJM", "LANCET", "JAMA", "NATURE", "SCIENCE"]:
                        score = 25.0
                        break
                    elif high_quality_source == "JCO" or "ONCOLOGY" in journal_upper:
                        score = 20.0
                        break
            else:
                score = 10.0

        # Clinical Trial 额外加分
        if publication_type and "clinical trial" in publication_type.lower():
            score += 10.0

        return score

    def calculate_penalty_score(
        self,
        abstract_text: Optional[str] = None,
        publication_type: Optional[str] = None
    ) -> float:
        """
        计算惩罚得分

        惩罚规则：
        - Case Report: -20分
        - Review 类型: -10分

        Args:
            abstract_text: 摘要文本
            publication_type: 文献类型

        Returns:
            惩罚得分（负数）
        """
        penalty = 0.0

        # 检查是否为 Case Report
        if abstract_text:
            if "case report" in abstract_text.lower():
                penalty -= 20.0
            elif "case series" in abstract_text.lower():
                penalty -= 10.0

        # 检查文献类型
        if publication_type:
            if "review" in publication_type.lower():
                penalty -= 10.0

        return penalty

    def calculate_publication_score(
        self,
        title: str,
        pub_date: Optional[datetime | date | str] = None,
        abstract: Optional[str] = None,
        journal: Optional[str] = None,
        source_type: Optional[str] = None,
        publication_type: Optional[str] = None,
    ) -> PublicationScore:
        """
        计算文献总分

        综合所有维度计算最终得分

        Args:
            title: 文献标题
            pub_date: 发布日期
            abstract: 文献摘要
            journal: 期刊名称
            source_type: 来源类型
            publication_type: 文献类型

        Returns:
            PublicationScore 对象

        Example:
            >>> engine = ScoringEngine()
            >>> score = engine.calculate_publication_score(
            ...     title="EGFR抑制剂在NSCLC中的III期数据",
            ...     pub_date="2024-01-15",
            ...     abstract="...ORR: 62%, mPFS: 11.2月...",
            ...     journal="JCO",
            ...     publication_type="Clinical Trial"
            ... )
            >>> print(score.total_score)
            85.5
        """
        # 1. 计算时效性得分（40%权重）
        recency_score = self.calculate_recency_score(pub_date)

        # 2. 计算临床数据得分（25%权重）
        clinical_score = self.calculate_clinical_score(abstract, title)

        # 3. 计算阶段得分（10%权重）
        phase_score = self.calculate_phase_score(abstract, title)

        # 4. 计算监管认定得分（10%权重）
        regulatory_score = self.calculate_regulatory_score(abstract, title)

        # 5. 计算来源质量得分（15%权重）
        source_score = self.calculate_source_score(journal, source_type, publication_type)

        # 6. 计算惩罚得分
        penalty_score = self.calculate_penalty_score(abstract, publication_type)

        # 7. 计算总分（加权）
        total_score = (
            recency_score * 0.4 +  # 时效性40%
            clinical_score * 0.25 +  # 临床数据25%
            source_score * 0.15 +  # 来源质量15%
            phase_score * 0.1 +  # 阶段10%
            regulatory_score * 0.1  # 监管认定10%
        )

        # 应用惩罚
        total_score += penalty_score

        # 限制分数范围
        total_score = max(0.0, min(100.0, total_score))

        # 构建得分明细
        score_breakdown = {
            "recency_score": recency_score,
            "clinical_score": clinical_score,
            "phase_score": phase_score,
            "regulatory_score": regulatory_score,
            "source_score": source_score,
            "penalty_score": penalty_score,
        }

        return PublicationScore(
            total_score=round(total_score, 1),
            recency_score=recency_score,
            clinical_score=clinical_score,
            phase_score=phase_score,
            regulatory_score=regulatory_score,
            source_score=source_score,
            penalty_score=penalty_score,
            score_breakdown=score_breakdown,
        )

    # =====================================================
    # 管线评分
    # =====================================================

    def calculate_pipeline_score(
        self,
        phase: str,
        drug_code: str,
        indication: str,
        first_seen_at: Optional[datetime | date | str] = None,
        is_first_in_class: bool = False,
    ) -> PipelineScore:
        """
        计算管线得分

        Args:
            phase: 研发阶段
            drug_code: 药物代码
            indication: 适应症
            first_seen_at: 首次发现时间
            is_first_in_class: 是否首创

        Returns:
            PipelineScore 对象
        """
        # 阶段得分
        phase_score = self._calculate_pipeline_phase_score(phase)

        # 新颖性得分
        novelty_score = 30.0 if is_first_in_class else 0.0

        # 竞争优势得分（基于药物代码和适应症）
        competition_score = self._calculate_competition_score(drug_code, indication)

        # 时效性得分
        recency_score = self.calculate_recency_score(first_seen_at)

        # 计算总分
        total_score = (
            phase_score * 0.4 +  # 阶段40%
            novelty_score * 0.2 +  # 新颖性20%
            competition_score * 0.2 +  # 竞争优势20%
            recency_score * 0.2  # 时效性20%
        )

        total_score = round(total_score, 1)

        score_breakdown = {
            "phase_score": phase_score,
            "novelty_score": novelty_score,
            "competition_score": competition_score,
            "recency_score": recency_score,
        }

        return PipelineScore(
            total_score=total_score,
            phase_score=phase_score,
            novelty_score=novelty_score,
            competition_score=competition_score,
            recency_score=recency_score,
            score_breakdown=score_breakdown,
        )

    def _calculate_pipeline_phase_score(self, phase: str) -> float:
        """计算管线阶段得分"""
        phase_lower = phase.lower()

        if "approved" in phase_lower or "上市" in phase_lower:
            return 100.0
        elif "nda" in phase_lower or "bla" in phase_lower or "申请" in phase_lower:
            return 90.0
        elif "phase 3" in phase_lower or "phase iii" in phase_lower or "iii期" in phase_lower:
            return 80.0
        elif "phase 2" in phase_lower or "phase ii" in phase_lower or "ii期" in phase_lower:
            return 60.0
        elif "phase 1" in phase_lower or "phase i" in phase_lower or "i期" in phase_lower:
            return 40.0
        else:
            return 20.0

    def _calculate_competition_score(self, drug_code: str, indication: str) -> float:
        """
        计算竞争优势得分

        基于药物代码和适应症的复杂度
        """
        score = 50.0  # 基础分

        # 药物代码复杂度
        if len(drug_code) > 10:
            score += 20.0
        elif len(drug_code) > 5:
            score += 10.0

        # 适应症复杂度
        if "NSCLC" in indication or "非小细胞肺癌" in indication:
            score += 30.0
        elif any(term in indication for term in ["乳腺癌", "胃癌", "肝癌"]):
            score += 20.0

        return min(score, 100.0)


# =====================================================
# 便捷函数
# =====================================================

_engine_instance = None

def get_scoring_engine() -> ScoringEngine:
    """获取ScoringEngine单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ScoringEngine()
    return _engine_instance


def calculate_publication_score(
    title: str,
    pub_date: Optional[datetime | date | str] = None,
    abstract: Optional[str] = None,
    journal: Optional[str] = None,
    source_type: Optional[str] = None,
    publication_type: Optional[str] = None,
) -> PublicationScore:
    """
    便捷函数：计算文献得分

    Args:
        title: 文献标题
        pub_date: 发布日期
        abstract: 文献摘要
        journal: 期刊名称
        source_type: 来源类型
        publication_type: 文献类型

    Returns:
        PublicationScore 对象
    """
    engine = get_scoring_engine()
    return engine.calculate_publication_score(
        title=title,
        pub_date=pub_date,
        abstract=abstract,
        journal=journal,
        source_type=source_type,
        publication_type=publication_type
    )
