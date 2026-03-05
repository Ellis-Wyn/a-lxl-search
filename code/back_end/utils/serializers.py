"""
=====================================================
统一序列化层
=====================================================

处理 ORM 对象到 JSON 的序列化，解决 UUID、日期等类型的转换问题。

使用方式：
    from utils.serializers import TargetSerializer, PublicationSerializer

    # 单个对象
    data = TargetSerializer.from_orm(target)

    # 列表
    data = [TargetSerializer.from_orm(t) for t in targets]
=====================================================
"""

from typing import List, Optional, Any, Dict
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# =====================================================
# Base Serializer
# =====================================================

class BaseSerializer(BaseModel):
    """序列化器基类，提供通用的序列化方法"""

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True


# =====================================================
# Target Serializers
# =====================================================

class TargetListItemSerializer(BaseSerializer):
    """靶点列表项序列化器"""
    target_id: str = Field(..., description="靶点 UUID")
    standard_name: str = Field(..., description="标准名称")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    gene_id: Optional[str] = Field(None, description="Gene ID")
    uniprot_id: Optional[str] = Field(None, description="UniProt ID")
    category: Optional[str] = Field(None, description="分类")
    description: Optional[str] = Field(None, description="描述")

    @field_validator('target_id', mode='before')
    @classmethod
    def serialize_uuid(cls, value: UUID) -> str:
        """将 UUID 转换为字符串"""
        return str(value) if value else None

    @field_validator('aliases', mode='before')
    @classmethod
    def ensure_list(cls, value: Any) -> List[str]:
        """确保返回列表类型"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]


class TargetDetailSerializer(TargetListItemSerializer):
    """靶点详情序列化器"""
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def serialize_datetime(cls, value: Optional[datetime]) -> Optional[str]:
        """将 datetime 转换为 ISO 格式字符串"""
        return value.isoformat() if value else None


# =====================================================
# Publication Serializers
# =====================================================

class PublicationListItemSerializer(BaseSerializer):
    """文献列表项序列化器"""
    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="标题")
    abstract: Optional[str] = Field(None, description="摘要")
    pub_date: Optional[str] = Field(None, description="发布日期")
    journal: Optional[str] = Field(None, description="期刊")
    publication_type: Optional[str] = Field(None, description="文献类型")
    source_type: Optional[str] = Field(None, description="来源类型")

    @field_validator('pub_date', mode='before')
    @classmethod
    def serialize_date(cls, value: Optional[date]) -> Optional[str]:
        """将 date 转换为 ISO 格式字符串"""
        return value.isoformat() if value else None


class PublicationDetailSerializer(PublicationListItemSerializer):
    """文献详情序列化器"""
    mesh_terms: List[str] = Field(default_factory=list, description="MeSH 主题词")
    clinical_data_tags: List[Dict[str, Any]] = Field(default_factory=list, description="临床数据标签")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")

    @field_validator('mesh_terms', mode='before')
    @classmethod
    def ensure_list(cls, value: Any) -> List[str]:
        """确保返回列表类型"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @field_validator('clinical_data_tags', mode='before')
    @classmethod
    def ensure_dict_list(cls, value: Any) -> List[Dict[str, Any]]:
        """确保返回字典列表"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def serialize_datetime(cls, value: Optional[datetime]) -> Optional[str]:
        """将 datetime 转换为 ISO 格式字符串"""
        return value.isoformat() if value else None


# =====================================================
# Pipeline Serializers
# =====================================================

class PipelineListItemSerializer(BaseSerializer):
    """管线列表项序列化器"""
    pipeline_id: str = Field(..., description="管线 UUID")
    drug_code: str = Field(..., description="药物代码")
    company_name: str = Field(..., description="公司名称")
    indication: str = Field(..., description="适应症")
    phase: str = Field(..., description="阶段")
    phase_raw: Optional[str] = Field(None, description="原始阶段")
    modality: Optional[str] = Field(None, description="药物类型")
    source_url: Optional[str] = Field(None, description="来源 URL")
    status: Optional[str] = Field(None, description="状态")
    first_seen_at: Optional[str] = Field(None, description="首次发现时间")
    last_seen_at: Optional[str] = Field(None, description="最后见到时间")

    @field_validator('pipeline_id', mode='before')
    @classmethod
    def serialize_uuid(cls, value: UUID) -> str:
        """将 UUID 转换为字符串"""
        return str(value) if value else None

    @field_validator('first_seen_at', 'last_seen_at', mode='before')
    @classmethod
    def serialize_datetime(cls, value: Optional[datetime]) -> Optional[str]:
        """将 datetime 转换为 ISO 格式字符串"""
        return value.isoformat() if value else None


# =====================================================
# Statistics Serializers
# =====================================================

class TargetStatsSerializer(BaseSerializer):
    """靶点统计序列化器"""
    total: int = Field(..., description="总数")
    with_publications: int = Field(..., description="有文献的靶点数")
    with_pipelines: int = Field(..., description="有管线的靶点数")
    category_distribution: List[Dict[str, Any]] = Field(default_factory=list, description="分类分布")


class PublicationStatsSerializer(BaseSerializer):
    """文献统计序列化器"""
    total: int = Field(..., description="总数")
    latest_date: Optional[str] = Field(None, description="最新文献日期")
    journal_distribution: List[Dict[str, Any]] = Field(default_factory=list, description="期刊分布")
    type_distribution: List[Dict[str, Any]] = Field(default_factory=list, description="类型分布")


# =====================================================
# Helper Functions
# =====================================================

def serialize_uuid(value: Optional[UUID]) -> Optional[str]:
    """UUID 转字符串辅助函数"""
    return str(value) if value else None


def serialize_datetime(value: Optional[datetime]) -> Optional[str]:
    """datetime 转字符串辅助函数"""
    return value.isoformat() if value else None


def serialize_date(value: Optional[date]) -> Optional[str]:
    """date 转字符串辅助函数"""
    return value.isoformat() if value else None


__all__ = [
    "TargetListItemSerializer",
    "TargetDetailSerializer",
    "PublicationListItemSerializer",
    "PublicationDetailSerializer",
    "PipelineListItemSerializer",
    "TargetStatsSerializer",
    "PublicationStatsSerializer",
    "serialize_uuid",
    "serialize_datetime",
    "serialize_date",
]
