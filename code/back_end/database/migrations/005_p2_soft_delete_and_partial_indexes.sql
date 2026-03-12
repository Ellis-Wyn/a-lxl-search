-- =====================================================
-- P2 级数据库优化：软删除 + 部分索引
-- =====================================================
--
-- 功能说明：
-- 1. 软删除 (Soft Delete)
--    - 添加 deleted_at 字段到主要表
--    - 数据不会真正删除，仅标记删除时间
--    - 支持数据恢复和审计追溯
--
-- 2. 部分索引 (Partial Indexes)
--    - 仅对活跃数据（deleted_at IS NULL）创建索引
--    - 显著减少索引大小（通常 30-50% 的空间节省）
--    - 提升查询性能（更少的索引页需要扫描）
--
-- 作者：A_lxl_search Team
-- 创建日期：2026-03-12
-- =====================================================

-- =====================================================
-- 步骤 1/5: 添加软删除字段
-- =====================================================

-- 为 pipeline 表添加软删除字段
ALTER TABLE pipeline
ADD COLUMN IF NOT EXISTS deleted_at
TIMESTAMPTZ
DEFAULT NULL
COMMENT '软删除时间（NULL=未删除，非NULL=已删除）';

-- 为 target 表添加软删除字段
ALTER TABLE target
ADD COLUMN IF NOT EXISTS deleted_at
TIMESTAMPTZ
DEFAULT NULL
COMMENT '软删除时间（NULL=未删除，非NULL=已删除）';

-- 为 publication 表添加软删除字段（如果存在）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'publication') THEN
        ALTER TABLE publication
        ADD COLUMN IF NOT EXISTS deleted_at
        TIMESTAMPTZ
        DEFAULT NULL
        COMMENT '软删除时间（NULL=未删除，非NULL=已删除）';
    END IF;
END $$;

-- =====================================================
-- 步骤 2/5: 创建部分索引（仅索引活跃数据）
-- =====================================================

-- Pipeline 部分索引
-- 仅索引活跃的管线（deleted_at IS NULL）
-- 这些是 99% 查询需要的数据
CREATE INDEX IF NOT EXISTS ix_pipeline_active_drug_code
ON pipeline (drug_code)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_pipeline_active_company
ON pipeline (company_name)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_pipeline_active_phase
ON pipeline (phase)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_pipeline_active_status
ON pipeline (status)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_pipeline_active_modality
ON pipeline (modality)
WHERE deleted_at IS NULL;

-- 复合部分索引：活跃管线按公司+阶段
CREATE INDEX IF NOT EXISTS ix_pipeline_active_company_phase
ON pipeline (company_name, phase)
WHERE deleted_at IS NULL;

-- Target 部分索引
CREATE INDEX IF NOT EXISTS ix_target_active_standard_name
ON target (standard_name)
WHERE deleted_at IS NULL;

-- Publication 部分索引（如果表存在）
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
END $$;

-- =====================================================
-- 步骤 3/5: 为 deleted_at 创建索引（支持已删除数据查询）
-- =====================================================

-- 这些索引用于查询已删除数据（管理员功能）
CREATE INDEX IF NOT EXISTS ix_pipeline_deleted_at
ON pipeline (deleted_at)
WHERE deleted_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_target_deleted_at
ON target (deleted_at)
WHERE deleted_at IS NOT NULL;

-- =====================================================
-- 步骤 4/5: 创建软删除辅助函数
-- =====================================================

-- 软删除 Pipeline 的函数
CREATE OR REPLACE FUNCTION soft_delete_pipeline(p_pipeline_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE pipeline
    SET deleted_at = NOW()
    WHERE pipeline_id = p_pipeline_id AND deleted_at IS NULL;
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 恢复已删除的 Pipeline
CREATE OR REPLACE FUNCTION restore_pipeline(p_pipeline_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE pipeline
    SET deleted_at = NULL
    WHERE pipeline_id = p_pipeline_id AND deleted_at IS NOT NULL;
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 软删除 Target 的函数
CREATE OR REPLACE FUNCTION soft_delete_target(p_target_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE target
    SET deleted_at = NOW()
    WHERE target_id = p_target_id AND deleted_at IS NULL;
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 恢复已删除的 Target
CREATE OR REPLACE FUNCTION restore_target(p_target_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE target
    SET deleted_at = NULL
    WHERE target_id = p_target_id AND deleted_at IS NOT NULL;
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 步骤 5/5: 更新查询模式建议
-- =====================================================

-- 创建视图：仅活跃数据（方便查询）
CREATE OR REPLACE VIEW v_active_pipeline AS
SELECT *
FROM pipeline
WHERE deleted_at IS NULL;

CREATE OR REPLACE VIEW v_active_target AS
SELECT *
FROM target
WHERE deleted_at IS NULL;

-- 创建视图：已删除数据（方便审计）
CREATE OR REPLACE VIEW v_deleted_pipeline AS
SELECT *
FROM pipeline
WHERE deleted_at IS NOT NULL
ORDER BY deleted_at DESC;

CREATE OR REPLACE VIEW v_deleted_target AS
SELECT *
FROM target
WHERE deleted_at IS NOT NULL
ORDER BY deleted_at DESC;

-- =====================================================
-- 验证脚本
-- =====================================================

-- 验证 deleted_at 字段
SELECT
    table_name,
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name IN ('pipeline', 'target')
  AND column_name = 'deleted_at';

-- 验证部分索引
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'pipeline'
  AND indexname LIKE '%active%';

-- 查看索引大小对比
SELECT
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid::regclass)) AS index_size
FROM pg_stat_user_indexes
WHERE tablename IN ('pipeline', 'target')
  AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid::regclass) DESC;

-- =====================================================
-- 使用示例
-- =====================================================

/*
-- 软删除一个管线
SELECT soft_delete_pipeline('uuid-here');

-- 恢复已删除的管线
SELECT restore_pipeline('uuid-here');

-- 查询所有活跃管线（使用部分索引）
SELECT * FROM pipeline WHERE deleted_at IS NULL;

-- 查询所有活跃管线（使用视图）
SELECT * FROM v_active_pipeline;

-- 查询已删除的管线
SELECT * FROM v_deleted_pipeline;

-- 统计活跃/已删除数量
SELECT
    COUNT(*) FILTER (WHERE deleted_at IS NULL) AS active_count,
    COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted_count
FROM pipeline;
*/
