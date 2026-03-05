"""
=====================================================
数据验证模块（Pydantic）
=====================================================

提供严格的数据验证，确保：
1. API输入数据的安全性
2. 数据格式的一致性
3. 业务规则的验证

使用示例：
    from utils.validators import (
        TargetCreateRequest,
        PipelineCreateRequest,
        PublicationCreateRequest
    )

    # 验证数据
    data = PipelineCreateRequest(**request_data)
    pipeline = data.to_model()
=====================================================
"""

from pydantic import BaseModel, Field, validator, model_validator
from typing import Optional, List
from datetime import datetime
import re
from enum import Enum


# =====================================================
# 枚举类型
# =====================================================

class ModalityType(str, Enum):
    """药物类型"""
    SMALL_MOLECULE = "Small Molecule"
    MONOCLONAL_ANTIBODY = "Monoclonal Antibody"
    ADC = "ADC"
    BISPECIFIC_ANTIBODY = "Bispecific Antibody"
    CAR_T = "CAR-T"
    PROTAC = "PROTAC"
    BI_SPECIFIC = "Bi-specific"
    RNA_THERAPY = "RNA Therapy"
    GENE_THERAPY = "Gene Therapy"
    VACCINE = "Vaccine"
    OTHER = "Other"


class PhaseType(str, Enum):
    """研发阶段"""
    PRECLINICAL = "preclinical"
    PHASE_1 = "Phase 1"
    PHASE_2 = "Phase 2"
    PHASE_3 = "Phase 3"
    FILING = "filing"
    APPROVED = "approved"


class RelationType(str, Enum):
    """靶点关系类型"""
    TARGETS = "targets"
    INHIBITS = "inhibits"
    ANTIBODY_TO = "antibody_to"
    AGONIST_OF = "agonist_of"
    ACTIVATES = "activates"
    BINDS_TO = "binds_to"
    DEGRADES = "degrades"


# =====================================================
# Target 验证模型
# =====================================================

class TargetCreateRequest(BaseModel):
    """靶点创建请求验证"""

    standard_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="标准名称，如 EGFR",
        example="EGFR"
    )
    aliases: Optional[List[str]] = Field(
        default=None,
        description="别名列表",
        example=["ERBB1", "HER1"]
    )
    gene_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="NCBI Gene ID",
        example="1956"
    )
    uniprot_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="UniProt ID",
        example="P00533"
    )
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="靶点分类",
        example="Tyrosine Kinase"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="靶点描述"
    )

    @validator('standard_name')
    def validate_standard_name(cls, v):
        """验证标准名称格式"""
        if not re.match(r'^[A-Za-z0-9\-]+$', v):
            raise ValueError('标准名称只能包含字母、数字和连字符')
        if not v[0].isalpha():
            raise ValueError('标准名称必须以字母开头')
        return v

    @validator('aliases')
    def validate_aliases(cls, v):
        """验证别名列表"""
        if v is not None:
            # 去重
            unique_aliases = list(set(v))
            # 检查格式
            for alias in unique_aliases:
                if not re.match(r'^[A-Za-z0-9\-]+$', alias):
                    raise ValueError(f'别名 "{alias}" 格式无效，只能包含字母、数字和连字符')
            return unique_aliases
        return v

    @validator('gene_id')
    def validate_gene_id(cls, v):
        """验证Gene ID格式"""
        if v is not None and not v.isdigit():
            raise ValueError('Gene ID 必须是数字')
        return v

    def to_dict(self) -> dict:
        """转换为字典"""
        return self.dict(exclude_unset=True)

    def to_model(self):
        """转换为ORM模型（需要在使用时导入Target类）"""
        from models.target import Target
        return Target(
            standard_name=self.standard_name,
            aliases=self.aliases or [],
            gene_id=self.gene_id,
            uniprot_id=self.uniprot_id,
            category=self.category,
            description=self.description
        )


class TargetUpdateRequest(BaseModel):
    """靶点更新请求验证"""

    standard_name: Optional[str] = Field(None, min_length=1, max_length=100)
    aliases: Optional[List[str]] = None
    gene_id: Optional[str] = Field(None, min_length=1, max_length=50)
    uniprot_id: Optional[str] = Field(None, min_length=1, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)

    @validator('standard_name')
    def validate_standard_name(cls, v):
        if v is not None:
            if not re.match(r'^[A-Za-z0-9\-]+$', v):
                raise ValueError('标准名称只能包含字母、数字和连字符')
        return v


# =====================================================
# Publication 验证模型
# =====================================================

class PublicationCreateRequest(BaseModel):
    """文献创建请求验证"""

    pmid: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="PubMed ID",
        example="12345678"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="文献标题"
    )
    abstract: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="文献摘要"
    )
    pub_date: Optional[datetime] = Field(
        default=None,
        description="发布日期"
    )
    journal: Optional[str] = Field(
        default=None,
        max_length=200,
        description="期刊名称"
    )
    publication_type: Optional[str] = Field(
        default=None,
        max_length=100,
        description="文献类型"
    )
    authors: Optional[List[str]] = Field(
        default=None,
        description="作者列表"
    )
    mesh_terms: Optional[List[str]] = Field(
        default=None,
        description="MeSH主题词"
    )
    clinical_data_tags: Optional[List[str]] = Field(
        default=None,
        description="临床数据标签",
        example=["ORR: 45%", "PFS: 6.8 months"]
    )

    @validator('pmid')
    def validate_pmid(cls, v):
        """验证PMID格式"""
        if not v.isdigit():
            raise ValueError('PMID 必须是数字')
        if len(v) > 10:
            raise ValueError('PMID 长度不能超过10位')
        return v

    @validator('authors')
    def validate_authors(cls, v):
        """验证作者列表"""
        if v is not None:
            # 去重
            unique_authors = list(set(v))
            # 检查格式
            for author in unique_authors:
                if not author.strip():
                    raise ValueError('作者名不能为空')
            return unique_authors
        return v

    def to_dict(self) -> dict:
        """转换为字典"""
        return self.dict(exclude_unset=True)

    def to_model(self):
        """转换为ORM模型"""
        from models.publication import Publication
        return Publication(
            pmid=self.pmid,
            title=self.title,
            abstract=self.abstract,
            pub_date=self.pub_date,
            journal=self.journal,
            publication_type=self.publication_type,
            authors=self.authors,
            mesh_terms=self.mesh_terms,
            clinical_data_tags=self.clinical_data_tags
        )


# =====================================================
# Pipeline 验证模型
# =====================================================

class PipelineCreateRequest(BaseModel):
    """管线创建请求验证"""

    drug_code: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="药物代码，如 SHR-1210",
        example="SHR-1210"
    )
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="公司名称",
        example="恒瑞医药"
    )
    indication: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="适应症",
        example="非小细胞肺癌"
    )
    phase: str = Field(
        ...,
        description="研发阶段",
        example="Phase 3"
    )
    phase_raw: Optional[str] = Field(
        default=None,
        max_length=255,
        description="原始阶段名称（官网原文）"
    )
    modality: Optional[str] = Field(
        default=None,
        max_length=100,
        description="药物类型"
    )
    source_url: str = Field(
        ...,
        description="来源URL",
        example="https://www.hengrui.com/RD/pipeline.html"
    )
    status: Optional[str] = Field(
        default="active",
        description="状态",
        pattern=r'^(active|discontinued)$'
    )
    is_combination: Optional[bool] = Field(
        default=False,
        description="是否联合用药"
    )
    combination_drugs: Optional[List[str]] = Field(
        default=None,
        description="联合用药列表"
    )

    @validator('drug_code')
    def validate_drug_code(cls, v):
        """验证药物代码格式"""
        if not re.match(r'^[A-Z0-9\-]+$', v):
            raise ValueError('药物代码只能包含大写字母、数字和连字符')
        if not v[0].isalpha():
            raise ValueError('药物代码必须以字母开头')
        return v

    @validator('phase')
    def validate_phase(cls, v):
        """验证阶段格式"""
        valid_phases = ['preclinical', 'Phase 1', 'Phase 2', 'Phase 3', 'filing', 'approved']
        if v not in valid_phases:
            raise ValueError(f'无效的阶段，必须是: {", ".join(valid_phases)}')
        return v

    @validator('source_url')
    def validate_source_url(cls, v):
        """验证URL格式"""
        if not re.match(r'^https?://', v):
            raise ValueError('来源URL必须以 http:// 或 https:// 开头')
        return v

    @validator('combination_drugs')
    def validate_combination_drugs(cls, v):
        """验证联合用药列表"""
        if v is not None:
            # 去重
            unique_drugs = list(set(v))
            # 检查格式
            for drug in unique_drugs:
                if not re.match(r'^[A-Z0-9\-]+$', drug):
                    raise ValueError(f'联合药物 "{drug}" 格式无效')
            if len(unique_drugs) < 2:
                raise ValueError('联合用药列表至少需要2个药物')
            return unique_drugs
        return v

    @model_validator(mode='after')
    def validate_combination_logic(self):
        """验证联合用药逻辑"""
        if self.is_combination and not self.combination_drugs:
            raise ValueError('is_combination=True 时必须提供 combination_drugs')
        return self

    def to_dict(self) -> dict:
        """转换为字典"""
        return self.dict(exclude_unset=True)

    def to_model(self):
        """转换为ORM模型"""
        from models.pipeline import Pipeline
        import json

        return Pipeline(
            drug_code=self.drug_code,
            company_name=self.company_name,
            indication=self.indication,
            phase=self.phase,
            phase_raw=self.phase_raw,
            modality=self.modality,
            source_url=self.source_url,
            status=self.status,
            is_combination=self.is_combination,
            combination_drugs=json.dumps(self.combination_drugs) if self.combination_drugs else None
        )


class PipelineUpdateRequest(BaseModel):
    """管线更新请求验证"""

    phase: Optional[str] = None
    indication: Optional[str] = Field(None, min_length=1, max_length=1000)
    status: Optional[str] = Field(None, pattern=r'^(active|discontinued)$')
    is_combination: Optional[bool] = None
    combination_drugs: Optional[List[str]] = None

    @validator('phase')
    def validate_phase(cls, v):
        if v is not None:
            valid_phases = ['preclinical', 'Phase 1', 'Phase 2', 'Phase 3', 'filing', 'approved']
            if v not in valid_phases:
                raise ValueError(f'无效的阶段，必须是: {", ".join(valid_phases)}')
        return v

    @validator('combination_drugs')
    def validate_combination_drugs(cls, v):
        if v is not None:
            unique_drugs = list(set(v))
            for drug in unique_drugs:
                if not re.match(r'^[A-Z0-9\-]+$', drug):
                    raise ValueError(f'联合药物 "{drug}" 格式无效')
            return unique_drugs
        return v


# =====================================================
# Target-Publication 关联验证
# =====================================================

class TargetPublicationLinkRequest(BaseModel):
    """靶点-文献关联请求验证"""

    target_id: str = Field(..., description="靶点UUID")
    pmid: str = Field(..., min_length=1, max_length=20, description="文献PMID")
    relation_type: Optional[str] = Field(
        default="mentioned_in",
        description="关系类型"
    )
    evidence_snippet: Optional[str] = Field(
        default=None,
        max_length=500,
        description="证据片段"
    )

    @validator('pmid')
    def validate_pmid(cls, v):
        if not v.isdigit():
            raise ValueError('PMID 必须是数字')
        return v

    @validator('relation_type')
    def validate_relation_type(cls, v):
        valid_types = ['mentioned_in', 'focus_on']
        if v and v not in valid_types:
            raise ValueError(f'关系类型必须是: {", ".join(valid_types)}')
        return v

    def to_dict(self) -> dict:
        """转换为字典"""
        return self.dict(exclude_unset=True)


# =====================================================
# Target-Pipeline 关联验证
# =====================================================

class TargetPipelineLinkRequest(BaseModel):
    """靶点-管线关联请求验证"""

    target_id: str = Field(..., description="靶点UUID")
    pipeline_id: str = Field(..., description="管线UUID")
    relation_type: Optional[str] = Field(
        default="targets",
        description="作用关系"
    )
    evidence_snippet: Optional[str] = Field(
        default=None,
        max_length=500,
        description="证据片段"
    )
    is_primary: Optional[bool] = Field(
        default=False,
        description="是否主靶点"
    )

    @validator('relation_type')
    def validate_relation_type(cls, v):
        if v:
            valid_types = ['targets', 'inhibits', 'antibody_to', 'agonist_of', 'activates', 'binds_to', 'degrades']
            if v not in valid_types:
                raise ValueError(f'作用关系必须是: {", ".join(valid_types)}')
        return v

    def to_dict(self) -> dict:
        """转换为字典"""
        return self.dict(exclude_unset=True)


# =====================================================
# 导出
# =====================================================

__all__ = [
    # 枚举
    "ModalityType",
    "PhaseType",
    "RelationType",
    # Target
    "TargetCreateRequest",
    "TargetUpdateRequest",
    # Publication
    "PublicationCreateRequest",
    # Pipeline
    "PipelineCreateRequest",
    "PipelineUpdateRequest",
    # 关联
    "TargetPublicationLinkRequest",
    "TargetPipelineLinkRequest",
]
