"""
统一异常体系定义.

设计原则：
1. 分层异常体系：基类异常 → 业务异常 → 领域异常
2. 错误码枚举：统一错误码管理
3. HTTP状态码映射：自动映射到合适的HTTP状态码
4. 请求追踪：支持request_id用于全链路追踪
"""

from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class ErrorCode(str, Enum):
    """错误码枚举.

    格式：{模块}_{错误类型}_{数字}
    例如：PUBMED_API_001 表示PubMed API相关错误
    """

    # 通用错误 (0000-0099)
    INTERNAL_SERVER_ERROR = "INTERNAL_001"
    INVALID_REQUEST = "INVALID_002"
    NOT_FOUND = "NOT_FOUND_003"
    UNAUTHORIZED = "UNAUTHORIZED_004"
    FORBIDDEN = "FORBIDDEN_005"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_006"

    # 数据库错误 (0100-0199)
    DATABASE_CONNECTION_ERROR = "DATABASE_001"
    DATABASE_QUERY_ERROR = "DATABASE_002"
    DATABASE_CONSTRAINT_ERROR = "DATABASE_003"
    DATABASE_TRANSACTION_ERROR = "DATABASE_004"

    # 验证错误 (0200-0299)
    VALIDATION_ERROR = "VALIDATION_001"
    MISSING_REQUIRED_FIELD = "VALIDATION_002"
    INVALID_FORMAT = "VALIDATION_003"
    INVALID_VALUE_RANGE = "VALIDATION_004"

    # 外部API错误 (0300-0399)
    EXTERNAL_API_TIMEOUT = "EXTERNAL_API_001"
    EXTERNAL_API_UNAVAILABLE = "EXTERNAL_API_002"
    EXTERNAL_API_RATE_LIMIT = "EXTERNAL_API_003"
    EXTERNAL_API_INVALID_RESPONSE = "EXTERNAL_API_004"

    # PubMed API错误 (0300-0349)
    PUBMED_API_ERROR = "PUBMED_API_001"
    PUBMED_QUERY_ERROR = "PUBMED_API_002"
    PUBMED_RATE_LIMIT = "PUBMED_API_003"
    PUBMED_PARSE_ERROR = "PUBMED_API_004"

    # 爬虫错误 (0350-0399)
    CRAWLER_ERROR = "CRAWLER_001"
    CRAWLER_PARSE_ERROR = "CRAWLER_002"
    CRAWLER_BLOCKED = "CRAWLER_003"
    CRAWLER_TIMEOUT = "CRAWLER_004"

    # 数据归一化错误 (0400-0499)
    NORMALIZATION_ERROR = "NORMALIZATION_001"
    COMPANY_NAME_NORMALIZATION_FAILED = "NORMALIZATION_002"
    TARGET_NORMALIZATION_FAILED = "NORMALIZATION_003"
    INDICATION_NORMALIZATION_FAILED = "NORMALIZATION_004"


class BaseAppException(Exception):
    """应用异常基类.

    所有自定义异常的基类，提供统一的错误处理接口。
    """

    # 默认HTTP状态码，子类可覆盖
    status_code: int = 500

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        detail: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        """初始化异常.

        Args:
            message: 用户友好的错误描述
            error_code: 错误码枚举
            detail: 额外的错误详情（可选）
            status_code: HTTP状态码（可选，默认使用类属性）
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.detail = detail or {}
        # 如果提供了status_code参数，覆盖类属性
        if status_code is not None:
            self.status_code = status_code
        # 生成唯一的错误ID用于追踪
        self.error_id = str(uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """将异常转换为字典格式，用于API响应.

        Returns:
            包含错误信息的字典
        """
        result = {
            "error_code": self.error_code.value,
            "message": self.message,
            "error_id": self.error_id,
        }
        if self.detail:
            result["detail"] = self.detail
        return result

    def __str__(self) -> str:
        """字符串表示."""
        return f"[{self.error_code.value}] {self.message}"

    def __repr__(self) -> str:
        """调试用字符串表示."""
        return f"{self.__class__.__name__}(error_code={self.error_code.value}, message={self.message})"


class DatabaseError(BaseAppException):
    """数据库操作异常."""

    def __init__(
        self,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.DATABASE_QUERY_ERROR,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            detail=detail,
            status_code=500,
        )


class ValidationError(BaseAppException):
    """数据验证异常."""

    status_code = 400

    def __init__(
        self,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.VALIDATION_ERROR,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            detail=detail,
        )


class ExternalAPIError(BaseAppException):
    """外部API调用异常."""

    status_code = 502

    def __init__(
        self,
        message: str,
        service_name: str,
        detail: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.EXTERNAL_API_UNAVAILABLE,
    ):
        """初始化外部API异常.

        Args:
            message: 错误描述
            service_name: 外部服务名称（如"PubMed API"）
            detail: 额外详情
            error_code: 错误码
        """
        if detail is None:
            detail = {}
        detail["service"] = service_name
        super().__init__(
            message=message,
            error_code=error_code,
            detail=detail,
        )


class CrawlerError(BaseAppException):
    """爬虫执行异常."""

    status_code = 500

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.CRAWLER_ERROR,
    ):
        """初始化爬虫异常.

        Args:
            message: 错误描述
            url: 抓取失败的URL（可选）
            detail: 额外详情
            error_code: 错误码
        """
        if detail is None:
            detail = {}
        if url:
            detail["url"] = url
        super().__init__(
            message=message,
            error_code=error_code,
            detail=detail,
        )


class DataNormalizationError(BaseAppException):
    """数据归一化异常."""

    status_code = 422  # Unprocessable Entity

    def __init__(
        self,
        message: str,
        entity_type: str,
        raw_value: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.NORMALIZATION_ERROR,
    ):
        """初始化归一化异常.

        Args:
            message: 错误描述
            entity_type: 实体类型（如"公司名"、"靶点"）
            raw_value: 未能归一化的原始值
            detail: 额外详情
            error_code: 错误码
        """
        if detail is None:
            detail = {}
        detail["entity_type"] = entity_type
        if raw_value:
            detail["raw_value"] = raw_value
        super().__init__(
            message=message,
            error_code=error_code,
            detail=detail,
        )


class NotFoundError(BaseAppException):
    """资源未找到异常."""

    status_code = 404

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ):
        """初始化未找到异常.

        Args:
            message: 错误描述
            resource_type: 资源类型（如"Publication"、"Target"）
            resource_id: 资源ID（可选）
            detail: 额外详情
        """
        if detail is None:
            detail = {}
        detail["resource_type"] = resource_type
        if resource_id:
            detail["resource_id"] = resource_id
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            detail=detail,
        )


class RateLimitError(BaseAppException):
    """请求频率限制异常."""

    status_code = 429

    def __init__(
        self,
        message: str = "请求频率超过限制，请稍后重试",
        retry_after: Optional[int] = None,
        detail: Optional[Dict[str, Any]] = None,
    ):
        """初始化频率限制异常.

        Args:
            message: 错误描述
            retry_after: 建议重试的秒数
            detail: 额外详情
        """
        if detail is None:
            detail = {}
        if retry_after:
            detail["retry_after"] = retry_after
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            detail=detail,
        )
