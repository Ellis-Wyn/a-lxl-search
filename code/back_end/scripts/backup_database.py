"""
=====================================================
数据库备份脚本 - P8 级标准
=====================================================

功能：
- 自动检测 PostgreSQL 安装路径
- 从 .env 读取配置（无硬编码）
- 完整的错误处理和日志
- 备份文件完整性验证
- 自动清理旧备份（保留最近 N 个）

运行方式：
    python -m scripts.backup_database
    python -m scripts.backup_database --keep 5

作者：A_lxl_search Team
日期：2026-03-12
=====================================================
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
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
    r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
    r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
    r"C:\Program Files\PostgreSQL\13\bin\pg_dump.exe",
    r"C:\Program Files (x86)\PostgreSQL\15\bin\pg_dump.exe",
]

DEFAULT_BACKUP_DIR = Path("D:/backups")
DEFAULT_KEEP_COUNT = 5  # 保留最近5个备份
MIN_BACKUP_SIZE_KB = 1  # 最小备份大小 1KB


# =====================================================
# 异常类
# =====================================================

class BackupError(Exception):
    """备份错误基类"""
    pass


class PostgreSQLNotFoundError(BackupError):
    """找不到 PostgreSQL 安装"""
    pass


class BackupVerificationError(BackupError):
    """备份验证失败"""
    pass


# =====================================================
# 配置加载
# =====================================================

def load_config() -> dict:
    """
    从 .env 加载数据库配置

    返回:
        dict: 数据库配置 {host, port, user, password, db_name}
    """
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"

    if not env_file.exists():
        raise BackupError(f"配置文件不存在: {env_file}")

    # 简单的 .env 解析（避免依赖 python-dotenv）
    config = {
        "host": "localhost",
        "port": "5432",
        "user": "postgres",
        "password": "",
        "db_name": "drug_intelligence_db"
    }

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

    if not config["password"]:
        raise BackupError("未找到 DB_PASSWORD 配置")

    return config


# =====================================================
# PostgreSQL 路径检测
# =====================================================

def find_pg_dump() -> Path:
    """
    查找 pg_dump 可执行文件

    返回:
        Path: pg_dump 的完整路径

    抛出:
        PostgreSQLNotFoundError: 如果找不到 pg_dump
    """
    # 先检查 PATH
    pg_dump_in_path = shutil.which("pg_dump")
    if pg_dump_in_path:
        logger.info(f"从 PATH 找到 pg_dump: {pg_dump_in_path}")
        return Path(pg_dump_in_path)

    # 检查常见安装位置
    for path_str in DEFAULT_POSTGRES_PATHS:
        path = Path(path_str)
        if path.exists():
            logger.info(f"找到 PostgreSQL: {path}")
            return path

    # 让用户手动输入
    logger.warning("未能自动找到 PostgreSQL 安装")
    logger.info("常见安装位置:")
    for i, path in enumerate(DEFAULT_POSTGRES_PATHS, 1):
        logger.info(f"  {i}. {path}")

    custom_path = input("请输入 pg_dump 完整路径: ").strip()
    custom_path = Path(custom_path)
    if not custom_path.exists():
        raise PostgreSQLNotFoundError(f"指定的路径不存在: {custom_path}")
    return custom_path


# =====================================================
# 备份核心逻辑
# =====================================================

def create_backup(
    config: dict,
    pg_dump_path: Path,
    backup_dir: Path
) -> Path:
    """
    执行数据库备份

    参数:
        config: 数据库配置
        pg_dump_path: pg_dump 可执行文件路径
        backup_dir: 备份目录

    返回:
        Path: 备份文件路径

    抛出:
        BackupError: 备份失败
    """
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_name = config["db_name"]
    backup_file = backup_dir / f"{db_name}_backup_{timestamp}.sql"

    logger.info("=" * 60)
    logger.info(f"开始备份数据库: {db_name}")
    logger.info(f"目标文件: {backup_file}")
    logger.info("=" * 60)

    # 构建命令
    cmd = [
        str(pg_dump_path),
        f"--host={config['host']}",
        f"--port={config['port']}",
        f"--username={config['user']}",
        "--format=plain",
        "--no-owner",
        "--no-acl",
        "--verbose",
        db_name
    ]

    # 设置密码环境变量
    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]

    # 执行备份
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            process = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )

        if process.returncode != 0:
            error_msg = process.stderr or "未知错误"
            raise BackupError(f"pg_dump 失败: {error_msg}")

        file_size = backup_file.stat().st_size / 1024
        logger.success(f"✓ 备份成功！")
        logger.info(f"  文件: {backup_file}")
        logger.info(f"  大小: {file_size:.1f} KB")

        return backup_file

    except FileNotFoundError as e:
        raise BackupError(f"找不到 pg_dump: {pg_dump_path}")
    except Exception as e:
        # 清理失败的备份文件
        if backup_file.exists():
            backup_file.unlink()
        raise BackupError(f"备份失败: {e}")


def verify_backup(backup_file: Path, db_name: str) -> bool:
    """
    验证备份文件完整性

    参数:
        backup_file: 备份文件路径
        db_name: 数据库名称

    返回:
        bool: 验证是否通过

    抛出:
        BackupVerificationError: 验证失败
    """
    logger.info("=" * 60)
    logger.info("验证备份文件...")
    logger.info("=" * 60)

    # 检查文件存在
    if not backup_file.exists():
        raise BackupVerificationError(f"备份文件不存在: {backup_file}")

    # 检查文件大小
    size_kb = backup_file.stat().st_size / 1024
    if size_kb < MIN_BACKUP_SIZE_KB:
        raise BackupVerificationError(
            f"备份文件过小: {size_kb:.1f} KB (可能不完整)"
        )

    # 检查内容
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查关键标记
        checks = [
            ("PostgreSQL database dump", "PG_DUMP 标记"),
            ("CREATE TABLE", "CREATE TABLE 语句"),
            ("COPY", "COPY 语句"),
        ]

        for pattern, name in checks:
            if pattern not in content:
                raise BackupVerificationError(f"缺少 {name}")

        logger.success("✓ 备份验证通过")
        logger.info(f"  文件大小: {size_kb:.1f} KB")

        # 统计表数量
        table_count = content.count("CREATE TABLE")
        copy_count = content.count("COPY public")
        logger.info(f"  表数量: {table_count}")
        logger.info(f"  数据块: {copy_count}")

        return True

    except UnicodeDecodeError:
        raise BackupVerificationError("备份文件编码错误")
    except Exception as e:
        raise BackupVerificationError(f"验证失败: {e}")


def cleanup_old_backups(
    backup_dir: Path,
    db_name: str,
    keep_count: int = DEFAULT_KEEP_COUNT
) -> int:
    """
    清理旧备份文件

    参数:
        backup_dir: 备份目录
        db_name: 数据库名称
        keep_count: 保留文件数量

    返回:
        int: 删除的文件数量
    """
    pattern = f"{db_name}_backup_*.sql"
    backups = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

    if len(backups) <= keep_count:
        logger.info(f"当前有 {len(backups)} 个备份，无需清理")
        return 0

    to_delete = backups[keep_count:]
    deleted_count = 0

    for old_backup in to_delete:
        try:
            old_backup.unlink()
            deleted_count += 1
            logger.info(f"  删除旧备份: {old_backup.name}")
        except Exception as e:
            logger.warning(f"  删除失败: {old_backup.name} - {e}")

    if deleted_count > 0:
        logger.info(f"已清理 {deleted_count} 个旧备份，保留最近 {keep_count} 个")

    return deleted_count


# =====================================================
# 主流程
# =====================================================

def main(keep_count: int = DEFAULT_KEEP_COUNT, backup_dir: Optional[Path] = None):
    """
    主函数

    参数:
        keep_count: 保留备份数量
        backup_dir: 备份目录（默认 D:/backups）
    """
    try:
        # 1. 加载配置
        logger.info("加载数据库配置...")
        config = load_config()
        logger.info(f"  数据库: {config['db_name']}")
        logger.info(f"  主机: {config['host']}:{config['port']}")

        # 2. 查找 pg_dump
        pg_dump_path = find_pg_dump()

        # 3. 执行备份
        backup_path = backup_dir or DEFAULT_BACKUP_DIR
        backup_file = create_backup(config, pg_dump_path, backup_path)

        # 4. 验证备份
        verify_backup(backup_file, config['db_name'])

        # 5. 清理旧备份
        cleanup_old_backups(backup_path, config['db_name'], keep_count)

        # 6. 保存备份信息
        info_file = backup_path / "last_backup.txt"
        info_file.write_text(str(backup_file))

        logger.success("=" * 60)
        logger.success("备份完成！")
        logger.success("=" * 60)

        return 0

    except BackupError as e:
        logger.error(f"✗ 备份失败: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("备份已取消")
        return 130
    except Exception as e:
        logger.exception(f"✗ 未预期的错误: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="数据库备份脚本 - P8 级标准",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m scripts.backup_database              # 使用默认配置
    python -m scripts.backup_database --keep 3     # 只保留最近3个备份
    python -m scripts.backup_database --dir ./backups  # 指定备份目录
        """
    )

    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP_COUNT,
        help=f"保留最近 N 个备份 (默认: {DEFAULT_KEEP_COUNT})"
    )

    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help=f"备份目录 (默认: {DEFAULT_BACKUP_DIR})"
    )

    args = parser.parse_args()

    sys.exit(main(keep_count=args.keep, backup_dir=args.dir))
