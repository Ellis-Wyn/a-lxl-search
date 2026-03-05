"""
=====================================================
Pipeline 模型单元测试
=====================================================

测试覆盖：
- 管线创建和字段验证
- 时间戳方法
- Phase 映射和排序
- 消失检测
- 联合用药
- to_dict 序列化
- ORM 关系
=====================================================
"""

import pytest
import json
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session

from models.pipeline import Pipeline
from models.target import Target
from models.relationships import TargetPipeline
from conftest import assert_pipeline_equal


class TestPipelineModel:
    """Pipeline 模型测试类"""

    def test_create_pipeline_minimal(self, db_session: Session):
        """测试创建最小管线（仅必填字段）"""
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.commit()
        db_session.refresh(pipeline)

        assert pipeline.pipeline_id is not None
        assert pipeline.drug_code == "SHR-1210"
        assert pipeline.company_name == "恒瑞医药"
        assert pipeline.indication == "非小细胞肺癌"
        assert pipeline.phase == "Phase 3"
        assert pipeline.source_url == "https://example.com"
        assert pipeline.phase_raw is None
        assert pipeline.modality is None
        assert pipeline.status == "active"
        assert pipeline.is_combination is False
        assert pipeline.combination_drugs is None
        assert isinstance(pipeline.first_seen_at, datetime)
        assert isinstance(pipeline.last_seen_at, datetime)

    def test_create_pipeline_full(self, db_session: Session):
        """测试创建完整管线"""
        pipeline_data = {
            "drug_code": "SHR-1210",
            "company_name": "恒瑞医药",
            "indication": "非小细胞肺癌",
            "phase": "Phase 3",
            "phase_raw": "III期",
            "modality": "Monoclonal Antibody",
            "source_url": "https://www.hengrui.com/pipeline.html",
            "status": "active",
            "is_combination": True,
            "combination_drugs": json.dumps(["SHR-1210", "SHR-1501"])
        }

        pipeline = Pipeline(**pipeline_data)
        db_session.add(pipeline)
        db_session.commit()
        db_session.refresh(pipeline)

        assert_pipeline_equal(pipeline, pipeline_data)
        assert pipeline.phase_raw == "III期"
        assert pipeline.modality == "Monoclonal Antibody"
        assert pipeline.is_combination is True

    def test_pipeline_unique_constraint(self, db_session: Session):
        """测试唯一约束（drug_code + company_name + indication）"""
        pipeline1 = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline1)
        db_session.commit()

        # 尝试创建相同的管线（完全相同）
        pipeline2 = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 2",  # 阶段不同
            source_url="https://example.com"
        )
        db_session.add(pipeline2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_get_days_since_first_seen(self, db_session: Session):
        """测试计算距首次发现天数"""
        # 手动设置 first_seen_at 为 10 天前
        first_seen = datetime.now() - timedelta(days=10)
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.flush()
        pipeline.first_seen_at = first_seen
        db_session.commit()

        days = pipeline.get_days_since_first_seen()
        assert days == 10

    def test_get_days_since_last_seen(self, db_session: Session):
        """测试计算距最后见到天数"""
        # 手动设置 last_seen_at 为 5 天前
        last_seen = datetime.now() - timedelta(days=5)
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.flush()
        pipeline.last_seen_at = last_seen
        db_session.commit()

        days = pipeline.get_days_since_last_seen()
        assert days == 5

    def test_is_disappeared(self, db_session: Session):
        """测试消失检测（默认 90 天）"""
        # 创建 91 天前的管线（应判定为消失）
        old_date = datetime.now() - timedelta(days=91)
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.flush()
        pipeline.last_seen_at = old_date
        db_session.commit()

        assert pipeline.is_disappeared() is True

        # 更新时间后不应消失
        pipeline.last_seen_at = datetime.now()
        db_session.commit()
        assert pipeline.is_disappeared() is False

    def test_is_disappeared_custom_threshold(self, db_session: Session):
        """测试自定义消失阈值"""
        # 创建 50 天前的管线
        old_date = datetime.now() - timedelta(days=50)
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.flush()
        pipeline.last_seen_at = old_date
        db_session.commit()

        # 默认阈值（90天）不应消失
        assert pipeline.is_disappeared() is False

        # 自定义阈值为 30 天，应消失
        assert pipeline.is_disappeared(threshold_days=30) is True

    def test_get_phase_order(self, db_session: Session):
        """测试阶段排序值"""
        test_cases = [
            ("preclinical", 1),
            ("Phase 1", 2),
            ("Phase 2", 3),
            ("Phase 3", 4),
            ("filing", 5),
            ("approved", 6),
        ]

        for phase, expected_order in test_cases:
            pipeline = Pipeline(
                drug_code=f"TEST-{phase}",
                company_name="Test Company",
                indication="Test",
                phase=phase,
                source_url="https://example.com"
            )
            db_session.add(pipeline)
            db_session.commit()

            order = pipeline.get_phase_order()
            assert order == expected_order, f"Failed for phase: {phase}"

    def test_has_phase_changed(self, db_session: Session):
        """测试阶段变化检测"""
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 2",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.commit()

        # 阶段未变化
        assert pipeline.has_phase_changed("Phase 2") is False

        # 阶段变化
        assert pipeline.has_phase_changed("Phase 3") is True

    def test_combination_drugs_storage(self, db_session: Session):
        """测试联合用药存储"""
        drugs = ["SHR-1210", "SHR-1501", "Chemotherapy"]
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com",
            is_combination=True,
            combination_drugs=json.dumps(drugs)
        )
        db_session.add(pipeline)
        db_session.commit()

        # 读取并解析
        stored_drugs = json.loads(pipeline.combination_drugs)
        assert stored_drugs == drugs

    def test_to_dict_basic(self, db_session: Session):
        """测试基本序列化（不含关联）"""
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.commit()

        pipeline_dict = pipeline.to_dict(include_relations=False)

        assert pipeline_dict["drug_code"] == "SHR-1210"
        assert pipeline_dict["company_name"] == "恒瑞医药"
        assert pipeline_dict["indication"] == "非小细胞肺癌"
        assert pipeline_dict["phase"] == "Phase 3"
        assert "targets" not in pipeline_dict

    def test_to_dict_with_relations(self, db_session: Session, target: Target):
        """测试序列化（含关联靶点）"""
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.commit()
        db_session.refresh(pipeline)

        # 创建关联
        link = TargetPipeline(
            target_id=target.target_id,
            pipeline_id=pipeline.pipeline_id,
            relation_type="inhibits"
        )
        db_session.add(link)
        db_session.commit()

        db_session.refresh(pipeline)

        pipeline_dict = pipeline.to_dict(include_relations=True)

        assert "targets" in pipeline_dict
        assert len(pipeline_dict["targets"]) == 1
        assert pipeline_dict["targets"][0]["standard_name"] == target.standard_name

    def test_pipeline_orm_relationship_targets(self, db_session: Session, pipeline, target: Target):
        """测试管线-靶点 ORM 关系"""
        # 创建关联
        link = TargetPipeline(
            target_id=target.target_id,
            pipeline_id=pipeline.pipeline_id,
            relation_type="inhibits"
        )
        db_session.add(link)
        db_session.commit()

        db_session.refresh(pipeline)

        # 通过 ORM 关系查询
        targets = pipeline.targets
        assert len(targets) == 1
        assert targets[0].standard_name == target.standard_name

    def test_status_default_value(self, db_session: Session):
        """测试状态默认值"""
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.commit()

        assert pipeline.status == "active"

    def test_discontinued_status(self, db_session: Session):
        """测试终止状态"""
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com",
            status="discontinued"
        )
        db_session.add(pipeline)
        db_session.commit()

        assert pipeline.status == "discontinued"

    def test_query_by_drug_code(self, db_session: Session, pipeline):
        """测试根据药物代码查询"""
        found = db_session.query(Pipeline).filter(
            Pipeline.drug_code == "SHR-1210"
        ).first()

        assert found is not None
        assert found.company_name == "恒瑞医药"

    def test_query_by_company_name(self, db_session: Session):
        """测试根据公司查询"""
        pipeline = Pipeline(
            drug_code="TEST-001",
            company_name="Test Company",
            indication="Test",
            phase="Phase 1",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.commit()

        found = db_session.query(Pipeline).filter(
            Pipeline.company_name == "Test Company"
        ).all()

        assert len(found) >= 1

    def test_query_by_phase(self, db_session: Session):
        """测试根据阶段查询"""
        pipeline = Pipeline(
            drug_code="TEST-001",
            company_name="Test Company",
            indication="Test",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.commit()

        found = db_session.query(Pipeline).filter(
            Pipeline.phase == "Phase 3"
        ).all()

        assert len(found) >= 1

    def test_pipeline_ordering_by_last_seen(self, db_session: Session):
        """测试按最后见到时间排序"""
        # 创建不同时间的管线
        old_pipeline = Pipeline(
            drug_code="OLD-001",
            company_name="Test Company",
            indication="Test",
            phase="Phase 1",
            source_url="https://example.com"
        )
        db_session.add(old_pipeline)
        db_session.flush()

        new_pipeline = Pipeline(
            drug_code="NEW-001",
            company_name="Test Company",
            indication="Test",
            phase="Phase 1",
            source_url="https://example.com"
        )
        db_session.add(new_pipeline)
        db_session.commit()

        # 手动调整时间
        old_pipeline.last_seen_at = datetime.now() - timedelta(days=10)
        new_pipeline.last_seen_at = datetime.now()
        db_session.commit()

        # 按最后见到时间降序
        pipelines = db_session.query(Pipeline).order_by(
            Pipeline.last_seen_at.desc()
        ).all()

        assert pipelines[0].drug_code == "NEW-001"
        assert pipelines[1].drug_code == "OLD-001"

    def test_delete_pipeline_cascade_relationships(self, db_session: Session, pipeline, target: Target):
        """测试删除管线时级联删除关联"""
        # 创建关联
        link = TargetPipeline(
            target_id=target.target_id,
            pipeline_id=pipeline.pipeline_id,
            relation_type="inhibits"
        )
        db_session.add(link)
        db_session.commit()

        link_id = (target.target_id, pipeline.pipeline_id)

        # 删除管线
        db_session.delete(pipeline)
        db_session.commit()

        # 检查关联是否被删除
        remaining_link = db_session.query(TargetPipeline).filter(
            TargetPipeline.target_id == link_id[0],
            TargetPipeline.pipeline_id == link_id[1]
        ).first()

        assert remaining_link is None

    def test_pipeline_str_representation(self, db_session: Session):
        """测试管线的字符串表示"""
        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        assert "SHR-1210" in str(pipeline)

    def test_auto_timestamps_on_create(self, db_session: Session):
        """测试创建时自动设置时间戳"""
        before_create = datetime.now()

        pipeline = Pipeline(
            drug_code="SHR-1210",
            company_name="恒瑞医药",
            indication="非小细胞肺癌",
            phase="Phase 3",
            source_url="https://example.com"
        )
        db_session.add(pipeline)
        db_session.commit()
        db_session.refresh(pipeline)

        after_create = datetime.now()

        # 检查时间戳在合理范围内
        assert before_create <= pipeline.first_seen_at <= after_create
        assert before_create <= pipeline.last_seen_at <= after_create
