"""
=====================================================
应用 P0 级数据库迁移
=====================================================

关键修复：
1. Phase 字段 CHECK 约束（使用 ENUM）
2. Target.aliases GIN 索引
3. Pipeline status 约束
4. TargetPipeline relation_type 约束

运行方式：
    python -m scripts.apply_p0_migrations

作者：A_lxl_search Team
日期：2026-03-12
=====================================================
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, create_engine
from utils.database import engine, check_database_connection
from loguru import logger

# 兼容处理
if not hasattr(logger, 'success'):
    logger.success = logger.info


# =====================================================
# 迁移步骤
# =====================================================

def create_phase_enum(db):
    """创建 phase ENUM 类型"""
    logger.info("步骤 1/7: 创建 phase_enum 类型...")

    try:
        db.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'phase_enum') THEN
                    CREATE TYPE phase_enum AS ENUM (
                        'preclinical',
                        'I',
                        'II',
                        'III',
                        'filing',
                        'approved'
                    );
                END IF;
            END $$;
        """))
        db.commit()
        logger.success("  ✓ phase_enum 类型创建成功")
    except Exception as e:
        logger.error(f"  ✗ 创建 phase_enum 失败: {e}")
        raise


def standardize_existing_phases(db):
    """标准化现有的 phase 数据"""
    logger.info("步骤 2/7: 标准化现有 phase 数据...")

    try:
        # 检查 phase 列是否已经是 ENUM 类型
        column_type = db.execute(text("""
            SELECT udt_name
            FROM information_schema.columns
            WHERE table_name = 'pipeline' AND column_name = 'phase'
        """)).scalar()

        if column_type == 'phase_enum':
            logger.info("  phase 列已经是 ENUM 类型，跳过标准化")
            return

        # 如果还是 VARCHAR，执行标准化
        result = db.execute(text("""
            UPDATE pipeline
            SET phase = CASE
                WHEN LOWER(phase::text) LIKE '%preclinical%' OR LOWER(phase::text) LIKE '%临床前%' THEN 'preclinical'
                WHEN LOWER(phase::text) LIKE '%phase i%' OR LOWER(phase::text) LIKE '%i期%' OR phase::text = 'I' THEN 'I'
                WHEN LOWER(phase::text) LIKE '%phase ii%' OR LOWER(phase::text) LIKE '%ii期%' OR phase::text = 'II' THEN 'II'
                WHEN LOWER(phase::text) LIKE '%phase iii%' OR LOWER(phase::text) LIKE '%iii期%' OR phase::text = 'III' THEN 'III'
                WHEN LOWER(phase::text) LIKE '%filing%' OR LOWER(phase::text) LIKE '%申报%' THEN 'filing'
                WHEN LOWER(phase::text) LIKE '%approved%' OR LOWER(phase::text) LIKE '%批准%' OR LOWER(phase::text) LIKE '%上市%' THEN 'approved'
                ELSE 'preclinical'
            END
            WHERE phase::text NOT IN ('preclinical', 'I', 'II', 'III', 'filing', 'approved')
        """))
        db.commit()
        logger.success(f"  ✓ 标准化了 {result.rowcount} 条记录")
    except Exception as e:
        logger.error(f"  ✗ 标准化 phase 失败: {e}")
        raise


def alter_phase_column_type(db):
    """修改 phase 列类型为 ENUM"""
    logger.info("步骤 3/7: 修改 phase 列类型...")

    try:
        # 先检查是否有默认值，有则删除
        check_default = db.execute(text("""
            SELECT column_default
            FROM information_schema.columns
            WHERE table_name = 'pipeline' AND column_name = 'phase'
        """)).scalar()

        if check_default:
            db.execute(text("""
                ALTER TABLE pipeline ALTER COLUMN phase DROP DEFAULT;
            """))

        # 修改列类型
        db.execute(text("""
            ALTER TABLE pipeline
            ALTER COLUMN phase TYPE phase_enum
            USING phase::text::phase_enum;
        """))

        db.commit()
        logger.success("  ✓ phase 列类型修改成功")
    except Exception as e:
        logger.error(f"  ✗ 修改 phase 列类型失败: {e}")
        raise


def add_aliases_gin_index(db):
    """添加 aliases GIN 索引"""
    logger.info("步骤 4/7: 添加 target.aliases GIN 索引...")

    try:
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_target_aliases_gin
            ON target USING GIN (aliases);
        """))
        db.commit()
        logger.success("  ✓ GIN 索引创建成功")
    except Exception as e:
        logger.error(f"  ✗ 创建 GIN 索引失败: {e}")
        raise


def add_pipeline_status_constraint(db):
    """添加 pipeline status 约束"""
    logger.info("步骤 5/7: 添加 pipeline status 约束...")

    try:
        # 先标准化现有数据
        db.execute(text("""
            UPDATE pipeline
            SET status = CASE
                WHEN status IS NULL THEN 'active'
                WHEN status NOT IN ('active', 'discontinued', 'suspended') THEN 'active'
                ELSE status
            END;
        """))

        # 检查约束是否已存在
        existing = db.execute(text("""
            SELECT COUNT(*) FROM pg_constraint
            WHERE conrelid = 'pipeline'::regclass
              AND conname = 'chk_pipeline_status'
        """)).scalar()

        if existing == 0:
            # 添加约束
            db.execute(text("""
                ALTER TABLE pipeline
                ADD CONSTRAINT chk_pipeline_status
                CHECK (status IN ('active', 'discontinued', 'suspended'));
            """))
        else:
            logger.info("  status 约束已存在，跳过")

        db.commit()
        logger.success("  ✓ status 约束添加成功")
    except Exception as e:
        logger.error(f"  ✗ 添加 status 约束失败: {e}")
        raise


def add_target_pipeline_relation_constraint(db):
    """添加 target_pipeline relation_type 约束"""
    logger.info("步骤 6/7: 添加 target_pipeline relation_type 约束...")

    try:
        # 先标准化现有数据
        db.execute(text("""
            UPDATE target_pipeline
            SET relation_type = 'targets'
            WHERE relation_type IS NULL OR relation_type = '';
        """))

        # 检查约束是否已存在
        existing = db.execute(text("""
            SELECT COUNT(*) FROM pg_constraint
            WHERE conrelid = 'target_pipeline'::regclass
              AND conname = 'chk_relation_type'
        """)).scalar()

        if existing == 0:
            # 添加约束
            db.execute(text("""
                ALTER TABLE target_pipeline
                ADD CONSTRAINT chk_relation_type
                CHECK (relation_type IN (
                    'targets', 'inhibits', 'antibody_to',
                    'agonist_of', 'activates', 'binds_to', 'degrades'
                ));
            """))
        else:
            logger.info("  relation_type 约束已存在，跳过")

        db.commit()
        logger.success("  ✓ relation_type 约束添加成功")
    except Exception as e:
        logger.error(f"  ✗ 添加 relation_type 约束失败: {e}")
        raise


def verify_migrations(db):
    """验证迁移结果"""
    logger.info("步骤 7/7: 验证迁移结果...")

    # 检查 phase_enum
    result = db.execute(text("""
        SELECT EXISTS(SELECT 1 FROM pg_type WHERE typname = 'phase_enum')
    """)).scalar()
    logger.info(f"  phase_enum 存在: {result}")

    # 检查 GIN 索引
    result = db.execute(text("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE tablename = 'target' AND indexdef LIKE '%USING gin%'
    """)).scalar()
    logger.info(f"  target GIN 索引数量: {result}")

    # 检查 pipeline 约束
    result = db.execute(text("""
        SELECT COUNT(*) FROM pg_constraint
        WHERE conrelid = 'pipeline'::regclass AND conname = 'chk_pipeline_status'
    """)).scalar()
    logger.info(f"  pipeline 约束存在: {result > 0}")

    # 统计各阶段管线数量
    result = db.execute(text("""
        SELECT phase, COUNT(*) as cnt
        FROM pipeline
        GROUP BY phase
        ORDER BY phase
    """)).fetchall()
    logger.info("  当前管线阶段分布:")
    for row in result:
        logger.info(f"    {row[0]}: {row[1]}")

    logger.success("✓ 所有迁移验证通过")


# =====================================================
# 主函数
# =====================================================

def run_migrations():
    """执行所有 P0 迁移"""
    logger.info("=" * 60)
    logger.info("P0 级数据库迁移开始")
    logger.info("=" * 60)

    # 检查数据库连接
    if not check_database_connection():
        logger.error("数据库连接失败，请检查配置")
        return False

    from utils.database import SessionLocal
    db = SessionLocal()

    try:
        # 执行迁移步骤
        create_phase_enum(db)
        standardize_existing_phases(db)
        alter_phase_column_type(db)
        add_aliases_gin_index(db)
        add_pipeline_status_constraint(db)
        add_target_pipeline_relation_constraint(db)
        verify_migrations(db)

        logger.success("=" * 60)
        logger.success("P0 迁移完成！")
        logger.success("=" * 60)
        return True

    except Exception as e:
        logger.error(f"迁移失败: {e}")
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    import sys
    success = run_migrations()
    sys.exit(0 if success else 1)
