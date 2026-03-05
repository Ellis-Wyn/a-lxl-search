"""
=====================================================
数据库迁移：爬虫调度系统增强
=====================================================

创建表：
- crawler_execution_log: 爬虫执行日志表
- crawler_stats: 爬虫统计数据汇总表

使用方式：
    python scripts/migrate_crawler_enhancement.py
    python scripts/migrate_crawler_enhancement.py rollback  # 回滚
=====================================================
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import engine, SessionLocal, Base
from sqlalchemy import text, inspect
from core.logger import setup_logger, get_logger

# 导入新模型（用于创建表）
from models.crawler_execution_log import CrawlerExecutionLog
from models.crawler_statistics import CrawlerStatistics

# 初始化日志
setup_logger(app_name="migration", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


def check_table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate():
    """执行迁移"""
    logger.info("=" * 60)
    logger.info("Starting migration: Crawler Enhancement")
    logger.info("=" * 60)

    try:
        # =====================================================
        # 1. 创建 crawler_execution_log 表
        # =====================================================
        if not check_table_exists('crawler_execution_log'):
            logger.info("Creating table: crawler_execution_log")
            CrawlerExecutionLog.metadata.create_all(bind=engine)
            logger.info("✅ Created crawler_execution_log table")
        else:
            logger.info("ℹ️  Table crawler_execution_log already exists")

        # =====================================================
        # 2. 创建 crawler_stats 表
        # =====================================================
        if not check_table_exists('crawler_stats'):
            logger.info("Creating table: crawler_stats")
            CrawlerStatistics.metadata.create_all(bind=engine)
            logger.info("✅ Created crawler_stats table")
        else:
            logger.info("ℹ️  Table crawler_stats already exists")

        # =====================================================
        # 3. 创建额外索引
        # =====================================================
        logger.info("\nCreating additional indexes...")

        indexes_to_create = [
            # crawler_execution_log 索引
            (
                "idx_crawler_log_spider_started",
                "CREATE INDEX IF NOT EXISTS idx_crawler_log_spider_started "
                "ON crawler_execution_log(spider_name, started_at DESC)"
            ),
            (
                "idx_crawler_log_status_started",
                "CREATE INDEX IF NOT EXISTS idx_crawler_log_status_started "
                "ON crawler_execution_log(status, started_at DESC)"
            ),
            # crawler_stats 索引
            (
                "idx_crawler_stats_consecutive_failures",
                "CREATE INDEX IF NOT EXISTS idx_crawler_stats_consecutive_failures "
                "ON crawler_stats(consecutive_failures) "
                "WHERE consecutive_failures > 0"
            ),
        ]

        with engine.connect() as conn:
            for index_name, sql in indexes_to_create:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    logger.info(f"✅ Created index: {index_name}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"⚠️  Failed to create index {index_name}: {e}")

        # =====================================================
        # 4. 验证迁移结果
        # =====================================================
        logger.info("\n" + "=" * 60)
        logger.info("Verifying migration...")
        logger.info("=" * 60)

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        required_tables = ['crawler_execution_log', 'crawler_stats']
        missing = [t for t in required_tables if t not in tables]

        if missing:
            logger.error(f"❌ Migration failed! Missing tables: {missing}")
            return 1

        # 显示表结构
        for table in required_tables:
            if table in tables:
                columns = inspector.get_columns(table)
                logger.info(f"\n📋 Table: {table}")
                for col in columns:
                    logger.info(f"   - {col['name']}: {col['type']}")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 60)
        return 0

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def rollback():
    """回滚迁移"""
    logger.info("=" * 60)
    logger.info("Rolling back migration: Crawler Enhancement")
    logger.info("=" * 60)

    try:
        # 删除表（注意顺序：先删除有外键的表）
        tables_to_drop = ['crawler_stats', 'crawler_execution_log']

        with engine.connect() as conn:
            for table in tables_to_drop:
                if check_table_exists(table):
                    logger.info(f"Dropping table: {table}")
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    conn.commit()
                    logger.info(f"✅ Dropped {table}")
                else:
                    logger.info(f"ℹ️  Table {table} does not exist")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Rollback completed!")
        logger.info("=" * 60)
        return 0

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """主程序"""
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        return rollback()
    else:
        return migrate()


if __name__ == "__main__":
    sys.exit(main())
