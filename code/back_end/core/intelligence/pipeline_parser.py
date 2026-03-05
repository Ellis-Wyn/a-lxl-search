"""
=====================================================
PipelineParser - 管线解析器
=====================================================

解析管线描述文本，提取关键信息：
- 联合用药检测
- 终止关键词检测
- 适应症提取
- 靶点提取

使用示例：
    from core.intelligence import PipelineParser

    parser = PipelineParser()
    text = "Drug A + Drug B in combination for NSCLC treatment..."
    info = parser.parse(text)
    print(info['is_combination'])  # True
    print(info['is_discontinued'])  # False

作者：A_lxl_search Team
创建日期：2026-02-02
=====================================================
"""

import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class PipelineInfo:
    """管线信息"""
    is_combination: bool  # 是否联合用药
    is_discontinued: bool  # 是否已终止
    is_first_in_class: bool  # 是否首创
    is_best_in_class: bool  # 是否最佳
    targets: List[str]  # 靶点列表
    indications: List[str]  # 适应症列表
    combination_drugs: List[str]  # 联合用药列表
    discontinuation_reason: Optional[str]  # 终止原因

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "is_combination": self.is_combination,
            "is_discontinued": self.is_discontinued,
            "is_first_in_class": self.is_first_in_class,
            "is_best_in_class": self.is_best_in_class,
            "targets": self.targets,
            "indications": self.indications,
            "combination_drugs": self.combination_drugs,
            "discontinuation_reason": self.discontinuation_reason,
        }


class PipelineParser:
    """
    管线解析器

    从文本中解析管线关键信息
    """

    # 联合用药关键词
    COMBINATION_KEYWORDS = [
        r"\b\+\s*\w",  # Drug A + Drug B
        r"\bplus\b",
        r"\bin combination\b",
        r"\bcombination\b",
        r"\bcombo\b",
        r"\bwith\b",
        r"\bcombined\b",
        r"联合",
        r"联合用药",
        r"合并",
    ]

    # 终止关键词
    DISCONTINUED_KEYWORDS = [
        r"\bdiscontinued\b",
        r"\bterminated\b",
        r"\bwithdrawn\b",
        r"\bsuspended\b",
        r"\bhalted\b",
        r"\bstopped\b",
        r"已终止",
        r"终止",
        r"暂停",
        r"退场",
        r"撤回",
    ]

    # 首创关键词
    FIRST_IN_CLASS_KEYWORDS = [
        r"\bfirst-in-class\b",
        r"\bfirst in class\b",
        r"\bfic\b",
        r"首创",
        r"同类首创",
    ]

    # 最佳同类关键词
    BEST_IN_CLASS_KEYWORDS = [
        r"\bbest-in-class\b",
        r"\bbest in class\b",
        r"\bbic\b",
        r"同类最佳",
    ]

    # 常见靶点
    COMMON_TARGETS = [
        "EGFR", "HER2", "VEGFR", "PD-1", "PD-L1", "CTLA-4",
        "ALK", "ROS1", "BRAF", "KRAS", "NRAS", "PI3K", "mTOR",
        "CD19", "CD20", "BCMA", "CD47", "CLDN18", "FGFR", "MET",
        "PARP", "CDK4", "CDK6", "JAK", "STAT", "TIGIT", "LAG3",
        "TIM3", "IDO1", "CXCR4", "CCR5", "GITR", "OX40", "4-1BB",
    ]

    # 常见适应症
    COMMON_INDICATIONS = [
        "NSCLC", "非小细胞肺癌",
        "SCLC", "小细胞肺癌",
        "乳腺癌", "三阴性乳腺癌", "HER2阳性乳腺癌",
        "胃癌", "食管胃结合部癌",
        "结直肠癌", "直肠癌",
        "肝癌", "肝细胞癌",
        "胰腺癌",
        "肾癌", "肾细胞癌",
        "膀胱癌", "尿路上皮癌",
        "前列腺癌",
        "卵巢癌",
        "淋巴瘤", "非霍奇金淋巴瘤", "霍奇金淋巴瘤",
        "白血病", "急性白血病", "慢性淋巴细胞白血病",
        "多发性骨髓瘤",
        "黑色素瘤",
        "头颈鳞癌",
    ]

    def __init__(self):
        """初始化解析器"""
        # 编译正则表达式
        self.combination_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.COMBINATION_KEYWORDS]
        self.discontinued_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.DISCONTINUED_KEYWORDS]
        self.first_in_class_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.FIRST_IN_CLASS_KEYWORDS]
        self.best_in_class_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.BEST_IN_CLASS_KEYWORDS]

    def parse(self, text: str) -> PipelineInfo:
        """
        解析管线文本

        Args:
            text: 管线描述文本

        Returns:
            PipelineInfo 对象

        Example:
            >>> parser = PipelineParser()
            >>> text = "Drug A + Drug B for NSCLC treatment..."
            >>> info = parser.parse(text)
            >>> print(info.is_combination)
            True
            >>> print(info.indications)
            ['NSCLC']
        """
        if not text:
            return PipelineInfo(
                is_combination=False,
                is_discontinued=False,
                is_first_in_class=False,
                is_best_in_class=False,
                targets=[],
                indications=[],
                combination_drugs=[],
                discontinuation_reason=None
            )

        return PipelineInfo(
            is_combination=self._detect_combination(text),
            is_discontinued=self._detect_discontinued(text),
            is_first_in_class=self._detect_first_in_class(text),
            is_best_in_class=self._detect_best_in_class(text),
            targets=self._extract_targets(text),
            indications=self._extract_indications(text),
            combination_drugs=self._extract_combination_drugs(text),
            discontinuation_reason=self._extract_discontinuation_reason(text),
        )

    def _detect_combination(self, text: str) -> bool:
        """检测联合用药"""
        for pattern in self.combination_patterns:
            if pattern.search(text):
                return True
        return False

    def _detect_discontinued(self, text: str) -> bool:
        """检测终止状态"""
        for pattern in self.discontinued_patterns:
            if pattern.search(text):
                return True
        return False

    def _detect_first_in_class(self, text: str) -> bool:
        """检测首创"""
        for pattern in self.first_in_class_patterns:
            if pattern.search(text):
                return True
        return False

    def _detect_best_in_class(self, text: str) -> bool:
        """检测最佳同类"""
        for pattern in self.best_in_class_patterns:
            if pattern.search(text):
                return True
        return False

    def _extract_targets(self, text: str) -> List[str]:
        """提取靶点"""
        targets = []
        text_upper = text.upper()

        for target in self.COMMON_TARGETS:
            if target.upper() in text_upper:
                targets.append(target)

        return targets

    def _extract_indications(self, text: str) -> List[str]:
        """提取适应症"""
        indications = []

        for indication in self.COMMON_INDICATIONS:
            if indication in text:
                indications.append(indication)

        return indications

    def _extract_combination_drugs(self, text: str) -> List[str]:
        """提取联合用药"""
        drugs = []

        # 匹配 "Drug A + Drug B" 或 "Drug A plus Drug B"
        pattern = re.compile(r'\b([A-Z][a-zA-Z0-9\-]+)\s*\+\s*([A-Z][a-zA-Z0-9\-]+)\b')
        matches = pattern.findall(text)

        for match in matches:
            drugs.extend(list(match))

        # 匹配 "Drug A and Drug B"
        pattern = re.compile(r'\b([A-Z][a-zA-Z0-9\-]+)\s+and\s+([A-Z][a-zA-Z0-9\-]+)\b', re.IGNORECASE)
        matches = pattern.findall(text)

        for match in matches:
            drugs.extend(list(match))

        return list(set(drugs))  # 去重

    def _extract_discontinuation_reason(self, text: str) -> Optional[str]:
        """提取终止原因"""
        # 常见终止原因
        reasons = {
            "safety": ["safety", "toxicity", "adverse event", "安全性", "毒性"],
            "efficacy": ["lack of efficacy", "ineffective", "无效", "缺乏疗效"],
            "commercial": ["commercial", "strategic", "商业", "战略"],
            "regulatory": ["regulatory", "fda", "监管"],
        }

        text_lower = text.lower()

        for reason, keywords in reasons.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return reason

        return None

    def is_combination_therapy(self, text: str) -> bool:
        """
        便捷函数：判断是否联合用药
        """
        return self._detect_combination(text)

    def is_discontinued_therapy(self, text: str) -> bool:
        """
        便捷函数：判断是否已终止
        """
        return self._detect_discontinued(text)


# =====================================================
# 便捷函数
# =====================================================

_parser_instance = None

def get_pipeline_parser() -> PipelineParser:
    """获取PipelineParser单例"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = PipelineParser()
    return _parser_instance
