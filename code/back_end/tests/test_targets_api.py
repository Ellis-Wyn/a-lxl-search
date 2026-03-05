"""
=====================================================
Targets API 单元测试
=====================================================

测试靶点 API 的各个端点：
- GET /api/v1/targets - 获取靶点列表
- GET /api/v1/targets/stats - 获取统计信息
- GET /api/v1/targets/{id} - 获取靶点详情
- GET /api/v1/targets/{id}/publications - 获取靶点文献
- GET /api/v1/targets/{id}/pipelines - 获取靶点管线

运行方式：
    pytest tests/test_targets_api.py -v
    pytest tests/test_targets_api.py::test_list_targets -v
=====================================================
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from utils.database import SessionLocal
from models.target import Target
from utils.serializers import TargetListItemSerializer


# =====================================================
# Fixtures
# =====================================================

@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def db():
    """数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_target(db: Session):
    """创建测试靶点"""
    target = Target(
        standard_name="TEST_TARGET Serializer",
        aliases=["Test1", "Test2"],
        gene_id="12345",
        uniprot_id="Q12345",
        category="测试分类",
        description="这是一个测试靶点"
    )
    db.add(target)
    db.commit()
    db.refresh(target)

    yield target

    # 清理
    db.delete(target)
    db.commit()


# =====================================================
# 测试用例
# =====================================================


class TestTargetsListAPI:
    """测试靶点列表 API"""

    def test_list_targets_default(self, client: TestClient):
        """测试获取靶点列表（默认参数）"""
        response = client.get("/api/v1/targets")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # 应该有种子数据

        # 验证返回数据结构
        target = data[0]
        assert "target_id" in target
        assert "standard_name" in target
        assert "aliases" in target
        assert "gene_id" in target
        assert isinstance(target["target_id"], str)
        assert isinstance(target["aliases"], list)

    def test_list_targets_with_limit(self, client: TestClient):
        """测试获取靶点列表（带 limit）"""
        response = client.get("/api/v1/targets?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3

    def test_list_targets_with_keyword(self, client: TestClient):
        """测试搜索靶点"""
        # 搜索 EGFR
        response = client.get("/api/v1/targets?keyword=EGFR")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any("EGFR" in t["standard_name"] for t in data)

    def test_list_targets_with_category(self, client: TestClient):
        """测试按分类过滤"""
        response = client.get("/api/v1/targets?category=激酶")

        # 可能没有数据，但请求应该成功
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_targets_with_offset(self, client: TestClient):
        """测试分页（offset）"""
        # 第一次请求
        response1 = client.get("/api/v1/targets?offset=0&limit=2")
        assert response1.status_code == 200
        data1 = response1.json()

        # 第二次请求（跳过前2条）
        response2 = client.get("/api/v1/targets?offset=2&limit=2")
        assert response2.status_code == 200
        data2 = response2.json()

        # 验证分页效果
        if len(data1) >= 2 and len(data2) >= 1:
            assert data1[0]["target_id"] != data2[0]["target_id"]


class TestTargetsStatsAPI:
    """测试靶点统计 API"""

    def test_get_stats(self, client: TestClient):
        """测试获取统计信息"""
        response = client.get("/api/v1/targets/stats")

        assert response.status_code == 200
        data = response.json()

        # 验证返回数据结构
        assert "total" in data
        assert "with_publications" in data
        assert "with_pipelines" in data
        assert "category_distribution" in data

        # 验证数据类型
        assert isinstance(data["total"], int)
        assert data["total"] > 0
        assert isinstance(data["category_distribution"], list)


class TestTargetDetailAPI:
    """测试靶点详情 API"""

    def test_get_target_detail_valid_id(self, client: TestClient, sample_target: Target):
        """测试获取靶点详情（有效 ID）"""
        target_id = str(sample_target.target_id)
        response = client.get(f"/api/v1/targets/{target_id}")

        assert response.status_code == 200
        data = response.json()

        # 验证返回数据
        assert data["target_id"] == target_id
        assert data["standard_name"] == "TEST_TARGET Serializer"
        assert data["aliases"] == ["Test1", "Test2"]
        assert data["gene_id"] == "12345"

    def test_get_target_detail_invalid_id(self, client: TestClient):
        """测试获取靶点详情（无效 ID）"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/targets/{fake_id}")

        assert response.status_code == 404

    def test_get_target_detail_invalid_format(self, client: TestClient):
        """测试获取靶点详情（无效格式）"""
        response = client.get("/api/v1/targets/invalid-uuid")

        # 应该返回错误（可能是 404 或 422）
        assert response.status_code in [404, 422]


class TestTargetPublicationsAPI:
    """测试靶点文献 API"""

    def test_get_target_publications(self, client: TestClient, sample_target: Target):
        """测试获取靶点文献"""
        target_id = str(sample_target.target_id)
        response = client.get(f"/api/v1/targets/{target_id}/publications")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_target_publications_with_limit(self, client: TestClient, sample_target: Target):
        """测试获取靶点文献（带 limit）"""
        target_id = str(sample_target.target_id)
        response = client.get(f"/api/v1/targets/{target_id}/publications?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5


class TestTargetPipelinesAPI:
    """测试靶点管线 API"""

    def test_get_target_pipelines(self, client: TestClient, sample_target: Target):
        """测试获取靶点管线"""
        target_id = str(sample_target.target_id)
        response = client.get(f"/api/v1/targets/{target_id}/pipelines")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_target_pipelines_with_phase_filter(self, client: TestClient, sample_target: Target):
        """测试获取靶点管线（带阶段过滤）"""
        target_id = str(sample_target.target_id)
        response = client.get(f"/api/v1/targets/{target_id}/pipelines?phase=Phase 3")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# =====================================================
# 序列化器测试
# =====================================================


class TestTargetSerializer:
    """测试靶点序列化器"""

    def test_serialize_target(self, sample_target: Target):
        """测试序列化靶点对象"""
        serializer = TargetListItemSerializer.model_validate(sample_target)

        assert isinstance(serializer.target_id, str)
        assert isinstance(serializer.aliases, list)
        assert serializer.standard_name == "TEST_TARGET Serializer"

    def test_serialize_uuid_to_string(self, sample_target: Target):
        """测试 UUID 转字符串"""
        serializer = TargetListItemSerializer.model_validate(sample_target)

        # 验证 UUID 已转换为字符串
        assert "-" in serializer.target_id
        assert len(serializer.target_id) == 36  # UUID 格式

    def test_serialize_empty_aliases(self, db: Session):
        """测试空别名列表"""
        target = Target(
            standard_name="NO_ALIAS_TARGET",
            aliases=None,
            gene_id="99999"
        )
        db.add(target)
        db.commit()
        db.refresh(target)

        serializer = TargetListItemSerializer.model_validate(target)
        assert serializer.aliases == []

        # 清理
        db.delete(target)
        db.commit()


# =====================================================
# 运行测试
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
