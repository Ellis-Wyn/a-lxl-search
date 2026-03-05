"""
测试异常系统.

验证：
- 异常类正确初始化
- to_dict()方法正确返回字典
- 错误码正确映射
- HTTP状态码正确
"""

import pytest

from core.exceptions import (
    BaseAppException,
    DatabaseError,
    ValidationError,
    ExternalAPIError,
    CrawlerError,
    DataNormalizationError,
    NotFoundError,
    RateLimitError,
    ErrorCode,
)


class TestBaseAppException:
    """测试基础异常类."""

    def test_basic_initialization(self):
        """测试基本初始化."""
        exc = BaseAppException("Test error", ErrorCode.INTERNAL_SERVER_ERROR)
        assert exc.message == "Test error"
        assert exc.error_code == ErrorCode.INTERNAL_SERVER_ERROR
        assert exc.status_code == 500
        assert exc.error_id is not None
        assert len(exc.error_id) > 0

    def test_to_dict(self):
        """测试to_dict方法."""
        exc = BaseAppException(
            "Test error",
            ErrorCode.VALIDATION_ERROR,
            detail={"field": "username"},
        )
        result = exc.to_dict()
        assert result["error_code"] == "VALIDATION_001"
        assert result["message"] == "Test error"
        assert result["detail"] == {"field": "username"}
        assert "error_id" in result

    def test_str_representation(self):
        """测试字符串表示."""
        exc = BaseAppException("Test error", ErrorCode.INTERNAL_SERVER_ERROR)
        str_repr = str(exc)
        assert "INTERNAL_001" in str_repr
        assert "Test error" in str_repr


class TestDatabaseError:
    """测试数据库异常."""

    def test_initialization(self):
        """测试初始化."""
        exc = DatabaseError("Connection failed")
        assert exc.message == "Connection failed"
        assert exc.status_code == 500
        assert exc.error_code == ErrorCode.DATABASE_QUERY_ERROR

    def test_with_detail(self):
        """测试带详情."""
        exc = DatabaseError(
            "Query failed",
            detail={"query": "SELECT * FROM users"},
        )
        assert exc.detail["query"] == "SELECT * FROM users"


class TestValidationError:
    """测试验证异常."""

    def test_initialization(self):
        """测试初始化."""
        exc = ValidationError("Invalid input")
        assert exc.message == "Invalid input"
        assert exc.status_code == 400
        assert exc.error_code == ErrorCode.VALIDATION_ERROR


class TestExternalAPIError:
    """测试外部API异常."""

    def test_initialization(self):
        """测试初始化."""
        exc = ExternalAPIError("API timeout", service_name="PubMed")
        assert exc.message == "API timeout"
        assert exc.status_code == 502
        assert exc.detail["service"] == "PubMed"


class TestCrawlerError:
    """测试爬虫异常."""

    def test_initialization(self):
        """测试初始化."""
        exc = CrawlerError("Parse failed", url="https://example.com")
        assert exc.message == "Parse failed"
        assert exc.status_code == 500
        assert exc.detail["url"] == "https://example.com"


class TestDataNormalizationError:
    """测试数据归一化异常."""

    def test_initialization(self):
        """测试初始化."""
        exc = DataNormalizationError(
            "Unknown company",
            entity_type="company",
            raw_value="Unknown Corp",
        )
        assert exc.message == "Unknown company"
        assert exc.status_code == 422
        assert exc.detail["entity_type"] == "company"
        assert exc.detail["raw_value"] == "Unknown Corp"


class TestNotFoundError:
    """测试未找到异常."""

    def test_initialization(self):
        """测试初始化."""
        exc = NotFoundError(
            "Target not found",
            resource_type="Target",
            resource_id="EGFR",
        )
        assert exc.message == "Target not found"
        assert exc.status_code == 404
        assert exc.detail["resource_type"] == "Target"
        assert exc.detail["resource_id"] == "EGFR"


class TestRateLimitError:
    """测试频率限制异常."""

    def test_initialization(self):
        """测试初始化."""
        exc = RateLimitError("Too many requests", retry_after=60)
        assert exc.message == "Too many requests"
        assert exc.status_code == 429
        assert exc.detail["retry_after"] == 60
