"""
创建数据库的辅助脚本
运行：python scripts/create_database.py
"""

import sys
import psycopg2
from psycopg2 import OperationalError
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from core.logger import setup_logger, get_logger

# 初始化日志
setup_logger(app_name="create_db", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


def create_database():
    """创建数据库"""
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("创建数据库: drug_intelligence_db")
    logger.info("=" * 60)

    # 先连接到默认数据库（postgres）
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database="postgres",  # 连接到默认数据库
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = conn.cursor()

        # 检查数据库是否已存在
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (settings.DB_NAME,))
        exists = cursor.fetchone()

        if exists:
            logger.info(f"✓ 数据库 '{settings.DB_NAME}' 已存在")
        else:
            # 创建数据库
            cursor.execute(f"CREATE DATABASE {settings.DB_NAME}")
            logger.info(f"✓ 成功创建数据库: {settings.DB_NAME}")

        cursor.close()
        conn.close()

        return True

    except OperationalError as e:
        logger.error(f"❌ 连接失败: {e}")
        logger.info("\n请检查：")
        logger.info("1. PostgreSQL 是否已启动")
        logger.info("2. 用户名密码是否正确")
        logger.info(f"   - 用户名: {settings.DB_USER}")
        logger.info(f"   - 密码: {settings.DB_PASSWORD}")
        logger.info(f"   - 主机: {settings.DB_HOST}")
        logger.info(f"   - 端口: {settings.DB_PORT}")
        return False

    except Exception as e:
        logger.error(f"❌ 创建数据库失败: {e}")
        return False


if __name__ == "__main__":
    success = create_database()

    if success:
        logger.info("\n下一步：")
        logger.info("运行初始化脚本：python scripts/init_db.py")
        sys.exit(0)
    else:
        sys.exit(1)
