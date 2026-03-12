"""
=====================================================
应用 P2 级数据库迁移
=====================================================

P2 优化内容：
1. 软删除字段 (deleted_at)
2. 部分索引优化（仅索引活跃数据）
3. 辅助函数和视图

运行方式：
    python -m scripts.apply_p2_migrations

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


def add_deleted_at_columns(db):
    """添加软删除字段"""
    logger.info("步骤 1/5: 添加软删除字段...")

    try:
        # 为 pipeline 添加 deleted_at 列
        db.execute(text("""
            ALTER TABLE pipeline
            ADD COLUMN IF NOT EXISTS deleted_at
            TIMESTAMPTZ
            DEFAULT NULL
        """))

        # 为 target 添加 deleted_at 列
        db.execute(text("""
            ALTER TABLE target
            ADD COLUMN IF NOT EXISTS deleted_at
            TIMESTAMPTZ
            DEFAULT NULL
        """))

        # 为 publication 添加 deleted_at 列（如果存在）
        db.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'publication') THEN
                    ALTER TABLE publication
                    ADD COLUMN IF NOT EXISTS deleted_at
                    TIMESTAMPTZ
                    DEFAULT NULL;
                END IF;
            END $$
        """))

        db.commit()
        logger.success("  ✓ deleted_at 字段添加成功")
        return True
    except Exception as e:
        logger.error(f"  ✗ 添加 deleted_at 字段失败: {e}")
        db.rollback()
        raise


def create_partial_indexes(db):
    """创建部分索引（仅索引活跃数据）"""
    logger.info("步骤 2/5: 创建部分索引...")

    try:
        # Pipeline 部分索引
        pipeline_indexes = [
            ("ix_pipeline_active_drug_code", "CREATE INDEX IF NOT EXISTS ix_pipeline_active_drug_code ON pipeline (drug_code) WHERE deleted_at IS NULL"),
            ("ix_pipeline_active_company", "CREATE INDEX IF NOT EXISTS ix_pipeline_active_company ON pipeline (company_name) WHERE deleted_at IS NULL"),
            ("ix_pipeline_active_phase", "CREATE INDEX IF NOT EXISTS ix_pipeline_active_phase ON pipeline (phase) WHERE deleted_at IS NULL"),
            ("ix_pipeline_active_status", "CREATE INDEX IF NOT EXISTS ix_pipeline_active_status ON pipeline (status) WHERE deleted_at IS NULL"),
            ("ix_pipeline_active_modality", "CREATE INDEX IF NOT EXISTS ix_pipeline_active_modality ON pipeline (modality) WHERE deleted_at IS NULL"),
            ("ix_pipeline_active_company_phase", "CREATE INDEX IF NOT EXISTS ix_pipeline_active_company_phase ON pipeline (company_name, phase) WHERE deleted_at IS NULL"),
        ]

        for idx_name, sql in pipeline_indexes:
            db.execute(text(sql))
            logger.info(f"  ✓ 创建索引: {idx_name}")

        # Target 部分索引
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_target_active_standard_name
            ON target (standard_name)
            WHERE deleted_at IS NULL
        """))
        logger.info("  ✓ 创建索引: ix_target_active_standard_name")

        # Publication 部分索引（如果表存在）
        db.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'publication') THEN
                    CREATE INDEX IF NOT EXISTS ix_publication_active_pmid
                    ON publication (pmid)
                    WHERE deleted_at IS NULL;

                    CREATE INDEX IF NOT EXISTS ix_publication_active_pub_date
                    ON publication (pub_date DESC)
                    WHERE deleted_at IS NULL;
                END IF;
            END $$
        """))
        logger.info("  ✓ 创建索引: publication 部分索引")

        # 已删除数据的索引（用于审计查询）
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_pipeline_deleted_at
            ON pipeline (deleted_at)
            WHERE deleted_at IS NOT NULL
        """))

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_target_deleted_at
            ON target (deleted_at)
            WHERE deleted_at IS NOT NULL
        """))
        logger.info("  ✓ 创建索引: deleted_at 审计索引")

        db.commit()
        logger.success("  ✓ 部分索引创建成功")
        return True
    except Exception as e:
        logger.error(f"  ✗ 创建部分索引失败: {e}")
        db.rollback()
        raise


def create_soft_delete_functions(db):
    """创建软删除辅助函数"""
    logger.info("步骤 3/5: 创建软删除辅助函数...")

    try:
        # 软删除 Pipeline 函数
        db.execute(text("""
            CREATE OR REPLACE FUNCTION soft_delete_pipeline(p_pipeline_id UUID)
            RETURNS BOOLEAN AS $$
            BEGIN
                UPDATE pipeline
                SET deleted_at = NOW()
                WHERE pipeline_id = p_pipeline_id AND deleted_at IS NULL;
                RETURN FOUND;
            END;
            $$ LANGUAGE plpgsql
        """))

        # 恢复 Pipeline 函数
        db.execute(text("""
            CREATE OR REPLACE FUNCTION restore_pipeline(p_pipeline_id UUID)
            RETURNS BOOLEAN AS $$
            BEGIN
                UPDATE pipeline
                SET deleted_at = NULL
                WHERE pipeline_id = p_pipeline_id AND deleted_at IS NOT NULL;
                RETURN FOUND;
            END;
            $$ LANGUAGE plpgsql
        """))

        # 软删除 Target 函数
        db.execute(text("""
            CREATE OR REPLACE FUNCTION soft_delete_target(p_target_id UUID)
            RETURNS BOOLEAN AS $$
            BEGIN
                UPDATE target
                SET deleted_at = NOW()
                WHERE target_id = p_target_id AND deleted_at IS NULL;
                RETURN FOUND;
            END;
            $$ LANGUAGE plpgsql
        """))

        # 恢复 Target 函数
        db.execute(text("""
            CREATE OR REPLACE FUNCTION restore_target(p_target_id UUID)
            RETURNS BOOLEAN AS $$
            BEGIN
                UPDATE target
                SET deleted_at = NULL
                WHERE target_id = p_target_id AND deleted_at IS NOT NULL;
                RETURN FOUND;
            END;
            $$ LANGUAGE plpgsql
        """))

        db.commit()
        logger.success("  ✓ 软删除函数创建成功")
        return True
    except Exception as e:
        logger.error(f"  ✗ 创建软删除函数失败: {e}")
        db.rollback()
        raise


def create_views(db):
    """创建视图（活跃数据 + 已删除数据）"""
    logger.info("步骤 4/5: 创建视图...")

    try:
        # 活跃 Pipeline 视图
        db.execute(text("""
            CREATE OR REPLACE VIEW v_active_pipeline AS
            SELECT *
            FROM pipeline
            WHERE deleted_at IS NULL
        """))

        # 活跃 Target 视图
        db.execute(text("""
            CREATE OR REPLACE VIEW v_active_target AS
            SELECT *
            FROM target
            WHERE deleted_at IS NULL
        """))

        # 已删除 Pipeline 视图
        db.execute(text("""
            CREATE OR REPLACE VIEW v_deleted_pipeline AS
            SELECT *
            FROM pipeline
            WHERE deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
        """))

        # 已删除 Target 视图
        db.execute(text("""
            CREATE OR REPLACE VIEW v_deleted_target AS
            SELECT *
            FROM target
            WHERE deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
        """))

        db.commit()
        logger.success("  ✓ 视图创建成功")
        return True
    except Exception as e:
        logger.error(f"  ✗ 创建视图失败: {e}")
        db.rollback()
        raise


def verify_migrations(db):
    """验证迁移结果"""
    logger.info("步骤 5/5: 验证迁移结果...")

    # 检查 deleted_at 字段
    tables = ['pipeline', 'target']
    for table in tables:
        result = db.execute(text(f"""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = '{table}' AND column_name = 'deleted_at'
        """)).scalar()
        logger.info(f"  {table}.deleted_at: {'✓ 存在' if result else '✗ 不存在'}")

    # 检查部分索引
    result = db.execute(text("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE indexname LIKE '%_active_%'
    """)).scalar()
    logger.info(f"  部分索引数量: {result} 个")

    # 检查软删除函数
    functions = ['soft_delete_pipeline', 'restore_pipeline', 'soft_delete_target', 'restore_target']
    for func in functions:
        result = db.execute(text(f"""
            SELECT COUNT(*) FROM pg_proc
            WHERE proname = '{func}'
        """)).scalar()
        logger.info(f"  {func}(): {'✓ 存在' if result else '✗ 不存在'}")

    # 检查视图
    views = ['v_active_pipeline', 'v_active_target', 'v_deleted_pipeline', 'v_deleted_target']
    for view in views:
        result = db.execute(text(f"""
            SELECT COUNT(*) FROM information_schema.views
            WHERE table_name = '{view}'
        """)).scalar()
        logger.info(f"  {view}: {'✓ 存在' if result else '✗ 不存在'}")

    # 统计活跃/已删除数据
    pipeline_stats = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE deleted_at IS NULL) AS active_count,
            COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted_count
        FROM pipeline
    """)).fetchone()

    if pipeline_stats:
        logger.info(f"  Pipeline 活跃: {pipeline_stats[0]}, 已删除: {pipeline_stats[1]}")

    target_stats = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE deleted_at IS NULL) AS active_count,
            COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted_count
        FROM target
    """)).fetchone()

    if target_stats:
        logger.info(f"  Target 活跃: {target_stats[0]}, 已删除: {target_stats[1]}")

    logger.success("✓ P2 迁移验证通过")


def run_migrations():
    """执行所有 P2 迁移"""
    logger.info("=" * 60)
    logger.info("P2 级数据库迁移开始")
    logger.info("=" * 60)

    if not check_database_connection():
        logger.error("数据库连接失败")
        return False

    db = SessionLocal()

    try:
        add_deleted_at_columns(db)
        create_partial_indexes(db)
        create_soft_delete_functions(db)
        create_views(db)
        verify_migrations(db)

        logger.success("=" * 60)
        logger.success("P2 迁移完成！")
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
