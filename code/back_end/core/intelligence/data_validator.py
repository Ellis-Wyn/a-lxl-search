"""
=====================================================
DataValidator - 数据验证器
=====================================================

验证数据质量，确保数据的完整性和准确性：
- Pipeline 数据验证
- Publication 数据验证
- Target 数据验证
- 字段完整性检查
- 数据格式验证

使用示例：
    from core.intelligence import DataValidator

    validator = DataValidator()
    result = validator.validate_pipeline_item(pipeline_dict)
    if result.is_valid:
        print("数据有效")
    else:
        print(f"错误: {result.errors}")

作者：A_lxl_search Team
创建日期：2026-02-02
=====================================================
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool  # 是否有效
    errors: List[str] = field(default_factory=list)  # 错误列表
    warnings: List[str] = field(default_factory=list)  # 警告列表
    missing_fields: List[str] = field(default_factory=list)  # 缺失字段

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "missing_fields": self.missing_fields,
        }


class DataValidator:
    """
    数据验证器

    验证各类数据的完整性和准确性
    """

    # Pipeline 必需字段
    PIPELINE_REQUIRED_FIELDS = [
        "drug_code",
        "company_name",
        "indication",
        "phase",
    ]

    # Pipeline 可选字段
    PIPELINE_OPTIONAL_FIELDS = [
        "modality",
        "source_url",
        "first_seen_at",
        "last_seen_at",
        "status",
    ]

    # Publication 必需字段
    PUBLICATION_REQUIRED_FIELDS = [
        "pmid",
        "title",
    ]

    # Publication 可选字段
    PUBLICATION_OPTIONAL_FIELDS = [
        "abstract",
        "journal",
        "pub_date",
        "publication_type",
        "authors",
        "doi",
    ]

    # Target 必需字段
    TARGET_REQUIRED_FIELDS = [
        "target_id",
        "standard_name",
    ]

    # Target 可选字段
    TARGET_OPTIONAL_FIELDS = [
        "full_name",
        "gene_name",
        "aliases",
        "gene_id",
        "uniprot_id",
        "category",
        "description",
    ]

    def __init__(self):
        """初始化验证器"""
        pass

    def validate_pipeline_item(self, item: Dict[str, Any]) -> ValidationResult:
        """
        验证Pipeline数据项

        Args:
            item: Pipeline数据字典

        Returns:
            ValidationResult 对象

        Example:
            >>> validator = DataValidator()
            >>> result = validator.validate_pipeline_item(pipeline_dict)
            >>> if result.is_valid:
            ...     print("有效")
        """
        errors = []
        warnings = []
        missing_fields = []

        # 检查必需字段
        for field in self.PIPELINE_REQUIRED_FIELDS:
            if field not in item or not item[field]:
                missing_fields.append(field)
                errors.append(f"缺少必需字段: {field}")

        # 检查字段类型
        if "drug_code" in item and not isinstance(item["drug_code"], str):
            errors.append("drug_code 必须是字符串")

        if "company_name" in item and not isinstance(item["company_name"], str):
            errors.append("company_name 必须是字符串")

        if "indication" in item and not isinstance(item["indication"], str):
            errors.append("indication 必须是字符串")

        # 检查phase格式
        if "phase" in item and item["phase"]:
            phase_lower = item["phase"].lower()
            valid_phases = ["phase 1", "phase 2", "phase 3", "approved", "discontinued",
                           "preclinical", "registration", "launched"]
            if not any(phase in phase_lower for phase in valid_phases):
                warnings.append(f"未识别的phase格式: {item['phase']}")

        # 检查modality格式
        if "modality" in item and item["modality"]:
            valid_modalities = ["small molecule", "monoclonal antibody", "adc",
                              "car-t", "vaccine", "gene therapy", "cell therapy"]
            if item["modality"].lower() not in [m.lower() for m in valid_modalities]:
                warnings.append(f"未识别的modality: {item['modality']}")

        is_valid = len(errors) == 0 and len(missing_fields) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields
        )

    def validate_publication_item(self, item: Dict[str, Any]) -> ValidationResult:
        """
        验证Publication数据项

        Args:
            item: Publication数据字典

        Returns:
            ValidationResult 对象
        """
        errors = []
        warnings = []
        missing_fields = []

        # 检查必需字段
        for field in self.PUBLICATION_REQUIRED_FIELDS:
            if field not in item or not item[field]:
                missing_fields.append(field)
                errors.append(f"缺少必需字段: {field}")

        # 检查PMID格式（应该是数字）
        if "pmid" in item:
            try:
                pmid_int = int(item["pmid"])
                if pmid_int <= 0:
                    errors.append("PMID 必须是正整数")
            except (ValueError, TypeError):
                errors.append("PMID 格式无效")

        # 检查标题长度
        if "title" in item and item["title"]:
            if len(item["title"]) < 10:
                warnings.append("标题过短，可能不完整")
            elif len(item["title"]) > 1000:
                warnings.append("标题过长，可能包含多余内容")

        # 检查日期格式
        if "pub_date" in item and item["pub_date"]:
            if not self._is_valid_date(item["pub_date"]):
                errors.append("pub_date 格式无效，应为 YYYY-MM-DD")

        is_valid = len(errors) == 0 and len(missing_fields) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields
        )

    def validate_target_item(self, item: Dict[str, Any]) -> ValidationResult:
        """
        验证Target数据项

        Args:
            item: Target数据字典

        Returns:
            ValidationResult 对象
        """
        errors = []
        warnings = []
        missing_fields = []

        # 检查必需字段
        for field in self.TARGET_REQUIRED_FIELDS:
            if field not in item or not item[field]:
                missing_fields.append(field)
                errors.append(f"缺少必需字段: {field}")

        # 检查standard_name格式
        if "standard_name" in item and item["standard_name"]:
            if len(item["standard_name"]) < 2:
                errors.append("standard_name 过短")
            if not any(c.isalpha() for c in item["standard_name"]):
                errors.append("standard_name 必须包含字母")

        # 检查aliases格式
        if "aliases" in item and item["aliases"]:
            if not isinstance(item["aliases"], list):
                errors.append("aliases 必须是列表")
            elif not all(isinstance(alias, str) for alias in item["aliases"]):
                errors.append("aliases 所有元素必须是字符串")

        is_valid = len(errors) == 0 and len(missing_fields) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields
        )

    def _is_valid_date(self, date_str: str) -> bool:
        """
        检查日期格式是否有效

        Args:
            date_str: 日期字符串

        Returns:
            是否有效
        """
        from datetime import datetime

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False

    def validate_batch(
        self,
        items: List[Dict[str, Any]],
        item_type: str = "pipeline"
    ) -> Dict[str, Any]:
        """
        批量验证数据

        Args:
            items: 数据列表
            item_type: 数据类型 ("pipeline", "publication", "target")

        Returns:
            批量验证结果

        Example:
            >>> validator = DataValidator()
            >>> result = validator.validate_batch(pipelines, "pipeline")
            >>> print(result["valid_count"])
            10
            >>> print(result["invalid_count"])
            2
        """
        valid_count = 0
        invalid_count = 0
        all_errors = []

        for item in items:
            if item_type == "pipeline":
                result = self.validate_pipeline_item(item)
            elif item_type == "publication":
                result = self.validate_publication_item(item)
            elif item_type == "target":
                result = self.validate_target_item(item)
            else:
                result = ValidationResult(is_valid=False, errors=[f"未知类型: {item_type}"])

            if result.is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                all_errors.extend(result.errors)

        return {
            "total_count": len(items),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "all_errors": all_errors,
        }


# =====================================================
# 便捷函数
# =====================================================

_validator_instance = None

def get_data_validator() -> DataValidator:
    """获取DataValidator单例"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DataValidator()
    return _validator_instance
