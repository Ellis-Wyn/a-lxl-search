"""
=====================================================
数据模型包
=====================================================

导出所有ORM模型
=====================================================
"""

from .target import Target
from .publication import Publication
from .pipeline import Pipeline
from .relationships import TargetPublication, TargetPipeline
from .crawler_execution_log import CrawlerExecutionLog
from .crawler_statistics import CrawlerStatistics
from .cde_event import CDEEvent

__all__ = [
    "Target",
    "Publication",
    "Pipeline",
    "TargetPublication",
    "TargetPipeline",
    "CrawlerExecutionLog",
    "CrawlerStatistics",
    "CDEEvent",
]


# =====================================================
# 模型工厂函数（便捷创建）
# =====================================================

def create_target(
    standard_name: str,
    aliases: list = None,
    gene_id: str = None,
    uniprot_id: str = None,
    category: str = None,
    description: str = None
) -> Target:
    """
    创建靶点对象

    参数：
        standard_name: 标准名称（必填）
        aliases: 别名数组
        gene_id: Gene ID
        uniprot_id: UniProt ID
        category: 分类
        description: 描述

    返回：
        Target: 靶点对象（未保存到数据库）
    """
    return Target(
        standard_name=standard_name,
        aliases=aliases or [],
        gene_id=gene_id,
        uniprot_id=uniprot_id,
        category=category,
        description=description
    )


def create_publication(
    pmid: str,
    title: str,
    abstract: str = None,
    pub_date = None,
    journal: str = None,
    publication_type: str = None
) -> Publication:
    """
    创建文献对象

    参数：
        pmid: PubMed ID（必填）
        title: 标题（必填）
        abstract: 摘要
        pub_date: 发布日期
        journal: 期刊名
        publication_type: 文献类型

    返回：
        Publication: 文献对象（未保存到数据库）
    """
    return Publication(
        pmid=pmid,
        title=title,
        abstract=abstract,
        pub_date=pub_date,
        journal=journal,
        publication_type=publication_type
    )


def create_pipeline(
    drug_code: str,
    company_name: str,
    indication: str,
    phase: str,
    source_url: str,
    modality: str = None,
    phase_raw: str = None
) -> Pipeline:
    """
    创建管线对象

    参数：
        drug_code: 药物代号（必填）
        company_name: 公司名称（必填）
        indication: 适应症（必填）
        phase: 阶段（必填）
        source_url: 来源URL（必填）
        modality: 药物类型
        phase_raw: 原始阶段名称

    返回：
        Pipeline: 管线对象（未保存到数据库）
    """
    return Pipeline(
        drug_code=drug_code,
        company_name=company_name,
        indication=indication,
        phase=phase,
        source_url=source_url,
        modality=modality,
        phase_raw=phase_raw
    )


def link_target_publication(
    target: Target,
    publication: Publication,
    relation_type: str = "mentioned_in",
    evidence_snippet: str = None,
    source: str = None
) -> TargetPublication:
    """
    创建靶点-文献关联

    参数：
        target: 靶点对象
        publication: 文献对象
        relation_type: 关系类型
        evidence_snippet: 证据片段
        source: 来源

    返回：
        TargetPublication: 关联对象（未保存到数据库）
    """
    return TargetPublication(
        target_id=target.target_id,
        pmid=publication.pmid,
        relation_type=relation_type,
        evidence_snippet=evidence_snippet,
        source=source
    )


def link_target_pipeline(
    target: Target,
    pipeline: Pipeline,
    relation_type: str = "targets",
    evidence_snippet: str = None,
    source_url: str = None,
    is_primary: bool = False
) -> TargetPipeline:
    """
    创建靶点-管线关联

    参数：
        target: 靶点对象
        pipeline: 管线对象
        relation_type: 关系类型
        evidence_snippet: 证据片段
        source_url: 来源URL
        is_primary: 是否主靶点

    返回：
        TargetPipeline: 关联对象（未保存到数据库）
    """
    return TargetPipeline(
        target_id=target.target_id,
        pipeline_id=pipeline.pipeline_id,
        relation_type=relation_type,
        evidence_snippet=evidence_snippet,
        source_url=source_url,
        is_primary=is_primary
    )


def create_cde_event(
    acceptance_no: str,
    event_type: str,
    drug_name: str,
    applicant: str,
    public_page_url: str,
    drug_type: str = None,
    registration_class: str = None,
    indication: str = None,
    undertake_date = None,
    source_urls: list = None
) -> CDEEvent:
    """
    创建CDE事件对象

    参数：
        acceptance_no: 受理号（必填）
        event_type: 事件类型（必填）IND/CTA/NDA/BLA
        drug_name: 药品名称（必填）
        applicant: 申请人（必填）
        public_page_url: 公示页面URL（必填）
        drug_type: 药物类型（化药/生物制品/中药）
        registration_class: 注册分类
        indication: 适应症
        undertake_date: 承办日期
        source_urls: 所有相关URL数组

    返回：
        CDEEvent: CDE事件对象（未保存到数据库）
    """
    return CDEEvent(
        id=acceptance_no,  # 使用 acceptance_no 作为主键
        acceptance_no=acceptance_no,
        event_type=event_type,
        drug_name=drug_name,
        applicant=applicant,
        public_page_url=public_page_url,
        drug_type=drug_type,
        registration_class=registration_class,
        indication=indication,
        undertake_date=undertake_date,
        source_urls=source_urls or [public_page_url]
    )


# =====================================================
# 导出工厂函数
# =====================================================

__all__.extend([
    "create_target",
    "create_publication",
    "create_pipeline",
    "create_cde_event",
    "link_target_publication",
    "link_target_pipeline",
])
