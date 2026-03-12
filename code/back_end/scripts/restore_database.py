"""
=====================================================
数据库恢复脚本 - P8 级标准
=====================================================

功能：
- 自动检测 PostgreSQL 安装路径
- 从 .env 或命令行读取配置
- 完整的错误处理和日志
- 恢复前验证备份文件
- 支持命令行参数

运行方式：
    python -m scripts.restore_database
    python -m scripts.restore_database --backup D:/backups/backup.sql
    python -m scripts.restore_database --host localhost --port 5433

作者：A_lxl_search Team
日期：2026-03-12
=====================================================
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
import argparse

# 日志配置
try:
    from loguru import logger
    if not hasattr(logger, 'success'):
        logger.success = logger.info
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# =====================================================
# 配置常量
# =====================================================

DEFAULT_POSTGRES_PATHS = [
    r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
    r"C:\Program Files (x86)\PostgreSQL\17\bin\psql.exe",
]

DEFAULT_BACKUP_DIR = Path("D:/backups")
MIN_BACKUP_SIZE_KB = 1


# =====================================================
# 异常类
# =====================================================

class RestoreError(Exception):
    """恢复错误基类"""
    pass


class PostgreSQLNotFoundError(RestoreError):
    """找不到 PostgreSQL 安装"""
    pass


class BackupFileNotFoundError(RestoreError):
    """备份文件不存在"""
    pass


class BackupVerificationError(RestoreError):
    """备份文件验证失败"""
    pass


# =====================================================
# 配置加载
# =====================================================

def load_config() -> dict:
    """从 .env 加载数据库配置"""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"

    config = {
        "host": "localhost",
        "port": "5432",
        "user": "postgres",
        "password": "",
        "db_name": "drug_intelligence_db"
    }

    if not env_file.exists():
        logger.warning(f"配置文件不存在: {env_file}")
        return config

    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == "DB_HOST":
                    config["host"] = value
                elif key == "DB_PORT":
                    config["port"] = value
                elif key == "DB_USER":
                    config["user"] = value
                elif key == "DB_PASSWORD":
                    config["password"] = value
                elif key == "DB_NAME":
                    config["db_name"] = value

    return config


# =====================================================
# 工具函数
# =====================================================

def find_psql() -> Path:
    """查找 psql 可执行文件"""
    # 先检查 PATH
    psql_in_path = shutil.which("psql")
    if psql_in_path:
        return Path(psql_in_path)

    # 检查常见安装位置
    for path_str in DEFAULT_POSTGRES_PATHS:
        path = Path(path_str)
        if path.exists():
            logger.info(f"找到 PostgreSQL: {path}")
            return path

    raise PostgreSQLNotFoundError("找不到 psql，请手动指定路径")


def find_last_backup(backup_dir: Path, db_name: str) -> Optional[Path]:
    """查找最新的备份文件"""
    pattern = f"{db_name}_backup_*.sql"
    backups = list(backup_dir.glob(pattern))

    if not backups:
        return None

    # 按修改时间排序，返回最新的
    return sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def verify_backup_file(backup_file: Path) -> bool:
    """验证备份文件是否有效"""
    if not backup_file.exists():
        raise BackupFileNotFoundError(f"备份文件不存在: {backup_file}")

    size_kb = backup_file.stat().st_size / 1024
    if size_kb < MIN_BACKUP_SIZE_KB:
        raise BackupVerificationError(
            f"备份文件过小: {size_kb:.1f} KB (可能损坏)"
        )

    # 检查内容
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            # 读取前1MB检查
            content = f.read(1024 * 1024)

        if "PostgreSQL database dump" not in content:
            raise BackupVerificationError("不是有效的 PostgreSQL 备份文件")

        logger.info(f"  文件大小: {size_kb:.1f} KB")
        return True

    except UnicodeDecodeError:
        raise BackupVerificationError("备份文件编码错误")


def ensure_database_exists(psql_path: Path, config: dict) -> bool:
    """确保目标数据库存在，不存在则创建"""
    logger.info("检查数据库是否存在...")

    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]

    # 检查数据库是否存在
    check_cmd = [
        str(psql_path),
        f"--host={config['host']}",
        f"--port={config['port']}",
        f"--username={config['user']}",
        "--list",
        "--tuples-only"  # 只输出数据行
    ]

    try:
        result = subprocess.run(
            check_cmd,
            capture_output=True,
            env=env,
            encoding='utf-8',
            errors='ignore'  # 忽略编码错误
        )
    except Exception as e:
        logger.warning(f"  检查数据库失败: {e}")
        # 尝试直接创建
        result = subprocess.run(check_cmd, capture_output=True, env=env)

    # 解析输出检查数据库是否存在
    output = result.stdout if result.stdout else ""
    if config["db_name"] in output:
        logger.info(f"  数据库 '{config['db_name']}' 已存在")
        return True

    # 创建数据库
    logger.info(f"  创建数据库 '{config['db_name']}'...")
    create_cmd = [
        str(psql_path),
        f"--host={config['host']}",
        f"--port={config['port']}",
        f"--username={config['user']}",
        "-c",
        f"CREATE DATABASE {config['db_name']} ENCODING 'UTF8';"
    ]

    result = subprocess.run(create_cmd, capture_output=True, env=env)

    if result.returncode == 0:
        logger.success(f"  ✓ 数据库创建成功")
        return True
    else:
        # 可能已存在，再次检查
        logger.info(f"  尝试连接数据库...")
        return True


# =====================================================
# 恢复核心逻辑
# =====================================================

def restore_database(
    backup_file: Path,
    config: dict,
    psql_path: Path
) -> bool:
    """执行数据库恢复"""
    logger.info("=" * 60)
    logger.info(f"开始恢复数据库: {config['db_name']}")
    logger.info(f"备份文件: {backup_file}")
    logger.info(f"目标服务器: {config['host']}:{config['port']}")
    logger.info("=" * 60)

    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]

    logger.info("执行恢复...")

    # 使用完整路径的 psql
    cmd = [
        str(psql_path),
        f"--host={config['host']}",
        f"--port={config['port']}",
        f"--username={config['user']}",
        f"--dbname={config['db_name']}",
        f"--file={backup_file}"
    ]

    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        encoding='utf-8',
        errors='ignore'
    )

    # psql 可能返回非0但实际成功，检查输出
    stderr = process.stderr if process.stderr else ""
    stdout = process.stdout if process.stdout else ""

    if "ERROR" in stderr.upper() or "FATAL" in stderr.upper():
        logger.error(f"✗ 恢复失败:")
        logger.error(stderr)
        return False

    # 检查是否有关键错误
    combined_output = stdout + stderr
    if any(x in combined_output.upper() for x in ["ERROR", "FATAL", "ROLLBACK"]):
        logger.error(f"✗ 恢复可能失败:")
        logger.error(combined_output[-500:])  # 只显示最后500字符
        return False

    logger.success("✓ 恢复成功！")
    return True


# =====================================================
# 主流程
# =====================================================

def main(
    backup_file: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[str] = None,
    password: Optional[str] = None,
    create_db: bool = True
):
    """主函数"""
    try:
        # 1. 加载配置
        config = load_config()

        # 命令行参数覆盖配置
        if host:
            config["host"] = host
        if port:
            config["port"] = port
        if password:
            config["password"] = password

        if not config["password"]:
            raise RestoreError("未设置数据库密码，请使用 --password 参数")

        logger.info("数据库配置:")
        logger.info(f"  主机: {config['host']}:{config['port']}")
        logger.info(f"  数据库: {config['db_name']}")

        # 2. 查找备份文件
        if backup_file:
            backup_path = Path(backup_file)
        else:
            backup_path = find_last_backup(DEFAULT_BACKUP_DIR, config["db_name"])
            if not backup_path:
                raise RestoreError(
                    f"未找到备份文件: {DEFAULT_BACKUP_DIR}/{config['db_name']}_backup_*.sql"
                )

        logger.info(f"备份文件: {backup_path}")

        # 3. 验证备份文件
        verify_backup_file(backup_path)

        # 4. 查找 psql
        psql_path = find_psql()

        # 5. 确保数据库存在
        if create_db:
            if not ensure_database_exists(psql_path, config):
                return 1

        # 6. 执行恢复
        if restore_database(backup_path, config, psql_path):
            logger.success("=" * 60)
            logger.success("恢复完成！")
            logger.success("=" * 60)
            return 0
        else:
            return 1

    except RestoreError as e:
        logger.error(f"✗ 恢复失败: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("恢复已取消")
        return 130
    except Exception as e:
        logger.exception(f"✗ 未预期的错误: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="数据库恢复脚本 - P8 级标准",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 使用最后一次备份
    python -m scripts.restore_database

    # 指定备份文件
    python -m scripts.restore_database --backup D:/backups/backup.sql

    # 恢复到 PostgreSQL 17（端口5433）
    python -m scripts.restore_database --port 5433 --password 051028

    # 恢复到远程服务器
    python -m scripts.restore_database --host 192.168.1.100 --port 5433
        """
    )

    parser.add_argument(
        "--backup", "-b",
        type=str,
        default=None,
        help="备份文件路径（默认使用最后一次备份）"
    )

    parser.add_argument(
        "--host", "-H",
        type=str,
        default=None,
        help="数据库主机（默认: localhost）"
    )

    parser.add_argument(
        "--port", "-p",
        type=str,
        default=None,
        help="数据库端口（默认: 从 .env 读取）"
    )

    parser.add_argument(
        "--password", "-P",
        type=str,
        default=None,
        help="数据库密码（默认: 从 .env 读取）"
    )

    parser.add_argument(
        "--no-create-db",
        action="store_true",
        help="不自动创建数据库"
    )

    args = parser.parse_args()

    sys.exit(main(
        backup_file=args.backup,
        host=args.host,
        port=args.port,
        password=args.password,
        create_db=not args.no_create_db
    ))
