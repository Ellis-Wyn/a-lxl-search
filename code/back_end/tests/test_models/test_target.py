"""
=====================================================
Target 模型单元测试
=====================================================

测试覆盖：
- 靶点创建和字段验证
- 别名相关方法
- to_dict 序列化
- ORM 关系
=====================================================
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from models.target import Target
from models.publication import Publication
from models.pipeline import Pipeline
from models.relationships import TargetPublication, TargetPipeline
from conftest import assert_target_equal


class TestTargetModel:
    """Target 模型测试类"""

    def test_create_target_minimal(self, db_session: Session):
        """测试创建最小靶点（仅必填字段）"""
        target = Target(standard_name="EGFR")
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        assert target.target_id is not None
        assert target.standard_name == "EGFR"
        assert target.aliases == []
        assert target.gene_id is None
        assert target.uniprot_id is None
        assert target.category is None
        assert target.description is None
        assert isinstance(target.created_at, datetime)

    def test_create_target_full(self, db_session: Session):
        """测试创建完整靶点"""
        target_data = {
            "standard_name": "EGFR",
            "aliases": ["ERBB1", "HER1"],
            "gene_id": "1956",
            "uniprot_id": "P00533",
            "category": "Tyrosine Kinase",
            "description": "Epidermal Growth Factor Receptor"
        }

        target = Target(**target_data)
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        assert_target_equal(target, target_data)
        assert isinstance(target.created_at, datetime)

    def test_target_aliases(self, db_session: Session):
        """测试别名功能"""
        # 测试有别名
        target_with_aliases = Target(
            standard_name="EGFR",
            aliases=["ERBB1", "HER1", "ERBB2"]
        )
        db_session.add(target_with_aliases)
        db_session.commit()
        db_session.refresh(target_with_aliases)

        assert target_with_aliases.has_alias("ERBB1") is True
        assert target_with_aliases.has_alias("HER1") is True
        assert target_with_aliases.has_alias("EGFR") is False  # 标准名称不算别名
        assert target_with_aliases.has_alias("INVALID") is False

        # 测试无别名
        target_no_aliases = Target(standard_name="PD-1")
        db_session.add(target_no_aliases)
        db_session.commit()
        db_session.refresh(target_no_aliases)

        assert target_no_aliases.has_alias("anything") is False

    def test_get_all_names(self, db_session: Session):
        """测试获取所有名称（标准名称 + 别名）"""
        target = Target(
            standard_name="EGFR",
            aliases=["ERBB1", "HER1"]
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        all_names = target.get_all_names()
        assert set(all_names) == {"EGFR", "ERBB1", "HER1"}

        # 无别名的情况
        target2 = Target(standard_name="PD-1")
        db_session.add(target2)
        db_session.commit()
        db_session.refresh(target2)

        assert target2.get_all_names() == ["PD-1"]

    def test_to_dict_basic(self, db_session: Session):
        """测试基本序列化（不含关联）"""
        target = Target(
            standard_name="EGFR",
            aliases=["ERBB1"],
            gene_id="1956",
            category="Tyrosine Kinase"
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        target_dict = target.to_dict(include_relations=False)

        assert target_dict["standard_name"] == "EGFR"
        assert target_dict["aliases"] == ["ERBB1"]
        assert target_dict["gene_id"] == "1956"
        assert target_dict["category"] == "Tyrosine Kinase"
        assert "publications" not in target_dict
        assert "pipelines" not in target_dict

    def test_to_dict_with_relations(self, db_session: Session, sample_publication: Publication, sample_pipeline: Pipeline):
        """测试序列化（含关联）"""
        target = Target(standard_name="EGFR")
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        # 创建关联
        link1 = TargetPublication(
            target_id=target.target_id,
            pmid=sample_publication.pmid,
            relation_type="focus_on"
        )
        link2 = TargetPipeline(
            target_id=target.target_id,
            pipeline_id=sample_pipeline.pipeline_id,
            relation_type="inhibits"
        )
        db_session.add(link1)
        db_session.add(link2)
        db_session.commit()

        db_session.refresh(target)

        target_dict = target.to_dict(include_relations=True)

        assert "publications" in target_dict
        assert "pipelines" in target_dict
        assert len(target_dict["publications"]) == 1
        assert len(target_dict["pipelines"]) == 1
        assert target_dict["publications"][0]["pmid"] == sample_publication.pmid
        assert target_dict["pipelines"][0]["drug_code"] == sample_pipeline.drug_code

    def test_target_orm_relationship_publications(self, db_session: Session, target, sample_publication: Publication):
        """测试靶点-文献 ORM 关系"""
        # 创建关联
        link = TargetPublication(
            target_id=target.target_id,
            pmid=sample_publication.pmid,
            relation_type="mentions"
        )
        db_session.add(link)
        db_session.commit()

        db_session.refresh(target)

        # 通过 ORM 关系查询
        publications = target.publications
        assert len(publications) == 1
        assert publications[0].pmid == sample_publication.pmid

    def test_target_orm_relationship_pipelines(self, db_session: Session, target, sample_pipeline: Pipeline):
        """测试靶点-管线 ORM 关系"""
        # 创建关联
        link = TargetPipeline(
            target_id=target.target_id,
            pipeline_id=sample_pipeline.pipeline_id,
            relation_type="inhibits",
            is_primary=True
        )
        db_session.add(link)
        db_session.commit()

        db_session.refresh(target)

        # 通过 ORM 关系查询
        pipelines = target.pipelines
        assert len(pipelines) == 1
        assert pipelines[0].drug_code == sample_pipeline.drug_code

    def test_target_unique_constraint(self, db_session: Session):
        """测试标准名称唯一约束"""
        target1 = Target(standard_name="EGFR")
        db_session.add(target1)
        db_session.commit()

        # 尝试创建重复的标准名称
        target2 = Target(standard_name="EGFR")
        db_session.add(target2)

        with pytest.raises(Exception):  # 应该抛出 IntegrityError
            db_session.commit()

    def test_target_aliase_list_mutability(self, db_session: Session):
        """测试别名列表的可变性"""
        target = Target(
            standard_name="EGFR",
            aliases=["ERBB1"]
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        # 修改别名
        target.aliases.append("HER1")
        db_session.commit()

        db_session.refresh(target)
        assert "HER1" in target.aliases

    def test_delete_target_cascade_relationships(self, db_session: Session, target, sample_publication: Publication):
        """测试删除靶点时级联删除关联"""
        # 创建关联
        link = TargetPublication(
            target_id=target.target_id,
            pmid=sample_publication.pmid,
            relation_type="focus_on"
        )
        db_session.add(link)
        db_session.commit()

        link_id = (target.target_id, sample_publication.pmid)

        # 删除靶点
        db_session.delete(target)
        db_session.commit()

        # 检查关联是否被删除
        remaining_link = db_session.query(TargetPublication).filter(
            TargetPublication.target_id == link_id[0],
            TargetPublication.pmid == link_id[1]
        ).first()

        assert remaining_link is None

    def test_target_str_representation(self, db_session: Session):
        """测试靶点的字符串表示"""
        target = Target(standard_name="EGFR")
        assert str(target) == "EGFR" or "EGFR" in str(target)

    def test_target_query_by_standard_name(self, db_session: Session, target):
        """测试根据标准名称查询"""
        found = db_session.query(Target).filter(
            Target.standard_name == "EGFR"
        ).first()

        assert found is not None
        assert found.target_id == target.target_id

    def test_target_query_by_gene_id(self, db_session: Session):
        """测试根据 Gene ID 查询"""
        target = Target(
            standard_name="EGFR",
            gene_id="1956"
        )
        db_session.add(target)
        db_session.commit()

        found = db_session.query(Target).filter(
            Target.gene_id == "1956"
        ).first()

        assert found is not None
        assert found.standard_name == "EGFR"

    def test_target_case_sensitive_search(self, db_session: Session):
        """测试区分大小写搜索"""
        target = Target(standard_name="EGFR")
        db_session.add(target)
        db_session.commit()

        # 应该找到
        found = db_session.query(Target).filter(
            Target.standard_name == "EGFR"
        ).first()
        assert found is not None

        # 应该找不到
        not_found = db_session.query(Target).filter(
            Target.standard_name == "egfr"
        ).first()
        assert not_found is None
