-- =====================================================
-- P1 Important Fixes - 重要修复
-- 优先级：P1
-- 目标：数据一致性保证、并发安全
-- =====================================================

-- =====================================================
-- 1. Pipeline 唯一约束（防止重复数据）
-- =====================================================

-- 添加唯一约束：(drug_code, company_name, normalized_indication)
-- 使用 LOWER + TRIM 确保一致性
CREATE UNIQUE INDEX IF NOT EXISTS ux_pipeline_unique
ON pipeline (drug_code, company_name, LOWER(TRIM(indication)));

COMMENT ON INDEX ux_pipeline_unique IS '管线唯一约束：同一公司的同一药物代码+适应症组合唯一';


-- =====================================================
-- 2. 添加乐观锁 version 字段（并发安全）
-- =====================================================

-- 添加 version 列
ALTER TABLE pipeline
    ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 1;

COMMENT ON COLUMN pipeline.version IS '乐观锁版本号，每次更新自动递增';

-- 为 target 表也添加 version
ALTER TABLE target
    ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 1;

COMMENT ON COLUMN target.version IS '乐观锁版本号';


-- =====================================================
-- 3. 创建触发器自动更新 version
-- =====================================================

-- Pipeline version 更新触发器
CREATE OR REPLACE FUNCTION update_pipeline_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 删除旧触发器（如果存在）
DROP TRIGGER IF EXISTS trg_pipeline_version ON pipeline;

-- 创建新触发器
CREATE TRIGGER trg_pipeline_version
    BEFORE UPDATE ON pipeline
    FOR EACH ROW
    EXECUTE FUNCTION update_pipeline_version();

COMMENT ON TRIGGER trg_pipeline_version IS '每次更新 pipeline 时自动递增 version';

-- Target version 更新触发器
CREATE OR REPLACE FUNCTION update_target_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_target_version ON target;

CREATE TRIGGER trg_target_version
    BEFORE UPDATE ON target
    FOR EACH ROW
    EXECUTE FUNCTION update_target_version();

COMMENT ON TRIGGER trg_target_version IS '每次更新 target 时自动递增 version';


-- =====================================================
-- 4. PipelineEvent 索引优化
-- =====================================================

-- 复合索引用于查询某管线的最近事件
-- 已在之前创建，这里补充注释
COMMENT ON INDEX ix_pipeline_event_timeline IS '时间线索引：按管线ID+时间倒序，用于获取最近事件';


-- =====================================================
-- 5. TargetPipeline 复合索引优化
-- =====================================================

-- 为常用查询添加复合索引
CREATE INDEX IF NOT EXISTS ix_target_pipeline_lookup
ON target_pipeline (target_id, pipeline_id);

COMMENT ON INDEX ix_target_pipeline_lookup IS '靶点-管线查找索引';


-- =====================================================
-- 验证脚本
-- =====================================================

-- 检查唯一约束
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'pipeline'
  AND indexname = 'ux_pipeline_unique';

-- 检查 version 字段
SELECT
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'pipeline'
  AND column_name = 'version';

-- 检查触发器
SELECT
    trigger_name,
    event_manipulation,
    action_statement
FROM information_schema.triggers
WHERE event_object_table = 'pipeline'
  AND trigger_name LIKE '%version%';
