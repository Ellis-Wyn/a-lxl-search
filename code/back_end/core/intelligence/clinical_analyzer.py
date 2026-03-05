"""
=====================================================
ClinicalAnalyzer - 临床数据分析器
=====================================================

从文献摘要/文本中自动提取临床指标：
- ORR (Overall Response Rate) - 总缓解率
- PFS (Progression-Free Survival) - 无进展生存期
- OS (Overall Survival) - 总生存期
- DCR (Disease Control Rate) - 疾病控制率
- n= / N= - 样本量
- p-value - 统计学意义

使用示例：
    from core.intelligence import ClinicalAnalyzer

    analyzer = ClinicalAnalyzer()
    text = "The study showed ORR of 45.2% (95% CI: 38.2-52.3), mPFS of 11.2 months..."
    metrics = analyzer.extract_metrics(text)
    print(metrics['ORR'])  # '45.2%'

作者：A_lxl_search Team
创建日期：2026-02-02
=====================================================
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ClinicalMetrics:
    """临床指标数据类"""
    orr: Optional[str] = None  # Overall Response Rate
    orr_ci: Optional[str] = None  # ORR 置信区间
    pfs: Optional[str] = None  # Progression-Free Survival
    pfs_ci: Optional[str] = None  # PFS 置信区间
    os_val: Optional[str] = None  # Overall Survival (os避免和os模块冲突)
    os_ci: Optional[str] = None  # OS 置信区间
    dcr: Optional[str] = None  # Disease Control Rate
    dcr_ci: Optional[str] = None  # DCR 置信区间
    sample_size: Optional[int] = None  # n=
    p_value: Optional[str] = None  # p-value
    safety: Optional[str] = None  # 安全性数据
    efficacy: Optional[str] = None  # 有效性数据

    def to_dict(self) -> Dict[str, Optional[str]]:
        """转换为字典"""
        return {
            "ORR": self.orr,
            "ORR_CI": self.orr_ci,
            "PFS": self.pfs,
            "PFS_CI": self.pfs_ci,
            "OS": self.os_val,
            "OS_CI": self.os_ci,
            "DCR": self.dcr,
            "DCR_CI": self.dcr_ci,
            "Sample_Size": self.sample_size,
            "P_Value": self.p_value,
            "Safety": self.safety,
            "Efficacy": self.efficacy,
        }

    def has_any_metric(self) -> bool:
        """是否包含任何临床指标"""
        return any([
            self.orr, self.pfs, self.os_val, self.dcr,
            self.sample_size, self.p_value
        ])


class ClinicalAnalyzer:
    """
    临床数据分析器

    使用正则表达式从文本中提取临床数据
    """

    def __init__(self):
        """初始化分析器"""

        # ORR (Overall Response Rate)
        self.orr_patterns = [
            r'ORR\s*[:]\s*(\d+\.?\d*%?)',  # ORR: 45.2%
            r'ORR\s+of\s+(\d+\.?\d*%?)',  # ORR of 45.2%
            r'overall\s+response\s+rate\s*[:]\s*(\d+\.?\d*%?)',  # overall response rate: 45.2%
            r'总缓解率\s*[:]\s*(\d+\.?\d*%?)',  # 总缓解率: 45.2%
        ]

        # PFS (Progression-Free Survival)
        self.pfs_patterns = [
            r'mPFS\s*[:]\s*(\d+\.?\d*\s*(?:months?|mos)?)',  # mPFS: 11.2 months
            r'median\s+PFS\s*[:]\s*(\d+\.?\d*\s*(?:months?|mos)?)',  # median PFS: 11.2 months
            r'PFS\s*[:]\s*(\d+\.?\d*\s*(?:months?|mos)?)',  # PFS: 11.2 months
            r'无进展生存期\s*[:]\s*(\d+\.?\d*\s*(?:个月|月)?)',  # 无进展生存期: 11.2个月
        ]

        # OS (Overall Survival)
        self.os_patterns = [
            r'mOS\s*[:]\s*(\d+\.?\d*\s*(?:months?|mos)?)',  # mOS: 28.5 months
            r'median\s+OS\s*[:]\s*(\d+\.?\d*\s*(?:months?|mos)?)',  # median OS: 28.5 months
            r'OS\s*[:]\s*(\d+\.?\d*\s*(?:months?|mos)?)',  # OS: 28.5 months
            r'总生存期\s*[:]\s*(\d+\.?\d*\s*(?:个月|月)?)',  # 总生存期: 28.5个月
        ]

        # DCR (Disease Control Rate)
        self.dcr_patterns = [
            r'DCR\s*[:]\s*(\d+\.?\d*%?)',  # DCR: 65.2%
            r'disease\s+control\s+rate\s*[:]\s*(\d+\.?\d*%?)',  # disease control rate: 65.2%
            r'疾病控制率\s*[:]\s*(\d+\.?\d*%?)',  # 疾病控制率: 65.2%
        ]

        # Sample Size
        self.sample_size_patterns = [
            r'n\s*=\s*(\d+)',  # n = 150
            r'N\s*=\s*(\d+)',  # N = 150
            r'样本量\s*[:]\s*(\d+)',  # 样本量: 150
            r'(\d+)\s+patients?',  # 150 patients
        ]

        # P-value
        self.p_value_patterns = [
            r'p\s*[<>=]\s*(0\.?\d+)',  # p < 0.05
            r'P\s*[<>=]\s*(0\.?\d+)',  # P < 0.05
            r'P值\s*[:]\s*(<\s*0\.?\d+)',  # P值: < 0.05
        ]

        # Confidence Intervals (95% CI: X-Y)
        self.ci_patterns = [
            r'\((\d+\.?\d*%?)\s*[-–]\s*(\d+\.?\d*%?)\s*95\s*%?\s*CI\)',  # (38.2%–52.3% 95% CI)
            r'95\s*%\s*CI\s*[:]\s*(\d+\.?\d*%?)\s*[-–]\s*(\d+\.?\d*%?)',  # 95% CI: 38.2-52.3%
        ]

    def extract_value(self, text: str, patterns: List[str]) -> Optional[str]:
        """
        使用多个模式提取值

        Args:
            text: 文本
            patterns: 正则表达式列表

        Returns:
            提取的值或None
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_ci(self, text: str, metric_value: str) -> Optional[str]:
        """
        提取置信区间

        Args:
            text: 文本
            metric_value: 指标值（用于查找附近的CI）

        Returns:
            置信区间字符串或None
        """
        for pattern in self.ci_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ci_lower = match.group(1)
                ci_upper = match.group(2)
                return f"{ci_lower}-{ci_upper}"
        return None

    def extract_metrics(self, text: str) -> ClinicalMetrics:
        """
        从文本中提取所有临床指标

        Args:
            text: 文本内容

        Returns:
            ClinicalMetrics 对象

        Example:
            >>> analyzer = ClinicalAnalyzer()
            >>> text = "The study showed ORR of 45.2% (95% CI: 38.2-52.3), mPFS of 11.2 months..."
            >>> metrics = analyzer.extract_metrics(text)
            >>> print(metrics.orr)
            '45.2%'
            >>> print(metrics.pfs)
            '11.2 months'
        """
        if not text:
            return ClinicalMetrics()

        metrics = ClinicalMetrics()

        # 提取 ORR
        metrics.orr = self.extract_value(text, self.orr_patterns)
        if metrics.orr:
            metrics.orr_ci = self.extract_ci(text, metrics.orr)

        # 提取 PFS
        metrics.pfs = self.extract_value(text, self.pfs_patterns)
        if metrics.pfs:
            metrics.pfs_ci = self.extract_ci(text, metrics.pfs)

        # 提取 OS
        metrics.os_val = self.extract_value(text, self.os_patterns)
        if metrics.os_val:
            metrics.os_ci = self.extract_ci(text, metrics.os_val)

        # 提取 DCR
        metrics.dcr = self.extract_value(text, self.dcr_patterns)
        if metrics.dcr:
            metrics.dcr_ci = self.extract_ci(text, metrics.dcr)

        # 提取样本量
        sample_size_str = self.extract_value(text, self.sample_size_patterns)
        if sample_size_str:
            try:
                metrics.sample_size = int(sample_size_str)
            except ValueError:
                pass

        # 提取 P-value
        metrics.p_value = self.extract_value(text, self.p_value_patterns)

        return metrics

    def calculate_score(self, metrics: ClinicalMetrics) -> float:
        """
        计算临床数据得分

        得分规则（参考需求说明书）：
        - 有 ORR/PFS/OS: +50分
        - 有 n=: +25分
        - 总分上限100分

        Args:
            metrics: 临床指标对象

        Returns:
            得分（0-100）
        """
        if not metrics:
            return 0.0

        score = 0.0

        # 主要临床指标（ORR, PFS, OS）
        if metrics.orr:
            score += 25.0

        if metrics.pfs:
            score += 15.0

        if metrics.os_val:
            score += 15.0

        if metrics.dcr:
            score += 10.0

        # 样本量
        if metrics.sample_size:
            score += 25.0

        # 统计学意义
        if metrics.p_value:
            score += 10.0

        return min(score, 100.0)  # 上限100分

    def has_clinical_data(self, text: str) -> bool:
        """
        检查文本是否包含临床数据

        Args:
            text: 文本内容

        Returns:
            是否包含临床数据
        """
        metrics = self.extract_metrics(text)
        return metrics.has_any_metric()


# =====================================================
# 便捷函数
# =====================================================

_analyzer_instance = None

def get_clinical_analyzer() -> ClinicalAnalyzer:
    """获取ClinicalAnalyzer单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ClinicalAnalyzer()
    return _analyzer_instance


def extract_clinical_metrics(text: str) -> ClinicalMetrics:
    """
    便捷函数：提取临床指标

    Args:
        text: 文本内容

    Returns:
        ClinicalMetrics 对象
    """
    analyzer = get_clinical_analyzer()
    return analyzer.extract_metrics(text)


def calculate_clinical_score(metrics: ClinicalMetrics) -> float:
    """
    便捷函数：计算临床得分

    Args:
        metrics: 临床指标对象

    Returns:
        得分（0-100）
    """
    analyzer = get_clinical_analyzer()
    return analyzer.calculate_score(metrics)
