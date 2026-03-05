"""
=====================================================
数据库迁移：添加Pipeline表新字段
=====================================================

添加字段：
- discontinued_at: 终止时间
- is_combination: 是否联合用药
- combination_drugs: 联合用药列表(JSON)

使用方式：
    python scripts/migrate_add_pipeline_fields.py
=====================================================
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import engine, SessionLocal
from sqlalchemy import text, inspect
from core.logger import setup_logger, get_logger

# 初始化日志
setup_logger(app_name="migration", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


def check_column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    """执行迁移"""
    logger.info("Starting migration: Add pipeline fields")

    # 检查当前表结构
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('pipeline')]
    logger.info(f"Current columns: {columns}")

    # 检查并添加 discontinued_at 字段
    if not check_column_exists('pipeline', 'discontinued_at'):
        logger.info("Adding column: discontinued_at")
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE pipeline
                ADD COLUMN discontinued_at TIMESTAMP NULL
                COMMENT '终止时间（当status=discontinued时记录）'
            """))
            conn.commit()
        logger.info("✅ Added discontinued_at column")
    else:
        logger.info("ℹ️  Column discontinued_at already exists")

    # 检查并添加 is_combination 字段
    if not check_column_exists('pipeline', 'is_combination'):
        logger.info("Adding column: is_combination")
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE pipeline
                ADD COLUMN is_combination BOOLEAN NOT NULL DEFAULT FALSE
                COMMENT '是否为联合用药'
            """))
            conn.commit()
        logger.info("✅ Added is_combination column")
    else:
        logger.info("ℹ️  Column is_combination already exists")

    # 检查并添加 combination_drugs 字段
    if not check_column_exists('pipeline', 'combination_drugs'):
        logger.info("Adding column: combination_drugs")
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE pipeline
                ADD COLUMN combination_drugs TEXT NULL
                COMMENT '联合用药列表(JSON格式): [\"HRS-1234\", \"HRS-5678\"]'
            """))
            conn.commit()
        logger.info("✅ Added combination_drugs column")
    else:
        logger.info("ℹ️  Column combination_drugs already exists")

    # 创建索引
    logger.info("Creating indexes...")

    indexes_to_create = [
        ("idx_pipeline_is_combination", "CREATE INDEX IF NOT EXISTS idx_pipeline_is_combination ON pipeline(is_combination)"),
    ]

    with engine.connect() as conn:
        for index_name, sql in indexes_to_create:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info(f"✅ Created index: {index_name}")
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning(f"⚠️  Failed to create index {index_name}: {e}")

    # 更新status字段默认值为active
    logger.info("Updating status field default value...")
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                ALTER TABLE pipeline
                ALTER COLUMN status SET DEFAULT 'active'
            """))
            conn.commit()
            logger.info("✅ Updated status default value")
        except Exception as e:
            logger.warning(f"⚠️  Failed to update status default: {e}")

    # 验证迁移结果
    logger.info("\nVerifying migration...")
    inspector = inspect(engine)
    new_columns = [col['name'] for col in inspector.get_columns('pipeline')]
    logger.info(f"New columns: {new_columns}")

    required_columns = ['discontinued_at', 'is_combination', 'combination_drugs']
    missing = [col for col in required_columns if col not in new_columns]

    if missing:
        logger.error(f"❌ Migration failed! Missing columns: {missing}")
        return 1

    logger.info("✅ Migration completed successfully!")
    return 0


def main():
    """主程序"""
    try:
        return migrate()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
