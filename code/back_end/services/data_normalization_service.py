"""
=====================================================
数据归一化服务 - Data Normalization Service
=====================================================

功能：
1. Phase 标准化（"临床I期" → "Phase 1"）
2. 适应症标准化（"非小细胞肺癌" → "NSCLC"）
3. 公司名称归一化

作者：A_lxl_search Team
创建日期：2026-02-05
=====================================================
"""

import re
from typing import Dict, List, Optional, Set
from core.logger import get_logger

logger = get_logger(__name__)


class DataNormalizationService:
    """
    数据归一化服务

    功能：
    - 标准化 Phase（临床I期、II期、III期 → Phase 1/2/3）
    - 标准化适应症（非小细胞肺癌 → NSCLC）
    - 归一化公司名称（恒瑞医药、恒瑞 → 江苏恒瑞）
    """

    def __init__(self):
        """初始化归一化服务"""
        # Phase 映射表
        self.phase_normalization_map = self._build_phase_map()

        # 适应症映射表
        self.indication_normalization_map = self._build_indication_map()

        # 公司名称映射表
        self.company_normalization_map = self._build_company_map()

    # =====================================================
    # Phase 归一化
    # =====================================================

    def normalize_phase(self, phase: str) -> str:
        """
        标准化 Phase

        Args:
            phase: 原始 Phase 字符串

        Returns:
            标准化后的 Phase（Phase 1/2/3/Preclinical/Approved）

        Examples:
            >>> service = DataNormalizationService()
            >>> service.normalize_phase("临床I期")
            'Phase 1'
            >>> service.normalize_phase("II期")
            'Phase 2'
        """
        if not phase:
            return "Unknown"

        phase_clean = phase.strip().lower()

        # 直接匹配
        if phase_clean in self.phase_normalization_map:
            return self.phase_normalization_map[phase_clean]

        # 正则匹配
        for pattern, standard in self.phase_normalization_map.items():
            if pattern.startswith("regex_"):
                regex_pattern = pattern.replace("regex_", "")
                if re.search(regex_pattern, phase_clean):
                    return standard

        # 如果没找到，尝试提取数字
        match = re.search(r"(\d+)", phase_clean)
        if match:
            phase_num = match.group(1)
            if phase_num in ["1", "2", "3"]:
                return f"Phase {phase_num}"
            elif phase_num in ["0", "4"]:
                return "Preclinical"

        # 默认返回原值（首字母大写）
        return phase.title() if phase_clean else "Unknown"

    def _build_phase_map(self) -> Dict[str, str]:
        """构建 Phase 映射表"""
        return {
            # 标准格式
            "phase 1": "Phase 1",
            "phase 2": "Phase 2",
            "phase 3": "Phase 3",
            "phase i": "Phase 1",
            "phase ii": "Phase 2",
            "phase iii": "Phase 3",

            # 中文格式
            "i期": "Phase 1",
            "ii期": "Phase 2",
            "iii期": "Phase 3",
            "1期": "Phase 1",
            "2期": "Phase 2",
            "3期": "Phase 3",
            "临床i期": "Phase 1",
            "临床ii期": "Phase 2",
            "临床iii期": "Phase 3",
            "临床1期": "Phase 1",
            "临床2期": "Phase 2",
            "临床3期": "Phase 3",

            # 其他常见表示
            "preclinical": "Preclinical",
            "临床前": "Preclinical",
            "pre-clinical": "Preclinical",

            "approved": "Approved",
            "已上市": "Approved",
            "批准": "Approved",
            "上市": "Approved",

            "filing": "Filing",
            "申报": "Filing",
            "申请": "Filing",

            "nda": "NDA",
            "bla": "BLA",
            "anda": "ANDA",

            # 正则模式（支持更多变体）
            "regex_^(?:临床)?i[期期]": "Phase 1",
            "regex_^(?:临床)?ii?[期期]": "Phase 2",
            "regex_^(?:临床)?iii?[期期]": "Phase 3",
            "regex_^(?:临床)?[1一二]期": "Phase 1",
            "regex_^(?:临床)?[2二两]期": "Phase 2",
            "regex_^(?:临床)?[3三三]期": "Phase 3",
        }

    # =====================================================
    # 适应症归一化
    # =====================================================

    def normalize_indication(self, indication: str) -> str:
        """
        标准化适应症

        Args:
            indication: 原始适应症字符串

        Returns:
            标准化后的适应症

        Examples:
            >>> service = DataNormalizationService()
            >>> service.normalize_indication("非小细胞肺癌")
            'NSCLC'
            >>> service.normalize_indication("非小细胞肺癌(NSCLC)")
            'NSCLC'
        """
        if not indication:
            return "Unknown"

        indication_clean = indication.strip()

        # 移除括号内容（已包含标准名称）
        match = re.search(r"\(([A-Z]+)\)", indication_clean)
        if match:
            standard = match.group(1)
            if self._is_valid_standard_indication(standard):
                return standard

        # 直接匹配
        indication_lower = indication_clean.lower()
        if indication_lower in self.indication_normalization_map:
            return self.indication_normalization_map[indication_lower]

        # 部分匹配
        for key, standard in self.indication_normalization_map.items():
            if key in indication_lower:
                return standard

        # 默认返回原值
        return indication_clean

    def _build_indication_map(self) -> Dict[str, str]:
        """构建适应症映射表"""
        return {
            # 肺癌
            "非小细胞肺癌": "NSCLC",
            "小细胞肺癌": "SCLC",
            "nsclc": "NSCLC",
            "sclc": "SCLC",
            "非小细胞": "NSCLC",
            "小细胞": "SCLC",

            # 乳腺癌
            "乳腺癌": "Breast Cancer",
            "三阴性乳腺癌": "TNBC",
            "her2阳性乳腺癌": "HER2+ Breast Cancer",

            # 结直肠癌
            "结直肠癌": "Colorectal Cancer",
            "结肠癌": "Colon Cancer",
            "直肠癌": "Rectal Cancer",

            # 肝癌
            "肝癌": "Liver Cancer",
            "肝细胞癌": "HCC",
            "肝内胆管癌": "ICC",

            # 胃癌
            "胃癌": "Gastric Cancer",
            "食管癌": "Esophageal Cancer",
            "胃食管结合部癌": "GEJ Cancer",

            # 血液肿瘤
            "淋巴瘤": "Lymphoma",
            "白血病": "Leukemia",
            "多发性骨髓瘤": "Multiple Myeloma",

            # 其他常见
            "黑色素瘤": "Melanoma",
            "肾癌": "Renal Cell Carcinoma",
            "胰腺癌": "Pancreatic Cancer",
            "卵巢癌": "Ovarian Cancer",
            "前列腺癌": "Prostate Cancer",
            "胶质母细胞瘤": "Glioblastoma",
        }

    def _is_valid_standard_indication(self, text: str) -> bool:
        """检查是否是标准适应症缩写"""
        # 大写字母组合，长度2-6
        return bool(re.match(r"^[A-Z]{2,6}$", text))

    # =====================================================
    # 公司名称归一化
    # =====================================================

    def normalize_company_name(self, company: str) -> str:
        """
        标准化公司名称

        Args:
            company: 原始公司名称

        Returns:
            标准化后的公司名称

        Examples:
            >>> service = DataNormalizationService()
            >>> service.normalize_company_name("恒瑞")
            '江苏恒瑞医药'
            >>> service.normalize_company_name("百济神州")
            '百济神州（北京）'
        """
        if not company:
            return "Unknown"

        company_clean = company.strip()

        # 直接匹配
        if company_clean in self.company_normalization_map:
            return self.company_normalization_map[company_clean]

        # 部分匹配（检查是否包含关键词）
        company_lower = company_clean.lower()
        for keyword, standard in self.company_normalization_map.items():
            if keyword in company_lower or company_lower in keyword:
                return standard

        # 默认返回原值
        return company_clean

    def _build_company_map(self) -> Dict[str, str]:
        """构建公司名称映射表"""
        return {
            # 恒瑞医药
            "恒瑞": "江苏恒瑞医药股份有限公司",
            "恒瑞医药": "江苏恒瑞医药股份有限公司",
            "江苏恒瑞": "江苏恒瑞医药股份有限公司",
            "hengrui": "江苏恒瑞医药股份有限公司",

            # 百济神州
            "百济": "百济神州（北京）生物科技有限公司",
            "百济神州": "百济神州（北京）生物科技有限公司",
            "beigene": "百济神州（北京）生物科技有限公司",

            # 信达生物
            "信达": "信达生物制药（苏州）有限公司",
            "信达生物": "信达生物制药（苏州）有限公司",

            # 君实生物
            "君实": "君实生物科技股份有限公司",
            "君实生物": "君实生物科技股份有限公司",

            # 康方生物
            "康方": "中山康方生物医药有限公司",
            "康方生物": "中山康方生物医药有限公司",

            # 再鼎医药
            "再鼎": "再鼎医药（上海）有限公司",
            "再鼎医药": "再鼎医药（上海）有限公司",

            # 和黄医药
            "和黄": "和黄医药（上海）有限公司",
            "和黄医药": "和黄医药（上海）有限公司",

            # 亚盛医药
            "亚盛": "江苏亚盛医药开发有限公司",
            "亚盛医药": "江苏亚盛医药开发有限公司",

            # 药明生物
            "药明": "无锡药明生物技术股份有限公司",
            "药明生物": "无锡药明生物技术股份有限公司",

            # 先声药业
            "先声": "先声药业有限公司",
            "先声药业": "先声药业有限公司",

            # 石药集团
            "石药": "石药集团有限公司",
            "石药集团": "石药集团有限公司",

            # 复星医药
            "复星": "上海复星医药（集团）股份有限公司",
            "复星医药": "上海复星医药（集团）股份有限公司",
        }

    # =====================================================
    # 批量归一化
    # =====================================================

    def normalize_pipeline_data(self, pipeline_data: Dict) -> Dict:
        """
        批量归一化管线数据

        Args:
            pipeline_data: 原始管线数据字典

        Returns:
            归一化后的管线数据
        """
        normalized = pipeline_data.copy()

        # 归一化 Phase
        if "phase" in normalized:
            normalized["phase_raw"] = normalized["phase"]  # 保留原始值
            normalized["phase"] = self.normalize_phase(normalized["phase"])

        # 归一化适应症
        if "indication" in normalized:
            normalized["indication_raw"] = normalized["indication"]
            normalized["indication"] = self.normalize_indication(normalized["indication"])

        # 归一化公司名称
        if "company_name" in normalized:
            normalized["company_name_raw"] = normalized["company_name"]
            normalized["company_name"] = self.normalize_company_name(normalized["company_name"])

        return normalized

    def batch_normalize_pipelines(self, pipelines: List[Dict]) -> List[Dict]:
        """
        批量归一化多条管线数据

        Args:
            pipelines: 管线数据列表

        Returns:
            归一化后的管线数据列表
        """
        return [self.normalize_pipeline_data(p) for p in pipelines]


# =====================================================
# 全局单例
# =====================================================

_normalization_service: Optional[DataNormalizationService] = None


def get_normalization_service() -> DataNormalizationService:
    """获取归一化服务单例"""
    global _normalization_service
    if _normalization_service is None:
        _normalization_service = DataNormalizationService()
    return _normalization_service


__all__ = [
    "DataNormalizationService",
    "get_normalization_service",
]
