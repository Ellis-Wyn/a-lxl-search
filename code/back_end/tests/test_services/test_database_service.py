"""
=====================================================
DatabaseService 单元测试
=====================================================

测试覆盖：
- CRUD 操作（创建、查询、更新）
- 事务管理和错误处理
- 重试机制
- 关联表操作
=====================================================
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from services.database_service import DatabaseService, get_db_service
from models.target import Target
from models.publication import Publication
from models.pipeline import Pipeline
from models.relationships import TargetPublication, TargetPipeline


class TestDatabaseService:
    """DatabaseService 测试类"""

    def test_create_target_success(self, db_session: Session):
        """测试成功创建靶点"""
        service = DatabaseService()
        service._db = db_session

        target_data = {
            "standard_name": "EGFR",
            "aliases": ["ERBB1", "HER1"],
            "gene_id": "1956",
            "category": "Tyrosine Kinase"
        }

        target = service.create_target(target_data)

        assert target.standard_name == "EGFR"
        assert target.aliases == ["ERBB1", "HER1"]
        assert target.gene_id == "1956"
        assert target.target_id is not None

    def test_create_target_duplicate(self, db_session: Session):
        """测试创建重复靶点"""
        service = DatabaseService()
        service._db = db_session

        # 创建第一个靶点
        service.create_target({"standard_name": "EGFR"})

        # 尝试创建重复靶点
        with pytest.raises(IntegrityError):
            service.create_target({"standard_name": "EGFR"})

    def test_create_publication_success(self, db_session: Session):
        """测试成功创建文献"""
        service = DatabaseService()
        service._db = db_session

        pub_data = {
            "pmid": "12345678",
            "title": "Test Article",
            "abstract": "Test abstract",
            "journal": "Test Journal",
            "publication_type": "Clinical Trial"
        }

        publication = service.create_publication(pub_data)

        assert publication.pmid == "12345678"
        assert publication.title == "Test Article"
        assert publication.abstract == "Test abstract"

    def test_create_publication_update_existing(self, db_session: Session):
        """测试更新已存在的文献"""
        service = DatabaseService()
        service._db = db_session

        # 创建初始文献
        pub_data = {
            "pmid": "12345678",
            "title": "Original Title"
        }
        service.create_publication(pub_data)

        # 更新文献
        updated_data = {
            "pmid": "12345678",
            "title": "Updated Title",
            "abstract": "New abstract"
        }
        publication = service.create_publication(updated_data)

        assert publication.title == "Updated Title"
        assert publication.abstract == "New abstract"

    def test_create_pipeline_success(self, db_session: Session):
        """测试成功创建管线"""
        service = DatabaseService()
        service._db = db_session

        pipeline_data = {
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "非小细胞肺癌",
            "phase": "Phase 3",
            "source_url": "https://example.com"
        }

        pipeline = service.create_pipeline(pipeline_data)

        assert pipeline.drug_code == "SHR-1210"
        assert pipeline.company_name == "恒瑞医药"
        assert pipeline.indication == "非小细胞肺癌"
        assert pipeline.phase == "Phase 3"

    def test_create_pipeline_duplicate(self, db_session: Session):
        """测试创建重复管线"""
        service = DatabaseService()
        service._db = db_session

        pipeline_data = {
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "非小细胞肺癌",
            "phase": "Phase 3",
            "source_url": "https://example.com"
        }

        # 创建第一个管线
        service.create_pipeline(pipeline_data)

        # 尝试创建相同管线
        with pytest.raises(IntegrityError):
            service.create_pipeline(pipeline_data)

    def test_get_target_by_name(self, db_session: Session):
        """测试根据标准名称查询靶点"""
        service = DatabaseService()
        service._db = db_session

        # 创建靶点
        service.create_target({"standard_name": "EGFR"})

        # 查询
        target = service.get_target_by_name("EGFR")

        assert target is not None
        assert target.standard_name == "EGFR"

    def test_get_target_by_name_not_found(self, db_session: Session):
        """测试查询不存在的靶点"""
        service = DatabaseService()
        service._db = db_session

        target = service.get_target_by_name("NONEXISTENT")

        assert target is None

    def test_get_target_by_id(self, db_session: Session):
        """测试根据 ID 查询靶点"""
        service = DatabaseService()
        service._db = db_session

        # 创建靶点
        created = service.create_target({"standard_name": "EGFR"})

        # 查询
        target = service.get_target_by_id(created.target_id)

        assert target is not None
        assert target.standard_name == "EGFR"
        assert target.target_id == created.target_id

    def test_search_targets(self, db_session: Session):
        """测试搜索靶点"""
        service = DatabaseService()
        service._db = db_session

        # 创建多个靶点
        service.create_target({"standard_name": "EGFR"})
        service.create_target({"standard_name": "HER2"})
        service.create_target({"standard_name": "PD-1"})

        # 搜索
        results = service.search_targets("EG")

        assert len(results) >= 1
        assert any(t.standard_name == "EGFR" for t in results)

    def test_get_publication_by_pmid(self, db_session: Session):
        """测试根据 PMID 查询文献"""
        service = DatabaseService()
        service._db = db_session

        # 创建文献
        service.create_publication({
            "pmid": "12345678",
            "title": "Test Article"
        })

        # 查询
        publication = service.get_publication_by_pmid("12345678")

        assert publication is not None
        assert publication.pmid == "12345678"

    def test_get_publications_by_target(self, db_session: Session):
        """测试获取靶点相关文献"""
        service = DatabaseService()
        service._db = db_session

        # 创建靶点和文献
        target = service.create_target({"standard_name": "EGFR"})
        pub1 = service.create_publication({
            "pmid": "11111111",
            "title": "Article 1",
            "pub_date": "2024-01-01"
        })
        pub2 = service.create_publication({
            "pmid": "22222222",
            "title": "Article 2",
            "pub_date": "2024-01-15"
        })

        # 创建关联
        service.link_target_publication(target.target_id, pub1.pmid)
        service.link_target_publication(target.target_id, pub2.pmid)

        # 查询
        publications = service.get_publications_by_target(target.target_id)

        assert len(publications) == 2
        # 应该按日期降序排序
        assert publications[0].pmid == "22222222"

    def test_get_pipeline_by_id(self, db_session: Session):
        """测试根据 ID 查询管线"""
        service = DatabaseService()
        service._db = db_session

        # 创建管线
        created = service.create_pipeline({
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "非小细胞肺癌",
            "phase": "Phase 3",
            "source_url": "https://example.com"
        })

        # 查询
        pipeline = service.get_pipeline_by_id(created.pipeline_id)

        assert pipeline is not None
        assert pipeline.drug_code == "SHR-1210"

    def test_get_pipelines_by_company(self, db_session: Session):
        """测试获取公司管线"""
        service = DatabaseService()
        service._db = db_session

        # 创建同一公司的多个管线
        service.create_pipeline({
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "肺癌",
            "phase": "Phase 3",
            "source_url": "https://example.com"
        })
        service.create_pipeline({
            "drug_code": "SHR-1501",
            "company_name": "恒瑞医药",
            "indication": "实体瘤",
            "phase": "Phase 2",
            "source_url": "https://example.com"
        })

        # 查询
        pipelines = service.get_pipelines_by_company("恒瑞医药")

        assert len(pipelines) == 2
        assert any(p.drug_code == "SHR-1210" for p in pipelines)
        assert any(p.drug_code == "SHR-1501" for p in pipelines)

    def test_get_pipelines_by_target(self, db_session: Session):
        """测试获取靶点相关管线"""
        service = DatabaseService()
        service._db = db_session

        # 创建靶点和管线
        target = service.create_target({"standard_name": "EGFR"})
        pipeline1 = service.create_pipeline({
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "肺癌",
            "phase": "Phase 3",
            "source_url": "https://example.com"
        })
        pipeline2 = service.create_pipeline({
            "drug_code": "BGB-A322",
            "company_name": "百济神州",
            "indication": "肺癌",
            "phase": "Phase 3",
            "source_url": "https://example.com"
        })

        # 创建关联
        service.link_target_pipeline(target.target_id, pipeline1.pipeline_id)
        service.link_target_pipeline(target.target_id, pipeline2.pipeline_id)

        # 查询
        pipelines = service.get_pipelines_by_target(target.target_id)

        assert len(pipelines) == 2

    def test_link_target_publication(self, db_session: Session):
        """测试关联靶点和文献"""
        service = DatabaseService()
        service._db = db_session

        target = service.create_target({"standard_name": "EGFR"})
        publication = service.create_publication({
            "pmid": "12345678",
            "title": "Test Article"
        })

        # 创建关联
        link = service.link_target_publication(
            target_id=target.target_id,
            pmid=publication.pmid,
            relation_type="focus_on",
            evidence_snippet="Test evidence"
        )

        assert link.target_id == target.target_id
        assert link.pmid == publication.pmid
        assert link.relation_type == "focus_on"
        assert link.evidence_snippet == "Test evidence"

    def test_link_target_publication_duplicate(self, db_session: Session):
        """测试重复关联（应返回已存在的关联）"""
        service = DatabaseService()
        service._db = db_session

        target = service.create_target({"standard_name": "EGFR"})
        publication = service.create_publication({
            "pmid": "12345678",
            "title": "Test Article"
        })

        # 创建关联
        link1 = service.link_target_publication(target.target_id, publication.pmid)

        # 再次关联（应返回已存在的关联）
        link2 = service.link_target_publication(target.target_id, publication.pmid)

        assert link1.target_id == link2.target_id
        assert link1.pmid == link2.pmid

    def test_link_target_pipeline(self, db_session: Session):
        """测试关联靶点和管线"""
        service = DatabaseService()
        service._db = db_session

        target = service.create_target({"standard_name": "EGFR"})
        pipeline = service.create_pipeline({
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "肺癌",
            "phase": "Phase 3",
            "source_url": "https://example.com"
        })

        # 创建关联
        link = service.link_target_pipeline(
            target_id=target.target_id,
            pipeline_id=pipeline.pipeline_id,
            relation_type="inhibits",
            is_primary=True
        )

        assert link.target_id == target.target_id
        assert link.pipeline_id == pipeline.pipeline_id
        assert link.relation_type == "inhibits"
        assert link.is_primary is True

    def test_link_target_pipeline_duplicate(self, db_session: Session):
        """测试重复关联（应返回已存在的关联）"""
        service = DatabaseService()
        service._db = db_session

        target = service.create_target({"standard_name": "EGFR"})
        pipeline = service.create_pipeline({
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "肺癌",
            "phase": "Phase 3",
            "source_url": "https://example.com"
        })

        # 创建关联
        link1 = service.link_target_pipeline(target.target_id, pipeline.pipeline_id)

        # 再次关联
        link2 = service.link_target_pipeline(target.target_id, pipeline.pipeline_id)

        assert link1.target_id == link2.target_id
        assert link1.pipeline_id == link2.pipeline_id

    def test_context_manager(self, db_session: Session):
        """测试上下文管理器"""
        with DatabaseService() as service:
            service._db = db_session

            target = service.create_target({"standard_name": "EGFR"})

            assert target.standard_name == "EGFR"

        # 上下文退出后，数据库会话应该关闭
        # 注意：这里不能直接测试 db_session 是否关闭，因为测试 fixture 会管理它

    def test_get_db_service_singleton(self, db_session: Session):
        """测试 DatabaseService 单例"""
        service1 = get_db_service()
        service2 = get_db_service()

        # 应该返回同一个实例
        assert service1 is service2

    def test_get_all_targets(self, db_session: Session):
        """测试获取所有靶点"""
        service = DatabaseService()
        service._db = db_session

        # 创建多个靶点
        service.create_target({"standard_name": "EGFR"})
        service.create_target({"standard_name": "HER2"})
        service.create_target({"standard_name": "PD-1"})

        # 获取所有
        targets = service.get_all_targets()

        assert len(targets) == 3

    def test_get_all_targets_with_limit(self, db_session: Session):
        """测试限制返回数量"""
        service = DatabaseService()
        service._db = db_session

        # 创建多个靶点
        for i in range(10):
            service.create_target({"standard_name": f"TARGET-{i}"})

        # 限制返回 5 个
        targets = service.get_all_targets(limit=5)

        assert len(targets) == 5

    def test_search_targets_with_limit(self, db_session: Session):
        """测试搜索限制返回数量"""
        service = DatabaseService()
        service._db = db_session

        # 创建多个靶点
        for i in range(10):
            service.create_target({"standard_name": f"TARGET-EGFR-{i}"})

        # 搜索，限制返回 3 个
        results = service.search_targets("EGFR", limit=3)

        assert len(results) == 3
