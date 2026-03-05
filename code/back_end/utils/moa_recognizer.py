"""
=====================================================
作用机制识别器（Mechanism of Action Recognition）
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
- RNA Therapy (RNA疗法)
- Peptide (多肽)
- Oligonucleotide (寡核苷酸)
- Oncolytic Virus (溶瘤病毒)

使用示例：
    from utils.moa_recognizer import detect_moa, get_modality_info

    text = "EGFR inhibitor is a small molecule tyrosine kinase inhibitor..."
    moa = detect_moa(text)
    print(moa.modality)  # 输出: "Small Molecule"
    print(moa.confidence)  # 输出: 0.95
=====================================================
"""

import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class ModalityType(Enum):
    """药物类型枚举"""

    # 小分子
    SMALL_MOLECULE = "Small Molecule"

    # 抗体类药物
    MONOCLONAL_ANTIBODY = "Monoclonal Antibody"
    BISPECIFIC_ANTIBODY = "Bispecific Antibody"
    ADC = "ADC"  # Antibody-Drug Conjugate
    RADIOLABELED_ANTIBODY = "Radiolabeled Antibody"

    # 细胞治疗
    CAR_T = "CAR-T"
    TCR_T = "TCR-T"
    TIL = "TIL"
    NK_CELL = "NK Cell"
    MSC = "MSC"

    # 基因治疗
    GENE_THERAPY = "Gene Therapy"
    RNA_THERAPY = "RNA Therapy"
    OLIGONUCLEOTIDE = "Oligonucleotide"

    # 蛋白降解
    PROTAC = "PROTAC"
    MOLECULAR_GLUE = "Molecular Glue"

    # 疫苗
    VACCINE = "Vaccine"
    ONCOLYTIC_VIRUS = "Oncolytic Virus"

    # 其他
    PEPTIDE = "Peptide"
    RADIOPHARMACEUTICAL = "Radiopharmaceutical"
    NANOMEDICINE = "Nanomedicine"
    CELL_FREE = "Cell-Free"
    UNKNOWN = "Unknown"


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


class MoARecognizer:
    """
    作用机制识别器

    使用关键词匹配和规则识别药物作用机制
    """

    def __init__(self):
        """初始化识别器"""

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

        # TCR-T关键词
        self.tcr_t_keywords = [
            r"\bTCR-T\b",
            r"\bTCR T\b",
            r"\bT cell receptor\b",
            r"\bTCR-engineered\b",
            r"TCR-T细胞",
        ]

        # TIL关键词
        self.til_keywords = [
            r"\bTIL\b",
            r"\btumor infiltrating lymphocyte\b",
            r"\btumor-infiltrating lymphocyte\b",
            r"肿瘤浸润淋巴细胞",
        ]

        # NK细胞关键词
        self.nk_cell_keywords = [
            r"\bNK cell\b",
            r"\bnatural killer cell\b",
            r"\bNK therapy\b",
            r"NK细胞",
        ]

        # 基因治疗关键词
        self.gene_therapy_keywords = [
            r"\bgene therapy\b",
            r"\bgene transfer\b",
            r"\bviral vector\b",
            r"\bAAV\b",
            r"\bladovirus\b",
            r"\blentivirus\b",
            r"\bretrovirus\b",
            r"基因治疗",
            r"病毒载体",
            r"腺相关病毒",
        ]

        # RNA治疗关键词
        self.rna_therapy_keywords = [
            r"\bmRNA\b",
            r"\bsiRNA\b",
            r"\bshRNA\b",
            r"\bmRNA therapy\b",
            r"\bRNA interference\b",
            r"\bRNAi\b",
            r"\bsmall interfering RNA\b",
            r"RNA治疗",
            r"RNA干扰",
        ]

        # 寡核苷酸关键词
        self.oligonucleotide_keywords = [
            r"\boligonucleotide\b",
            r"\baptamer\b",
            r"\bantisense\b",
            r"\bsplice-switching\b",
            r"寡核苷酸",
            r"适配体",
            r"反义寡核苷酸",
        ]

        # PROTAC关键词
        self.protac_keywords = [
            r"\bPROTAC\b",
            r"\bproteolysis targeting chimera\b",
            r"\bprotein degradation\b",
            r"\bubiquitin ligase\b",
            r"\bE3 ligase\b",
            r"蛋白降解",
            r"靶向嵌合体",
        ]

        # 分子胶关键词
        self.molecular_glue_keywords = [
            r"\bmolecular glue\b",
            r"\bmolecular glue degrader\b",
            r"分子胶",
        ]

        # 疫苗关键词
        self.vaccine_keywords = [
            r"\bvaccine\b",
            r"\bvaccination\b",
            r"\bimmunization\b",
            r"疫苗",
            r"免疫接种",
        ]

        # 溶瘤病毒关键词
        self.oncolytic_virus_keywords = [
            r"\boncolytic virus\b",
            r"\boncolytic virotherapy\b",
            r"\bHSV-1\b",
            r"\bherpes simplex\b",
            r"溶瘤病毒",
        ]

        # 多肽关键词
        self.peptide_keywords = [
            r"\bpeptide\b",
            r"\bpolypeptide\b",
            r"多肽",
        ]

        # 核药关键词
        self.radiopharmaceutical_keywords = [
            r"\bradiopharmaceutical\b",
            r"\bradioisotope\b",
            r"\bradioligand\b",
            r"\blu-177\b",
            r"\bradium-223\b",
            r"\byttrium-90\b",
            r"核药",
            r"放射性核素",
            r"放射性配体",
        ]

        # 纳米药物关键词
        self.nanomedicine_keywords = [
            r"\bnanoparticle\b",
            r"\bnano-medicine\b",
            r"\bnanocarrier\b",
            r"\bliposome\b",
            r"\bmicelle\b",
            r"纳米药物",
            r"纳米粒",
            r"脂质体",
        ]

        # 无细胞治疗关键词
        self.cell_free_keywords = [
            r"\bcell-free\b",
            r"\bexosome\b",
            r"\bextracellular vesicle\b",
            r"外泌体",
            r"细胞外囊泡",
        ]

    def detect_modality(
        self,
        text: str,
        title: Optional[str] = None,
    ) -> MoAInfo:
        """
        检测药物类型

        Args:
            text: 文本内容（摘要/描述）
            title: 标题（权重更高）

        Returns:
            MoAInfo 对象

        Example:
            >>> recognizer = MoARecognizer()
            >>> text = "EGFR inhibitor is a small molecule TKI..."
            >>> moa = recognizer.detect_modality(text)
            >>> print(moa.modality)
            'Small Molecule'
        """
        combined_text = f"{title or ''} {text}".lower()

        if not combined_text.strip():
            return MoAInfo(
                modality=ModalityType.UNKNOWN.value,
                category="Unknown",
                confidence=0.0,
                keywords_matched=[],
                aliases=[],
            )

        # 定义所有检测器列表（按优先级排序）
        detectors = [
            # PROTAC类（优先识别，因为可能包含"molecule"等词）
            (
                self.protac_keywords,
                ModalityType.PROTAC.value,
                "Protein Degrader",
            ),
            (
                self.molecular_glue_keywords,
                ModalityType.MOLECULAR_GLUE.value,
                "Protein Degrader",
            ),
            # 细胞治疗
            (self.car_t_keywords, ModalityType.CAR_T.value, "Cell Therapy"),
            (self.tcr_t_keywords, ModalityType.TCR_T.value, "Cell Therapy"),
            (self.til_keywords, ModalityType.TIL.value, "Cell Therapy"),
            (self.nk_cell_keywords, ModalityType.NK_CELL.value, "Cell Therapy"),
            # 抗体类药物
            (self.adc_keywords, ModalityType.ADC.value, "Antibody"),
            (
                self.bispecific_antibody_keywords,
                ModalityType.BISPECIFIC_ANTIBODY.value,
                "Antibody",
            ),
            (
                self.monoclonal_antibody_keywords,
                ModalityType.MONOCLONAL_ANTIBODY.value,
                "Antibody",
            ),
            # 基因/RNA治疗
            (
                self.gene_therapy_keywords,
                ModalityType.GENE_THERAPY.value,
                "Gene Therapy",
            ),
            (self.rna_therapy_keywords, ModalityType.RNA_THERAPY.value, "Gene Therapy"),
            (
                self.oligonucleotide_keywords,
                ModalityType.OLIGONUCLEOTIDE.value,
                "Gene Therapy",
            ),
            # 疫苗/病毒
            (
                self.oncolytic_virus_keywords,
                ModalityType.ONCOLYTIC_VIRUS.value,
                "Viral Therapy",
            ),
            (self.vaccine_keywords, ModalityType.VACCINE.value, "Vaccine"),
            # 其他
            (
                self.radiopharmaceutical_keywords,
                ModalityType.RADIOPHARMACEUTICAL.value,
                "Radiopharmaceutical",
            ),
            (
                self.nanomedicine_keywords,
                ModalityType.NANOMEDICINE.value,
                "Nanomedicine",
            ),
            (self.cell_free_keywords, ModalityType.CELL_FREE.value, "Cell Therapy"),
            (self.peptide_keywords, ModalityType.PEPTIDE.value, "Peptide"),
            # 小分子（最后识别，避免误判其他类型）
            (
                self.small_molecule_keywords,
                ModalityType.SMALL_MOLECULE.value,
                "Small Molecule",
            ),
        ]

        # 遍历检测器
        for keywords, modality, category in detectors:
            matched_keywords = []
            for pattern in keywords:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    # 提取匹配的关键词
                    match = re.search(pattern, combined_text, re.IGNORECASE)
                    if match:
                        matched_keywords.append(match.group(0))

            if matched_keywords:
                # 计算置信度（基于关键词数量）
                confidence = min(0.6 + len(matched_keywords) * 0.1, 1.0)

                # 标题中的关键词权重更高
                if title:
                    title_lower = title.lower()
                    title_matches = sum(
                        1
                        for kw in matched_keywords
                        if kw.lower() in title_lower
                    )
                    if title_matches > 0:
                        confidence = min(confidence + 0.2, 1.0)

                # 获取别名
                aliases = self._get_modality_aliases(modality)

                return MoAInfo(
                    modality=modality,
                    category=category,
                    confidence=round(confidence, 2),
                    keywords_matched=list(set(matched_keywords)),
                    aliases=aliases,
                )

        # 未识别到
        return MoAInfo(
            modality=ModalityType.UNKNOWN.value,
            category="Unknown",
            confidence=0.0,
            keywords_matched=[],
            aliases=[],
        )

    def _get_modality_aliases(self, modality: str) -> List[str]:
        """
        获取药物类型的别名

        Args:
            modality: 药物类型

        Returns:
            别名列表
        """
        aliases_map = {
            ModalityType.SMALL_MOLECULE.value: [
                "Small Molecule",
                "小分子",
                "Inhibitor",
                "TKI",
            ],
            ModalityType.MONOCLONAL_ANTIBODY.value: [
                "Monoclonal Antibody",
                "mAb",
                "单抗",
                "单克隆抗体",
            ],
            ModalityType.BISPECIFIC_ANTIBODY.value: [
                "Bispecific Antibody",
                "BsAb",
                "双抗",
                "双特异性抗体",
            ],
            ModalityType.ADC.value: [
                "ADC",
                "Antibody-Drug Conjugate",
                "抗体偶联药物",
            ],
            ModalityType.CAR_T.value: [
                "CAR-T",
                "CAR-T Cell",
                "CAR-T细胞",
            ],
            ModalityType.PROTAC.value: [
                "PROTAC",
                "Protein Degrader",
                "蛋白降解",
            ],
            ModalityType.GENE_THERAPY.value: [
                "Gene Therapy",
                "基因治疗",
            ],
            ModalityType.RNA_THERAPY.value: [
                "RNA Therapy",
                "mRNA Therapy",
                "RNA治疗",
            ],
            ModalityType.VACCINE.value: ["Vaccine", "疫苗"],
            ModalityType.ONCOLYTIC_VIRUS.value: [
                "Oncolytic Virus",
                "溶瘤病毒",
            ],
            ModalityType.PEPTIDE.value: ["Peptide", "多肽"],
            ModalityType.RADIOPHARMACEUTICAL.value: [
                "Radiopharmaceutical",
                "核药",
            ],
            ModalityType.NANOMEDICINE.value: [
                "Nanomedicine",
                "纳米药物",
            ],
        }

        return aliases_map.get(modality, [])

    def classify_drug_by_modality(
        self, modality: str
    ) -> Dict[str, str]:
        """
        根据药物类型分类（用于标签化）

        Args:
            modality: 药物类型

        Returns:
            分类信息字典
        """
        category_map = {
            ModalityType.SMALL_MOLECULE.value: {
                "category": "Small Molecule",
                "sub_category": "Kinase Inhibitor",
                "technology": "Chemical Synthesis",
            },
            ModalityType.MONOCLONAL_ANTIBODY.value: {
                "category": "Biologics",
                "sub_category": "Monoclonal Antibody",
                "technology": "Recombinant DNA",
            },
            ModalityType.BISPECIFIC_ANTIBODY.value: {
                "category": "Biologics",
                "sub_category": "Bispecific Antibody",
                "technology": "Recombinant DNA",
            },
            ModalityType.ADC.value: {
                "category": "Biologics",
                "sub_category": "Antibody-Drug Conjugate",
                "technology": "Bioconjugation",
            },
            ModalityType.CAR_T.value: {
                "category": "Cell Therapy",
                "sub_category": "CAR-T",
                "technology": "Genetic Engineering",
            },
            ModalityType.PROTAC.value: {
                "category": "Targeted Protein Degradation",
                "sub_category": "PROTAC",
                "technology": "Chemical Biology",
            },
            ModalityType.GENE_THERAPY.value: {
                "category": "Gene Therapy",
                "sub_category": "Viral Vector",
                "technology": "Viral Transduction",
            },
            ModalityType.RNA_THERAPY.value: {
                "category": "Gene Therapy",
                "sub_category": "RNA Therapy",
                "technology": "RNA Delivery",
            },
            ModalityType.VACCINE.value: {
                "category": "Immunotherapy",
                "sub_category": "Vaccine",
                "technology": "Immunization",
            },
            ModalityType.PEPTIDE.value: {
                "category": "Peptide",
                "sub_category": "Therapeutic Peptide",
                "technology": "Peptide Synthesis",
            },
            ModalityType.RADIOPHARMACEUTICAL.value: {
                "category": "Radiopharmaceutical",
                "sub_category": "Radionuclide Therapy",
                "technology": "Radiolabeling",
            },
        }

        return category_map.get(
            modality,
            {
                "category": "Unknown",
                "sub_category": "Unknown",
                "technology": "Unknown",
            },
        )

    def get_modality_statistics(
        self, texts: List[str]
    ) -> Dict[str, int]:
        """
        统计多个文本中的药物类型分布

        Args:
            texts: 文本列表

        Returns:
            药物类型计数字典
        """
        stats = {}

        for text in texts:
            moa = self.detect_modality(text)
            modality = moa.modality
            stats[modality] = stats.get(modality, 0) + 1

        return stats


# =====================================================
# 便捷函数
# =====================================================

def detect_moa(text: str, title: Optional[str] = None) -> MoAInfo:
    """
    便捷函数：检测药物作用机制

    Args:
        text: 文本内容
        title: 标题

    Returns:
        MoAInfo 对象

    Example:
        >>> text = "EGFR inhibitor is a small molecule..."
        >>> moa = detect_moa(text)
        >>> print(moa.modality)
        'Small Molecule'
    """
    recognizer = MoARecognizer()
    return recognizer.detect_modality(text, title)


def get_modality_info(modality: str) -> Dict[str, str]:
    """
    便捷函数：获取药物类型分类信息

    Args:
        modality: 药物类型

    Returns:
        分类信息字典
    """
    recognizer = MoARecognizer()
    return recognizer.classify_drug_by_modality(modality)


# =====================================================
# 导出
# =====================================================

__all__ = [
    "ModalityType",
    "MoAInfo",
    "MoARecognizer",
    "detect_moa",
    "get_modality_info",
]
