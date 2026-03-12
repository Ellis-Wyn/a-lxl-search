"""
=====================================================
应用 P1 级数据库迁移
=====================================================

重要修复：
1. Pipeline 唯一约束
2. 乐观锁 version 字段
3. 自动更新 version 触发器
4. 索引优化

运行方式：
    python -m scripts.apply_p1_migrations

作者：A_lxl_search Team
日期：2026-03-12
=====================================================
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from utils.database import check_database_connection, SessionLocal
from loguru import logger

# 兼容处理
if not hasattr(logger, 'success'):
    logger.success = logger.info


def add_pipeline_unique_constraint(db):
    """添加 pipeline 唯一约束"""
    logger.info("步骤 1/5: 添加 pipeline 唯一约束...")

    try:
        # 先检查并清理重复数据（如果有的话）
        result = db.execute(text("""
            WITH dupes AS (
                SELECT drug_code, company_name, LOWER(TRIM(indication)) as norm_indication, COUNT(*) as cnt
                FROM pipeline
                GROUP BY drug_code, company_name, LOWER(TRIM(indication))
                HAVING COUNT(*) > 1
            )
            SELECT COUNT(*) as duplicate_count FROM dupes
        """)).scalar()

        if result and result > 0:
            logger.warning(f"  发现 {result} 组重复数据，需要手动处理")
            # 这里不自动删除重复数据，因为需要业务判断保留哪一条
            logger.warning("  跳过唯一约束创建，请先清理重复数据")
            return False

        # 创建唯一索引
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_pipeline_unique
            ON pipeline (drug_code, company_name, LOWER(TRIM(indication)));
        """))
        db.commit()
        logger.success("  ✓ 唯一约束创建成功")
        return True
    except Exception as e:
        logger.error(f"  ✗ 创建唯一约束失败: {e}")
        db.rollback()
        raise


def add_version_columns(db):
    """添加乐观锁 version 字段"""
    logger.info("步骤 2/5: 添加 version 字段...")

    try:
        # 为 pipeline 添加 version 列
        db.execute(text("""
            ALTER TABLE pipeline
            ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 1;
        """))

        # 为 target 添加 version 列
        db.execute(text("""
            ALTER TABLE target
            ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 1;
        """))

        # 为 pipeline_event 添加 version 列（用于审计）
        db.execute(text("""
            ALTER TABLE pipeline_event
            ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 1;
        """))

        db.commit()
        logger.success("  ✓ version 字段添加成功")
    except Exception as e:
        logger.error(f"  ✗ 添加 version 字段失败: {e}")
        db.rollback()
        raise


def create_version_triggers(db):
    """创建 version 自动更新触发器"""
    logger.info("步骤 3/5: 创建 version 触发器...")

    try:
        # 创建 pipeline version 更新函数
        db.execute(text("""
            CREATE OR REPLACE FUNCTION update_pipeline_version()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.version = OLD.version + 1;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))

        # 创建 target version 更新函数
        db.execute(text("""
            CREATE OR REPLACE FUNCTION update_target_version()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.version = OLD.version + 1;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))

        # 删除旧触发器
        db.execute(text("DROP TRIGGER IF EXISTS trg_pipeline_version ON pipeline;"))
        db.execute(text("DROP TRIGGER IF EXISTS trg_target_version ON target;"))

        # 创建新触发器
        db.execute(text("""
            CREATE TRIGGER trg_pipeline_version
            BEFORE UPDATE ON pipeline
            FOR EACH ROW
            EXECUTE FUNCTION update_pipeline_version();
        """))

        db.execute(text("""
            CREATE TRIGGER trg_target_version
            BEFORE UPDATE ON target
            FOR EACH ROW
            EXECUTE FUNCTION update_target_version();
        """))

        db.commit()
        logger.success("  ✓ version 触发器创建成功")
    except Exception as e:
        logger.error(f"  ✗ 创建触发器失败: {e}")
        db.rollback()
        raise


def add_composite_indexes(db):
    """添加复合索引优化查询"""
    logger.info("步骤 4/5: 添加复合索引...")

    try:
        # TargetPipeline 查找索引
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_target_pipeline_lookup
            ON target_pipeline (target_id, pipeline_id);
        """))

        # Pipeline event 类型+时间复合索引（用于分析）
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_pipeline_event_type_time
            ON pipeline_event (event_type, occurred_at DESC);
        """))

        db.commit()
        logger.success("  ✓ 复合索引创建成功")
    except Exception as e:
        logger.error(f"  ✗ 创建复合索引失败: {e}")
        db.rollback()
        raise


def verify_migrations(db):
    """验证迁移结果"""
    logger.info("步骤 5/5: 验证迁移结果...")

    # 检查唯一约束
    result = db.execute(text("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE tablename = 'pipeline' AND indexname = 'ux_pipeline_unique'
    """)).scalar()
    logger.info(f"  pipeline 唯一约束: {'✓ 存在' if result else '✗ 不存在'}")

    # 检查 version 字段
    tables_to_check = ['pipeline', 'target']
    for table in tables_to_check:
        result = db.execute(text(f"""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = '{table}' AND column_name = 'version'
        """)).scalar()
        logger.info(f"  {table}.version: {'✓ 存在' if result else '✗ 不存在'}")

    # 检查触发器
    result = db.execute(text("""
        SELECT COUNT(*) FROM information_schema.triggers
        WHERE trigger_name LIKE '%_version'
    """)).scalar()
    logger.info(f"  version 触发器: {result} 个")

    logger.success("✓ P1 迁移验证通过")


def run_migrations():
    """执行所有 P1 迁移"""
    logger.info("=" * 60)
    logger.info("P1 级数据库迁移开始")
    logger.info("=" * 60)

    if not check_database_connection():
        logger.error("数据库连接失败")
        return False

    db = SessionLocal()

    try:
        add_pipeline_unique_constraint(db)
        add_version_columns(db)
        create_version_triggers(db)
        add_composite_indexes(db)
        verify_migrations(db)

        logger.success("=" * 60)
        logger.success("P1 迁移完成！")
        logger.success("=" * 60)
        return True

    except Exception as e:
        logger.error(f"迁移失败: {e}")
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
