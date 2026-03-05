"""
=====================================================
MoAClassifier - 作用机制分类器
=====================================================

从文献/管线描述中自动识别药物作用机制：
- Small Molecule (小分子)
- mAB (单抗)
- ADC (抗体偶联药物)
- PROTAC (蛋白降解靶向嵌合体)
- CAR-T (CAR-T细胞疗法)
- Gene Therapy (基因治疗)
- Bispecific Antibody (双抗)
- Radiopharmaceutical (核药)
- Vaccine (疫苗)
- Cell Therapy (细胞治疗)

使用示例：
    from core.intelligence import MoAClassifier

    classifier = MoAClassifier()
    text = "EGFR inhibitor is a small molecule tyrosine kinase inhibitor..."
    moa = classifier.classify(text)
    print(moa['modality'])  # 输出: "Small Molecule"
    print(moa['confidence'])  # 输出: 0.95

作者：A_lxl_search Team
创建日期：2026-02-02
=====================================================
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MoAInfo:
    """作用机制信息"""
    modality: str  # 药物类型
    category: str  # 大类（如"Antibody", "Cell Therapy"）
    confidence: float  # 置信度（0-1）
    keywords_matched: List[str]  # 匹配到的关键词
    aliases: List[str]  # 别名

    def to_dict(self) -> Dict[str, any]:
        """转换为字典"""
        return {
            "modality": self.modality,
            "category": self.category,
            "confidence": self.confidence,
            "keywords_matched": self.keywords_matched,
            "aliases": self.aliases,
        }


class MoAClassifier:
    """
    作用机制分类器

    使用关键词匹配和规则识别药物作用机制
    """

    def __init__(self):
        """初始化分类器"""

        # 小分子关键词
        self.small_molecule_keywords = [
            r"\bsmall molecule\b",
            r"\bsmall-molecule\b",
            r"\btyrosine kinase inhibitor\b",
            r"\bTKI\b",
            r"\bkinase inhibitor\b",
            r"\binhibitor\b",
            r"\boral\b",
            r"\btablet\b",
            r"\bcapsule\b",
            r"小分子",
            r"激酶抑制剂",
            r"口服",
        ]

        # 单抗关键词
        self.monoclonal_antibody_keywords = [
            r"\bmonoclonal antibody\b",
            r"\bmonoclonal antib\b",
            r"\bmAb\b",
            r"\bhumanized antibody\b",
            r"\bfully human antibody\b",
            r"\bchimeric antibody\b",
            r"\bantibody\b",
            r"单抗",
            r"单克隆抗体",
            r"人源化抗体",
            r"全人源抗体",
        ]

        # 双抗关键词
        self.bispecific_antibody_keywords = [
            r"\bbispecific antibody\b",
            r"\bbispecific antib\b",
            r"\bdual antibody\b",
            r"\bbispecific\b",
            r"\bBsAb\b",
            r"双抗",
            r"双特异性抗体",
        ]

        # ADC关键词
        self.adc_keywords = [
            r"\bantibody-drug conjugate\b",
            r"\bADC\b",
            r"\bantibody drug conjugate\b",
            r"\bconjugate\b",
            r"抗体偶联药物",
            r"抗体药物偶联物",
        ]

        # CAR-T关键词
        self.car_t_keywords = [
            r"\bCAR-T\b",
            r"\bCAR T\b",
            r"\bchimeric antigen receptor T-cell\b",
            r"\bCAR-T cell\b",
            r"\bCAR-T therapy\b",
            r"CAR-T细胞",
            r"嵌合抗原受体T细胞",
        ]

        # 细胞治疗关键词
        self.cell_therapy_keywords = [
            r"\bcell therapy\b",
            r"\bcellular therapy\b",
            r"\bTCR-T\b",
            r"\bTIL\b",
            r"\bNK cell\b",
            r"细胞治疗",
            r"细胞疗法",
        ]

        # 基因治疗关键词
        self.gene_therapy_keywords = [
            r"\bgene therapy\b",
            r"\bgene transfer\b",
            r"\bviral therapy\b",
            r"基因治疗",
            r"基因疗法",
        ]

        # RNA疗法关键词
        self.rna_therapy_keywords = [
            r"\bmRNA\b",
            r"\bsiRNA\b",
            r"\bRNA therapy\b",
            r"\bRNAi\b",
            r"RNA疗法",
        ]

        # PROTAC关键词
        self.protac_keywords = [
            r"\bPROTAC\b",
            r"\bproteolysis targeting chimera\b",
            r"\bprotein degradation\b",
            r"蛋白降解",
        ]

        # 疫苗关键词
        self.vaccine_keywords = [
            r"\bvaccine\b",
            r"\bvaccination\b",
            r"疫苗",
            r"预防",
        ]

        # 核药关键词
        self.radiopharmaceutical_keywords = [
            r"\bradiopharmaceutical\b",
            r"\bradiotherapy\b",
            r"\bradiolabeled\b",
            r"核药",
            r"放射性",
        ]

        # 多肽关键词
        self.peptide_keywords = [
            r"\bpeptide\b",
            r"\bpolypeptide\b",
            r"多肽",
        ]

    def _match_keywords(self, text: str, keywords: List[str]) -> tuple[int, List[str]]:
        """
        匹配关键词

        Returns:
            (匹配数量, 匹配到的关键词列表)
        """
        text_lower = text.lower()
        matched = []

        for keyword in keywords:
            if re.search(keyword, text_lower):
                matched.append(keyword)

        return len(matched), matched

    def classify(self, text: str) -> MoAInfo:
        """
        分类作用机制

        Args:
            text: 文本内容

        Returns:
            MoAInfo 对象

        Example:
            >>> classifier = MoAClassifier()
            >>> text = "EGFR inhibitor is a small molecule..."
            >>> moa = classifier.classify(text)
            >>> print(moa.modality)
            'Small Molecule'
        """
        if not text:
            return MoAInfo(
                modality="Unknown",
                category="Unknown",
                confidence=0.0,
                keywords_matched=[],
                aliases=[]
            )

        # 统计各类型匹配情况
        matches = {
            "Small Molecule": self._match_keywords(text, self.small_molecule_keywords),
            "Monoclonal Antibody": self._match_keywords(text, self.monoclonal_antibody_keywords),
            "Bispecific Antibody": self._match_keywords(text, self.bispecific_antibody_keywords),
            "ADC": self._match_keywords(text, self.adc_keywords),
            "CAR-T": self._match_keywords(text, self.car_t_keywords),
            "Cell Therapy": self._match_keywords(text, self.cell_therapy_keywords),
            "Gene Therapy": self._match_keywords(text, self.gene_therapy_keywords),
            "RNA Therapy": self._match_keywords(text, self.rna_therapy_keywords),
            "PROTAC": self._match_keywords(text, self.protac_keywords),
            "Vaccine": self._match_keywords(text, self.vaccine_keywords),
            "Radiopharmaceutical": self._match_keywords(text, self.radiopharmaceutical_keywords),
            "Peptide": self._match_keywords(text, self.peptide_keywords),
        }

        # 找出匹配最多的类型
        best_match = max(matches.items(), key=lambda x: x[1][0])

        modality = best_match[0]
        match_count, keywords_matched = best_match[1]

        # 计算置信度
        if match_count == 0:
            confidence = 0.0
        elif match_count >= 3:
            confidence = 1.0
        elif match_count == 2:
            confidence = 0.8
        else:
            confidence = 0.6

        # 确定大类
        category_mapping = {
            "Small Molecule": "Small Molecule",
            "Monoclonal Antibody": "Antibody",
            "Bispecific Antibody": "Antibody",
            "ADC": "Antibody",
            "CAR-T": "Cell Therapy",
            "Cell Therapy": "Cell Therapy",
            "Gene Therapy": "Gene Therapy",
            "RNA Therapy": "Gene Therapy",
            "PROTAC": "Small Molecule",
            "Vaccine": "Vaccine",
            "Radiopharmaceutical": "Radiopharmaceutical",
            "Peptide": "Peptide",
        }

        category = category_mapping.get(modality, "Unknown")

        # 别名
        aliases = []
        if modality == "Small Molecule":
            aliases = ["小分子", "TKI"]
        elif modality == "Monoclonal Antibody":
            aliases = ["单抗", "mAb"]
        elif modality == "Bispecific Antibody":
            aliases = ["双抗", "BsAb"]
        elif modality == "ADC":
            aliases = ["抗体偶联药物"]
        elif modality == "CAR-T":
            aliases = ["CAR-T细胞"]

        return MoAInfo(
            modality=modality,
            category=category,
            confidence=confidence,
            keywords_matched=keywords_matched,
            aliases=aliases
        )

    def get_modality_from_text(self, text: str) -> str:
        """
        便捷函数：直接获取药物类型

        Args:
            text: 文本内容

        Returns:
            药物类型字符串
        """
        info = self.classify(text)
        return info.modality


# =====================================================
# 便捷函数
# =====================================================

_classifier_instance = None

def get_moa_classifier() -> MoAClassifier:
    """获取MoAClassifier单例"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = MoAClassifier()
    return _classifier_instance
