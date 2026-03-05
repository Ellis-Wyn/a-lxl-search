"""
=====================================================
管线状态检测工具
=====================================================

检测管线状态：
- 终止研发（Discontinued）
- 联合用药（Combination Therapy）

使用方式：
    from utils.pipeline_parser import DiscontinuationDetector, CombinationTherapyDetector

    # 检测终止
    is_discontinued = DiscontinuationDetector.is_discontinued(text)

    # 检测联合用药
    is_combo, combo_drugs = CombinationTherapyDetector.detect_combination(text, [drug_code])
=====================================================
"""

import re
from typing import List, Tuple, Optional
from core.logger import get_logger

logger = get_logger(__name__)


# =====================================================
# 终止研发检测器
# =====================================================

class DiscontinuationDetector:
    """终止研发检测器"""

    # 终止关键词
    DISCONTINUED_KEYWORDS = [
        'discontinued',
        'terminated',
        'dropped',
        'suspended',
        'withdrawn',
        'halted',
        'stopped',
        # 中文
        '终止',
        '暂停',
        '放弃',
        '已终止',
        '已暂停',
        '已放弃',
        '停止',
        '中止',
    ]

    @classmethod
    def is_discontinued(cls, text: str) -> bool:
        """
        检测是否已终止研发

        Args:
            text: 待检测文本（可以是indication、phase或其他字段）

        Returns:
            是否已终止
        """
        if not text:
            return False

        text_lower = text.lower()

        for keyword in cls.DISCONTINUED_KEYWORDS:
            if keyword in text_lower:
                logger.debug(f"Found discontinued keyword: {keyword} in text")
                return True

        return False

    @classmethod
    def get_discontinued_reason(cls, text: str) -> Optional[str]:
        """
        获取终止原因

        Args:
            text: 待检测文本

        Returns:
            终止原因或 None
        """
        if not text:
            return None

        # 查找包含关键词的完整句子或短语
        for keyword in cls.DISCONTINUED_KEYWORDS:
            if keyword in text.lower():
                # 返回关键词前后50个字符作为上下文
                idx = text.lower().find(keyword)
                start = max(0, idx - 50)
                end = min(len(text), idx + 50)
                return text[start:end].strip()

        return None


# =====================================================
# 联合用药检测器
# =====================================================

class CombinationTherapyDetector:
    """联合用药检测器"""

    # 联合用药模式
    COMBINATION_PATTERNS = [
        r'\+\s*',                      # "Drug A + Drug B"
        r'\b(?:in\s+)?combination\s+(?:with|of)\b',  # "in combination with"
        r'\b(?:plus|&)\b',             # "Drug A plus Drug B"
        r'\band\b',                    # "Drug A and Drug B" (谨慎使用)
        r'联合',                        # 中文
        r'联用',                        # 中文
        r'合用',                        # 中文
    ]

    # 药物代码模式
    DRUG_CODE_PATTERN = r'\b([A-Z]{2,}-\d{3,})\b'

    @classmethod
    def detect_combination(cls, text: str, known_drugs: List[str]) -> Tuple[bool, List[str]]:
        """
        检测是否为联合用药

        Args:
            text: 待检测文本
            known_drugs: 已识别的药物列表

        Returns:
            (是否联合用药, 联合药物列表)
        """
        if not text:
            return False, []

        text_lower = text.lower()

        # 检查联合用药关键词
        for pattern in cls.COMBINATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Found combination pattern: {pattern} in text")
                # 提取联合药物
                combo_drugs = cls._extract_drugs(text, known_drugs)
                return True, combo_drugs

        return False, []

    @classmethod
    def _extract_drugs(cls, text: str, known_drugs: List[str]) -> List[str]:
        """
        从文本中提取药物代码

        Args:
            text: 文本内容
            known_drugs: 已知药物列表

        Returns:
            联合药物代码列表
        """
        # 提取所有药物代码
        found_drugs = re.findall(cls.DRUG_CODE_PATTERN, text)

        # 去重
        found_drugs = list(set(found_drugs))

        # 过滤掉已知的药物（只返回联合药物）
        combination_drugs = [d for d in found_drugs if d not in known_drugs]

        logger.debug(f"Extracted combination drugs: {combination_drugs}")
        return combination_drugs

    @classmethod
    def parse_combination_therapy(cls, text: str, primary_drug: str) -> Optional[dict]:
        """
        解析联合用药方案

        Args:
            text: 文本内容
            primary_drug: 主要药物代码

        Returns:
            联合用药信息字典或 None
        """
        is_combination, combo_drugs = cls.detect_combination(text, [primary_drug])

        if not is_combination:
            return None

        return {
            "is_combination": True,
            "primary_drug": primary_drug,
            "combination_drugs": combo_drugs,
            "all_drugs": [primary_drug] + combo_drugs,
            "therapy_type": "combination"
        }


__all__ = [
    "DiscontinuationDetector",
    "CombinationTherapyDetector",
]
