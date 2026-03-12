"""
=====================================================
创建 Pipeline Event 表
=====================================================

用于手动创建 pipeline_event 表
如果 init_database() 已被调用，表会自动创建
此脚本仅用于手动干预或调试

运行方式：
    python -m scripts.create_pipeline_event_table
=====================================================
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.database import engine, check_database_connection, Base
from models.pipeline_event import PipelineEvent
from loguru import logger

# 兼容处理
if not hasattr(logger, 'success'):
    logger.success = logger.info


def create_pipeline_event_table():
    """创建 pipeline_event 表"""
    logger.info("检查数据库连接...")

    if not check_database_connection():
        logger.error("数据库连接失败，请检查配置")
        return False

    logger.info("开始创建 pipeline_event 表...")

    try:
        # 只创建 pipeline_event 表
        PipelineEvent.__table__.create(engine, checkfirst=True)
        logger.success("✅ pipeline_event 表创建成功")
        return True

    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}")
        return False


def verify_table():
    """验证表是否创建成功"""
    try:
        with engine.connect() as conn:
            result = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'pipeline_event'
            """)
            count = result.scalar()

            if count > 0:
                logger.success("✅ pipeline_event 表已存在")

                # 检查索引
                indexes = conn.execute("""
                    SELECT indexname FROM pg_indexes
                    WHERE tablename = 'pipeline_event'
                """).fetchall()

                logger.info(f"  索引数量: {len(indexes)}")
                for idx in indexes:
                    logger.info(f"    - {idx[0]}")

                return True
            else:
                logger.warning("⚠️  pipeline_event 表不存在")
                return False

    except Exception as e:
        logger.error(f"验证失败: {e}")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Pipeline Event 表创建脚本")
    logger.info("=" * 60)

    # 创建表
    if create_pipeline_event_table():
        # 验证
        verify_table()
    else:
        logger.warning("提示：也可以运行 SQL 脚本手动创建：")
        logger.warning("  psql -U postgres -d drug_intelligence_db -f database/migrations/002_create_pipeline_event_table.sql")

    logger.info("=" * 60)
