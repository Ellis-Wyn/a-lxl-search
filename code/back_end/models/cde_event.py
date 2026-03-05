"""
=====================================================
CDEEvent ORM 模型（CDE事件表）
=====================================================

药审中心（CDE）受理/审评事件流
- 支持 IND/CTA/NDA/BLA 等事件类型
- 增量更新（first_seen_at, last_seen_at）
- 数据可追溯性（source_urls 存储所有相关URL）
- 关联 Pipeline 模型（通过 applicant 字段）
=====================================================
"""

from sqlalchemy import Column, String, Text, Date, DateTime, Float, Index, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from typing import Optional, Dict, Any, List

from utils.database import Base


class CDEEvent(Base):
    """
    CDE 受理/审评事件表

    核心设计：
    - 唯一标识：acceptance_no（受理号）
    - 双时间戳：first_seen_at（首次发现）+ last_seen_at（最近更新）
    - 数据可追溯性：source_urls 存储所有相关URL（列表页、详情页、附件）
    - 松散关联：通过 applicant 字段与 Pipeline.company_name 关联
    """

    __tablename__ = "cde_events"

    # =====================================================
    # 主键
    # =====================================================
    id = Column(
        String(100),
        primary_key=True,
        comment="主键（使用 acceptance_no）"
    )

    # =====================================================
    # 事件标识
    # =====================================================
    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="事件类型：IND/CTA/NDA/BLA/补充资料"
    )
    acceptance_no = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="受理号（唯一标识）"
    )

    # =====================================================
    # 药物信息
    # =====================================================
    drug_name = Column(
        String(200),
        nullable=False,
        index=True,
        comment="药品名称/通用名/代号"
    )
    drug_type = Column(
        String(50),
        comment="药物类型：化药/生物制品/中药"
    )
    registration_class = Column(
        String(50),
        comment="注册分类：1类/2类/3类等"
    )

    # =====================================================
    # 申请人信息
    # =====================================================
    applicant = Column(
        String(200),
        nullable=False,
        index=True,
        comment="申请人/企业名称（全称）"
    )

    # =====================================================
    # 时间信息
    # =====================================================
    undertake_date = Column(
        Date,
        index=True,
        comment="承办日期（进入CDE中心日期）"
    )
    acceptance_date = Column(
        Date,
        comment="受理日期"
    )
    public_date = Column(
        Date,
        comment="公示日期"
    )

    # =====================================================
    # 审评状态
    # =====================================================
    review_status = Column(
        String(50),
        comment="审评状态：审评中/已批准/已终止"
    )

    # =====================================================
    # 适应症（从详情页提取）
    # =====================================================
    indication = Column(
        Text,
        comment="适应症描述"
    )

    # =====================================================
    # 关联信息
    # =====================================================
    related_target = Column(
        String(100),
        comment="靶点（可通过药物名称匹配）"
    )
    related_company_id = Column(
        String(255),
        comment="关联公司ID（Pipeline.company_name）"
    )

    # =====================================================
    # 原始数据追溯（关键字段）
    # =====================================================
    public_page_url = Column(
        String(500),
        unique=True,
        nullable=False,
        comment="CDE公示页面URL（主入口）"
    )
    source_urls = Column(
        JSON,
        nullable=False,
        comment="所有相关URL数组：[列表页URL, 详情页URL, 附件URLs]"
    )

    # 可选：存储原始HTML快照（用于调试，生产环境可关闭）
    raw_html_snapshot = Column(
        Text,
        nullable=True,
        comment="原始HTML快照（仅用于调试）"
    )

    # =====================================================
    # 爬虫元数据
    # =====================================================
    first_seen_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="首次发现时间（永不变化）"
    )
    last_seen_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
        comment="最近更新时间（每次爬取更新）"
    )
    crawler_run_id = Column(
        String(100),
        comment="关联爬虫执行记录ID"
    )

    # =====================================================
    # 评分字段（复用 scoring_algorithms）
    # =====================================================
    clinical_significance_score = Column(
        Float,
        default=0.0,
        comment="临床显著性得分（0-100）"
    )
    regulatory_priority_score = Column(
        Float,
        default=0.0,
        comment="监管优先级得分（0-100）"
    )

    # =====================================================
    # 状态标记
    # =====================================================
    is_active = Column(
        Boolean,
        default=True,
        index=True,
        comment="是否有效（软删除标记）"
    )

    # =====================================================
    # 约束与索引
    # =====================================================
    __table_args__ = (
        UniqueConstraint('acceptance_no', name='uq_cde_acceptance_no'),
        Index('ix_cde_event_type_applicant', 'event_type', 'applicant'),
        Index('ix_cde_undertake_date', 'undertake_date'),
        {'comment': 'CDE药审中心受理/审评事件表'}
    )

    # =====================================================
    # ORM 方法
    # =====================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            事件数据字典
        """
        return {
            'id': self.id,
            'event_type': self.event_type,
            'acceptance_no': self.acceptance_no,
            'drug_name': self.drug_name,
            'drug_type': self.drug_type,
            'registration_class': self.registration_class,
            'applicant': self.applicant,
            'undertake_date': self.undertake_date.isoformat() if self.undertake_date else None,
            'acceptance_date': self.acceptance_date.isoformat() if self.acceptance_date else None,
            'public_date': self.public_date.isoformat() if self.public_date else None,
            'review_status': self.review_status,
            'indication': self.indication,
            'related_target': self.related_target,
            'public_page_url': self.public_page_url,
            'source_urls': self.source_urls,
            'first_seen_at': self.first_seen_at.isoformat() if self.first_seen_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'clinical_significance_score': self.clinical_significance_score,
            'regulatory_priority_score': self.regulatory_priority_score,
            'is_active': self.is_active,
        }

    def get_source_urls(self) -> List[str]:
        """
        获取所有源URL列表

        Returns:
            URL列表
        """
        if isinstance(self.source_urls, list):
            return self.source_urls
        elif isinstance(self.source_urls, dict):
            # 兼容字典格式
            return list(self.source_urls.values())
        else:
            # 默认返回主URL
            return [self.public_page_url]

    def add_source_url(self, url: str) -> None:
        """
        添加源URL

        Args:
            url: 要添加的URL
        """
        if self.source_urls is None:
            self.source_urls = []

        if isinstance(self.source_urls, list):
            if url not in self.source_urls:
                self.source_urls.append(url)
        elif isinstance(self.source_urls, dict):
            # 字典格式：按类型存储
            self.source_urls[url] = datetime.utcnow().isoformat()

    def get_primary_url(self) -> str:
        """
        获取主要URL

        Returns:
            主要URL（优先返回 public_page_url）
        """
        return self.public_page_url or self.get_source_urls()[0] if self.get_source_urls() else ""

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<CDEEvent(id={self.id}, "
            f"event_type={self.event_type}, "
            f"acceptance_no={self.acceptance_no}, "
            f"drug_name={self.drug_name}, "
            f"applicant={self.applicant})>"
        )

    def __str__(self) -> str:
        """用户友好的字符串表示"""
        return (
            f"{self.drug_name} - {self.event_type} "
            f"({self.applicant}, 受理号: {self.acceptance_no})"
        )


# =====================================================
# 导出
# =====================================================

__all__ = ["CDEEvent"]
