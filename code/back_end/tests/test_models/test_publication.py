"""
=====================================================
Publication 模型单元测试
=====================================================

测试覆盖：
- 文献创建和字段验证
- 作者列表处理
- 时效性计算方法
- to_dict 序列化
- ORM 关系
=====================================================
"""

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from models.publication import Publication
from models.target import Target
from models.relationships import TargetPublication
from conftest import assert_publication_equal


class TestPublicationModel:
    """Publication 模型测试类"""

    def test_create_publication_minimal(self, db_session: Session):
        """测试创建最小文献（仅必填字段）"""
        publication = Publication(
            pmid="12345678",
            title="Test Article"
        )
        db_session.add(publication)
        db_session.commit()
        db_session.refresh(publication)

        assert publication.pmid == "12345678"
        assert publication.title == "Test Article"
        assert publication.abstract is None
        assert publication.pub_date is None
        assert publication.journal is None
        assert publication.publication_type is None
        assert publication.authors is None
        assert isinstance(publication.created_at, datetime)

    def test_create_publication_full(self, db_session: Session):
        """测试创建完整文献"""
        pub_data = {
            "pmid": "12345678",
            "title": "EGFR inhibitor in NSCLC",
            "abstract": "This is a test abstract about EGFR inhibitors.",
            "pub_date": date(2024, 1, 15),
            "journal": "Journal of Clinical Oncology",
            "publication_type": "Clinical Trial",
            "authors": ["Zhang San", "Li Si", "Wang Wu"],
            "mesh_terms": ["Carcinoma, Non-Small Cell Lung", "Receptor, Epidermal Growth Factor"],
            "clinical_data_tags": ["ORR: 65%", "PFS: 12.3 months"]
        }

        publication = Publication(**pub_data)
        db_session.add(publication)
        db_session.commit()
        db_session.refresh(publication)

        assert_publication_equal(publication, pub_data)
        assert publication.abstract == pub_data["abstract"]
        assert publication.pub_date == pub_data["pub_date"]
        assert publication.authors == pub_data["authors"]
        assert publication.mesh_terms == pub_data["mesh_terms"]
        assert publication.clinical_data_tags == pub_data["clinical_data_tags"]

    def test_publication_unique_pmid(self, db_session: Session):
        """测试 PMID 唯一约束"""
        pub1 = Publication(
            pmid="12345678",
            title="First article"
        )
        db_session.add(pub1)
        db_session.commit()

        # 尝试创建相同的 PMID
        pub2 = Publication(
            pmid="12345678",
            title="Second article"
        )
        db_session.add(pub2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_get_days_since_publication(self, db_session: Session):
        """测试计算距发布天数"""
        # 创建 10 天前发表的文献
        pub_date = date.today() - timedelta(days=10)
        publication = Publication(
            pmid="12345678",
            title="Test",
            pub_date=pub_date
        )
        db_session.add(publication)
        db_session.commit()
        db_session.refresh(publication)

        days = publication.get_days_since_publication()
        assert days == 10

    def test_get_days_since_publication_no_date(self, db_session: Session):
        """测试无发布日期时的天数计算"""
        publication = Publication(
            pmid="12345678",
            title="Test"
        )
        db_session.add(publication)
        db_session.commit()

        days = publication.get_days_since_publication()
        assert days is None

    def test_calculate_recency_score(self, db_session: Session):
        """测试时效性得分计算"""
        test_cases = [
            (timedelta(days=10), 80),    # 11-30天: 80分
            (timedelta(days=50), 60),    # 31-90天: 60分
            (timedelta(days=200), 40),   # 91-365天: 40分
            (timedelta(days=500), 20),   # 366-730天: 20分
            (timedelta(days=1000), 20),  # >730天: 20分
        ]

        for days_delta, expected_score in test_cases:
            pub_date = date.today() - days_delta
            publication = Publication(
                pmid=f"{hash(days_delta)}",
                title="Test",
                pub_date=pub_date
            )
            db_session.add(publication)
            db_session.commit()

            score = publication.calculate_recency_score()
            assert score == expected_score, f"Failed for {days_delta.days} days"

    def test_calculate_recency_score_no_date(self, db_session: Session):
        """测试无发布日期时的时效性得分"""
        publication = Publication(
            pmid="12345678",
            title="Test"
        )
        db_session.add(publication)
        db_session.commit()

        score = publication.calculate_recency_score()
        assert score == 20  # 默认 20 分

    def test_to_dict_basic(self, db_session: Session):
        """测试基本序列化（不含关联）"""
        publication = Publication(
            pmid="12345678",
            title="Test Article",
            authors=["Author 1", "Author 2"]
        )
        db_session.add(publication)
        db_session.commit()

        pub_dict = publication.to_dict(include_relations=False)

        assert pub_dict["pmid"] == "12345678"
        assert pub_dict["title"] == "Test Article"
        assert pub_dict["authors"] == ["Author 1", "Author 2"]
        assert "targets" not in pub_dict

    def test_to_dict_with_relations(self, db_session: Session, target: Target):
        """测试序列化（含关联靶点）"""
        publication = Publication(
            pmid="12345678",
            title="Test Article"
        )
        db_session.add(publication)
        db_session.commit()
        db_session.refresh(publication)

        # 创建关联
        link = TargetPublication(
            target_id=target.target_id,
            pmid=publication.pmid,
            relation_type="focus_on"
        )
        db_session.add(link)
        db_session.commit()

        db_session.refresh(publication)

        pub_dict = publication.to_dict(include_relations=True)

        assert "targets" in pub_dict
        assert len(pub_dict["targets"]) == 1
        assert pub_dict["targets"][0]["standard_name"] == target.standard_name

    def test_publication_orm_relationship_targets(self, db_session: Session, publication, target: Target):
        """测试文献-靶点 ORM 关系"""
        # 创建关联
        link = TargetPublication(
            target_id=target.target_id,
            pmid=publication.pmid,
            relation_type="mentions"
        )
        db_session.add(link)
        db_session.commit()

        db_session.refresh(publication)

        # 通过 ORM 关系查询
        targets = publication.targets
        assert len(targets) == 1
        assert targets[0].standard_name == target.standard_name

    def test_authors_list_mutability(self, db_session: Session):
        """测试作者列表的可变性"""
        publication = Publication(
            pmid="12345678",
            title="Test",
            authors=["Author 1"]
        )
        db_session.add(publication)
        db_session.commit()

        # 添加作者
        publication.authors.append("Author 2")
        db_session.commit()

        db_session.refresh(publication)
        assert len(publication.authors) == 2
        assert "Author 2" in publication.authors

    def test_mesh_terms_storage(self, db_session: Session):
        """测试 MeSH 主题词存储"""
        publication = Publication(
            pmid="12345678",
            title="Test",
            mesh_terms=["Carcinoma, Non-Small Cell Lung", "Receptor, Epidermal Growth Factor"]
        )
        db_session.add(publication)
        db_session.commit()

        assert len(publication.mesh_terms) == 2
        assert "Carcinoma, Non-Small Cell Lung" in publication.mesh_terms

    def test_clinical_data_tags_storage(self, db_session: Session):
        """测试临床数据标签存储"""
        tags = ["ORR: 65%", "PFS: 12.3 months", "OS: 28.5 months"]
        publication = Publication(
            pmid="12345678",
            title="Test",
            clinical_data_tags=tags
        )
        db_session.add(publication)
        db_session.commit()

        assert publication.clinical_data_tags == tags

    def test_query_by_pmid(self, db_session: Session, publication):
        """测试根据 PMID 查询"""
        found = db_session.query(Publication).filter(
            Publication.pmid == publication.pmid
        ).first()

        assert found is not None
        assert found.title == publication.title

    def test_query_by_journal(self, db_session: Session):
        """测试根据期刊查询"""
        publication = Publication(
            pmid="12345678",
            title="Test",
            journal="Journal of Clinical Oncology"
        )
        db_session.add(publication)
        db_session.commit()

        found = db_session.query(Publication).filter(
            Publication.journal == "Journal of Clinical Oncology"
        ).all()

        assert len(found) >= 1

    def test_query_by_publication_type(self, db_session: Session):
        """测试根据文献类型查询"""
        publication = Publication(
            pmid="12345678",
            title="Test",
            publication_type="Clinical Trial"
        )
        db_session.add(publication)
        db_session.commit()

        found = db_session.query(Publication).filter(
            Publication.publication_type == "Clinical Trial"
        ).all()

        assert len(found) >= 1

    def test_publication_str_representation(self, db_session: Session):
        """测试文献的字符串表示"""
        publication = Publication(
            pmid="12345678",
            title="Test Article"
        )
        assert "12345678" in str(publication) or "Test Article" in str(publication)

    def test_delete_publication_preserves_target(self, db_session: Session, publication, target: Target):
        """测试删除文献时保留靶点"""
        # 创建关联
        link = TargetPublication(
            target_id=target.target_id,
            pmid=publication.pmid,
            relation_type="focus_on"
        )
        db_session.add(link)
        db_session.commit()

        # 删除文献
        db_session.delete(publication)
        db_session.commit()

        # 检查靶点是否还存在
        remaining_target = db_session.query(Target).filter(
            Target.target_id == target.target_id
        ).first()

        assert remaining_target is not None
        assert remaining_target.standard_name == "EGFR"

    def test_publication_ordering_by_date(self, db_session: Session):
        """测试按日期排序"""
        pub1 = Publication(pmid="1", title="Oldest", pub_date=date(2020, 1, 1))
        pub2 = Publication(pmid="2", title="Newest", pub_date=date(2024, 1, 1))
        pub3 = Publication(pmid="3", title="Middle", pub_date=date(2022, 1, 1))

        db_session.add_all([pub1, pub2, pub3])
        db_session.commit()

        # 按日期降序
        publications = db_session.query(Publication).order_by(
            Publication.pub_date.desc()
        ).all()

        assert publications[0].pmid == "2"  # Newest
        assert publications[1].pmid == "3"  # Middle
        assert publications[2].pmid == "1"  # Oldest
