"""
=====================================================
pytest 配置和共享 Fixture
=====================================================

提供测试所需的共享资源和配置：
- 数据库 Session（内存数据库）
- 测试数据工厂
- Mock 对象
=====================================================
"""

import pytest
import os
import sys
from datetime import date, datetime
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.target import Target
from models.publication import Publication
from models.pipeline import Pipeline
from models.relationships import TargetPublication, TargetPipeline
from utils.database import Base


# =====================================================
# 数据库 Fixture
# =====================================================


@pytest.fixture(scope="function")
def db_engine():
    """
    创建内存数据库引擎（每个测试函数独立）

    使用 SQLite 内存数据库，测试完成后自动清理
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # 创建所有表
    Base.metadata.create_all(engine)

    yield engine

    # 清理
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    创建数据库 Session（每个测试函数独立）

    自动回滚所有更改，确保测试隔离
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()

    yield session

    session.rollback()
    session.close()


# =====================================================
# 测试数据 Fixture
# =====================================================


@pytest.fixture
def sample_target(db_session: Session) -> Target:
    """创建示例靶点"""
    target = Target(
        standard_name="EGFR",
        aliases=["ERBB1", "HER1"],
        gene_id="1956",
        uniprot_id="P00533",
        category="Tyrosine Kinase",
        description="Epidermal Growth Factor Receptor"
    )
    db_session.add(target)
    db_session.commit()
    db_session.refresh(target)
    return target


@pytest.fixture
def sample_publication(db_session: Session) -> Publication:
    """创建示例文献"""
    publication = Publication(
        pmid="12345678",
        title="EGFR inhibitor in NSCLC: A phase III trial",
        abstract="This study evaluates the efficacy of EGFR inhibitor in non-small cell lung cancer.",
        pub_date=date(2024, 1, 15),
        journal="Journal of Clinical Oncology",
        publication_type="Clinical Trial",
        authors=["Zhang San", "Li Si", "Wang Wu"],
        mesh_terms=["Carcinoma, Non-Small Cell Lung", "Receptor, Epidermal Growth Factor"],
        clinical_data_tags=["ORR: 65%", "PFS: 12.3 months", "OS: 28.5 months"]
    )
    db_session.add(publication)
    db_session.commit()
    db_session.refresh(publication)
    return publication


@pytest.fixture
def sample_pipeline(db_session: Session) -> Pipeline:
    """创建示例管线"""
    pipeline = Pipeline(
        drug_code="SHR-1210",
        company_name="恒瑞医药",
        indication="非小细胞肺癌",
        phase="Phase 3",
        phase_raw="III期",
        modality="Monoclonal Antibody",
        source_url="https://www.hengrui.com/pipeline.html"
    )
    db_session.add(pipeline)
    db_session.commit()
    db_session.refresh(pipeline)
    return pipeline


@pytest.fixture
def sample_targets(db_session: Session) -> list[Target]:
    """创建多个示例靶点"""
    targets_data = [
        {
            "standard_name": "EGFR",
            "aliases": ["ERBB1", "HER1"],
            "gene_id": "1956",
            "category": "Tyrosine Kinase"
        },
        {
            "standard_name": "HER2",
            "aliases": ["ERBB2"],
            "gene_id": "2064",
            "category": "Tyrosine Kinase"
        },
        {
            "standard_name": "PD-1",
            "aliases": ["PDCD1"],
            "gene_id": "5133",
            "category": "Immune Checkpoint"
        }
    ]

    targets = []
    for data in targets_data:
        target = Target(**data)
        db_session.add(target)
        targets.append(target)

    db_session.commit()
    for target in targets:
        db_session.refresh(target)

    return targets


@pytest.fixture
def sample_pipelines(db_session: Session) -> list[Pipeline]:
    """创建多个示例管线"""
    pipelines_data = [
        {
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "非小细胞肺癌",
            "phase": "Phase 3",
            "modality": "Monoclonal Antibody",
            "source_url": "https://www.hengrui.com/pipeline.html"
        },
        {
            "drug_code": "SHR-1501",
            "company_name": "恒瑞医药",
            "indication": "实体瘤",
            "phase": "Phase 2",
            "modality": "Small Molecule",
            "source_url": "https://www.hengrui.com/pipeline.html"
        },
        {
            "drug_code": "BGB-A322",
            "company_name": "百济神州",
            "indication": "NSCLC",
            "phase": "Phase 3",
            "modality": "Monoclonal Antibody",
            "source_url": "https://www.beigene.com/pipeline.html"
        }
    ]

    pipelines = []
    for data in pipelines_data:
        pipeline = Pipeline(**data)
        db_session.add(pipeline)
        pipelines.append(pipeline)

    db_session.commit()
    for pipeline in pipelines:
        db_session.refresh(pipeline)

    return pipelines


# =====================================================
# 关联数据 Fixture
# =====================================================


@pytest.fixture
def linked_target_publication(
    db_session: Session,
    sample_target: Target,
    sample_publication: Publication
) -> TargetPublication:
    """创建靶点-文献关联"""
    link = TargetPublication(
        target_id=sample_target.target_id,
        pmid=sample_publication.pmid,
        relation_type="focus_on",
        evidence_snippet="This paper focuses on EGFR inhibition"
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)
    return link


@pytest.fixture
def linked_target_pipeline(
    db_session: Session,
    sample_target: Target,
    sample_pipeline: Pipeline
) -> TargetPipeline:
    """创建靶点-管线关联"""
    link = TargetPipeline(
        target_id=sample_target.target_id,
        pipeline_id=sample_pipeline.pipeline_id,
        relation_type="inhibits",
        is_primary=True,
        evidence_snippet="SHR-1210 is a PD-1 inhibitor"
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)
    return link


# =====================================================
# Mock Fixture
# =====================================================


@pytest.fixture
def mock_pubmed_response():
    """Mock PubMed API 响应"""
    return {
        "pmid": "12345678",
        "title": "EGFR inhibitor in NSCLC",
        "abstract": "Test abstract",
        "journal": "J Clin Oncol",
        "pub_date": "2024-01-15",
        "publication_type": "Clinical Trial",
        "authors": ["Zhang San", "Li Si"],
        "mesh_terms": ["Lung Neoplasms"],
        "clinical_data_tags": [{"ORR": "65%"}]
    }


@pytest.fixture
def mock_html_content():
    """Mock HTML 内容（用于爬虫测试）"""
    return """
    <html>
        <body>
            <div class="pipeline-item">
                <h3>SHR-1210</h3>
                <p>适应症：非小细胞肺癌</p>
                <p>阶段：III期</p>
            </div>
            <div class="pipeline-item">
                <h3>SHR-1501</h3>
                <p>适应症：实体瘤</p>
                <p>阶段：II期</p>
            </div>
        </body>
    </html>
    """


# =====================================================
# 配置 Fixture
# =====================================================


@pytest.fixture(autouse=True)
def set_test_settings(monkeypatch):
    """自动应用测试配置（所有测试）"""
    # 设置测试环境变量
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")  # 减少测试日志输出
    monkeypatch.setenv("CRAWLER_ENABLE_CACHE", "false")


# =====================================================
# 辅助函数
# =====================================================


def assert_target_equal(target: Target, expected: dict):
    """断言靶点数据匹配"""
    assert target.standard_name == expected.get("standard_name")
    assert target.aliases == expected.get("aliases", [])
    assert target.gene_id == expected.get("gene_id")
    assert target.uniprot_id == expected.get("uniprot_id")
    assert target.category == expected.get("category")


def assert_publication_equal(pub: Publication, expected: dict):
    """断言文献数据匹配"""
    assert pub.pmid == expected.get("pmid")
    assert pub.title == expected.get("title")
    assert pub.abstract == expected.get("abstract")
    assert pub.journal == expected.get("journal")
    assert pub.publication_type == expected.get("publication_type")


def assert_pipeline_equal(pipeline: Pipeline, expected: dict):
    """断言管线数据匹配"""
    assert pipeline.drug_code == expected.get("drug_code")
    assert pipeline.company_name == expected.get("company_name")
    assert pipeline.indication == expected.get("indication")
    assert pipeline.phase == expected.get("phase")
    assert pipeline.modality == expected.get("modality")
