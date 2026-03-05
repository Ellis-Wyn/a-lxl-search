"""
=====================================================
关联表 ORM 模型
=====================================================

两张关联表：
1. Target_Publication：靶点-文献关联
2. Target_Pipeline：靶点-管线关联

核心价值：
- 建立证据链（evidence_snippet）
- 支持多对多关系
- 记录关系类型（抑制/激活/结合等）
=====================================================
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from utils.database import Base


class TargetPublication(Base):
    """
    靶点-文献关联表

    核心设计：
    - 联合主键：(target_id, pmid)
    - relation_type：mentioned_in（顺带提到）/ focus_on（主要研究）
    - evidence_snippet：原文片段，支持可解释性
    """

    __tablename__ = "target_publication"

    # =====================================================
    # 联合主键
    # =====================================================
    target_id = Column(
        UUID(as_uuid=True),
        ForeignKey("target.target_id", ondelete="CASCADE"),
        primary_key=True,
        comment="靶点ID"
    )
    pmid = Column(
        String(20),
        ForeignKey("publication.pmid", ondelete="CASCADE"),
        primary_key=True,
        comment="文献PMID"
    )

    # =====================================================
    # 关系类型
    # =====================================================
    relation_type = Column(
        String(50),
        index=True,
        comment="关系类型：mentioned_in/focus_on"
    )

    # =====================================================
    # 证据片段
    # =====================================================
    evidence_snippet = Column(Text, comment="原文片段：在哪句话提到该靶点")

    # =====================================================
    # 来源
    # =====================================================
    source = Column(String(255), comment="来源：查询式/抓取时间")

    # =====================================================
    # 时间戳
    # =====================================================
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # =====================================================
    # 关系（ORM 关联）
    # =====================================================
    target = relationship("Target", back_populates="publications")
    publication = relationship("Publication", back_populates="targets")

    # =====================================================
    # 实用方法
    # =====================================================

    def to_dict(self) -> dict:
        """
        转换为字典（用于API返回）

        返回：
            dict: 关联信息字典
        """
        return {
            "target_id": str(self.target_id),
            "pmid": self.pmid,
            "relation_type": self.relation_type,
            "evidence_snippet": self.evidence_snippet,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # 关联对象
            "target_standard_name": self.target.standard_name if self.target else None,
            "publication_title": self.publication.title if self.publication else None,
        }

    def __repr__(self) -> str:
        return f"<TargetPublication({self.target_id} <-> {self.pmid}, {self.relation_type})>"

    def __str__(self) -> str:
        return f"{self.target.standard_name if self.target else '?'} -> {self.pmid}"


class TargetPipeline(Base):
    """
    靶点-管线关联表

    核心设计：
    - 联合主键：(target_id, pipeline_id)
    - relation_type：targets/inhibits/antibody_to/agonist_of/activates/binds_to
    - is_primary：多靶点药物时标识主靶点
    - source_url：关系级来源（官网哪句话提到）
    """

    __tablename__ = "target_pipeline"

    # =====================================================
    # 联合主键
    # =====================================================
    target_id = Column(
        UUID(as_uuid=True),
        ForeignKey("target.target_id", ondelete="CASCADE"),
        primary_key=True,
        comment="靶点ID"
    )
    pipeline_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pipeline.pipeline_id", ondelete="CASCADE"),
        primary_key=True,
        comment="管线ID"
    )

    # =====================================================
    # 关系类型
    # =====================================================
    relation_type = Column(
        String(50),
        index=True,
        comment="作用关系：targets/inhibits/antibody_to/agonist_of/activates/binds_to"
    )

    # =====================================================
    # 证据片段
    # =====================================================
    evidence_snippet = Column(Text, comment="原文片段")

    # =====================================================
    # 来源（关系级）
    # =====================================================
    source_url = Column(Text, comment="关系级来源URL")

    # =====================================================
    # 是否主靶点（V1：多靶点药物时标识）
    # =====================================================
    is_primary = Column(
        Boolean,
        default=False,
        index=True,
        comment="是否主靶点（多靶点药物）"
    )

    # =====================================================
    # 时间戳
    # =====================================================
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # =====================================================
    # 关系（ORM 关联）
    # =====================================================
    target = relationship("Target", back_populates="pipelines")
    pipeline = relationship("Pipeline", back_populates="targets")

    # =====================================================
    # 实用方法
    # =====================================================

    def get_relation_description(self) -> str:
        """
        获取关系类型的中文描述

        返回：
            str: 中文描述
        """
        relation_map = {
            "targets": "针对",
            "inhibits": "抑制",
            "antibody_to": "抗体结合",
            "agonist_of": "激动",
            "activates": "激活",
            "binds_to": "结合",
            "degrades": "降解"
        }

        return relation_map.get(self.relation_type, self.relation_type)

    def to_dict(self) -> dict:
        """
        转换为字典（用于API返回）

        返回：
            dict: 关联信息字典
        """
        return {
            "target_id": str(self.target_id),
            "pipeline_id": str(self.pipeline_id),
            "relation_type": self.relation_type,
            "relation_description": self.get_relation_description(),
            "evidence_snippet": self.evidence_snippet,
            "source_url": self.source_url,
            "is_primary": self.is_primary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # 关联对象
            "target_standard_name": self.target.standard_name if self.target else None,
            "pipeline_drug_code": self.pipeline.drug_code if self.pipeline else None,
            "pipeline_company": self.pipeline.company_name if self.pipeline else None,
        }

    def __repr__(self) -> str:
        return f"<TargetPipeline({self.target_id} <-> {self.pipeline_id}, {self.relation_type})>"

    def __str__(self) -> str:
        target_name = self.target.standard_name if self.target else "?"
        pipeline_name = f"{self.pipeline.drug_code}" if self.pipeline else "?"
        return f"{target_name} {self.get_relation_description()} {pipeline_name}"
