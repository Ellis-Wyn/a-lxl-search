"""
结构化日志系统配置.

使用Loguru实现统一日志管理：
- JSON格式日志（便于ELK分析）
- 日志文件轮转（按大小和日期）
- 按模块分离日志
- 上下文变量支持（request_id、user_id等）
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger as _logger

from config import settings

# 日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class JSONFormatter:
    """JSON格式日志格式化器."""

    def __init__(self, app_name: str = "pathology_ai"):
        """初始化格式化器.

        Args:
            app_name: 应用名称
        """
        self.app_name = app_name

    def __call__(self, record: Dict[str, Any]) -> str:
        """格式化日志记录为JSON.

        Args:
            record: 日志记录字典

        Returns:
            JSON格式的日志字符串
        """
        # 提取关键信息
        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "message": record["message"],
            "app": self.app_name,
        }

        # 添加额外字段（如果有）
        if record.get("extra"):
            # 排除None值
            extra = {
                k: v
                for k, v in record["extra"].items()
                if v is not None and not k.startswith("_")
            }
            if extra:
                log_entry.update(extra)

        # 添加异常信息（如果有）
        if record["exception"]:
            log_entry["exception"] = {
                "type": record["exception"].type.__name__,
                "value": record["exception"].value,
                "traceback": record["exception"].traceback,
            }

        # 添加文件和行号（仅DEBUG级别）
        if record["level"].name == "DEBUG":
            log_entry["file"] = {
                "name": record["file"].name,
                "path": str(record["file"].path),
                "line": record["line"],
                "function": record["function"],
            }

        return json.dumps(log_entry, ensure_ascii=False) + "\n"


def setup_logger(
    app_name: str = "pathology_ai",
    log_level: str = "INFO",
    json_logs: bool = True,
) -> None:
    """配置Loguru日志系统.

    Args:
        app_name: 应用名称
        log_level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        json_logs: 是否使用JSON格式
    """
    # 移除默认的handler
    _logger.remove()

    # 日志级别
    level = log_level.upper()

    # 控制台输出（开发环境使用彩色输出）
    if not json_logs:
        _logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>",
            level=level,
            colorize=True,
        )
    else:
        # 生产环境控制台也使用JSON（但只输出INFO及以上）
        _logger.add(
            sys.stderr,
            format="{message}",
            level="INFO",
            serialize=True,
        )

    # 应用主日志文件
    _logger.add(
        LOG_DIR / f"{app_name}.log",
        format="{message}",
        level=level,
        rotation="100 MB",  # 单文件最大100MB
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩旧日志
        filter=lambda record: record["extra"].get("module") != "crawler",
        enqueue=True,  # 异步写入
    )

    # 爬虫专用日志文件
    _logger.add(
        LOG_DIR / f"{app_name}_crawler.log",
        format="{message}",
        level=level,
        rotation="50 MB",
        retention="60 days",  # 爬虫日志保留更久
        compression="zip",
        filter=lambda record: record["extra"].get("module") == "crawler",
        enqueue=True,
    )

    # 错误日志文件（单独记录ERROR和CRITICAL）
    _logger.add(
        LOG_DIR / f"{app_name}_error.log",
        format="{message}",
        level="ERROR",
        rotation="10 MB",
        retention="90 days",  # 错误日志保留更久
        compression="zip",
        enqueue=True,
    )

    # 拦截标准库logging，将其重定向到loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    _logger.info(f"Logger initialized: {app_name}, level={level}")


class InterceptHandler(logging.Handler):
    """拦截标准库logging的Handler，重定向到loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """将logging记录转换为loguru记录.

        Args:
            record: logging记录
        """
        # 获取对应的loguru level
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找调用者
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def get_logger(name: str) -> Any:
    """获取logger实例.

    Args:
        name: logger名称（通常使用__name__）

    Returns:
        logger实例
    """
    return _logger.bind(name=name)


# 日志上下文管理器
class LoggerContext:
    """日志上下文管理器，用于添加上下文信息."""

    def __init__(self, **kwargs):
        """初始化上下文.

        Args:
            **kwargs: 上下文键值对
        """
        self.context = kwargs

    def __enter__(self):
        """进入上下文."""
        return _logger.bind(**self.context)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文."""
        if exc_type is not None:
            _logger.error(
                "Context exited with exception",
                extra={"exception_type": str(exc_type), "exception_value": str(exc_val)},
            )


def bind_context(**kwargs) -> None:
    """绑定上下文到logger.

    Args:
        **kwargs: 上下文键值对（如request_id、user_id等）
    """
    global _logger
    _logger = _logger.bind(**kwargs)


def unbind_context(*keys: str) -> None:
    """解绑上下文.

    Args:
        *keys: 要解绑的键名

    Note:
        loguru 不支持 unbind，上下文会在请求结束时自动清理
    """
    pass


# 模块初始化时自动配置
if not settings.DEBUG:
    # 生产环境使用JSON格式
    setup_logger(json_logs=True)
else:
    # 开发环境使用彩色输出
    setup_logger(json_logs=False)


# 导出logger和_default_logger
logger = _logger
__all__ = [
    "logger",
    "_logger",
    "get_logger",
    "setup_logger",
    "LoggerContext",
    "bind_context",
    "unbind_context",
]
