-- =====================================================
-- P0 Critical Fixes - 关键修复
-- 优先级：P0（立即执行）
-- 目标：防止脏数据，提升查询性能
-- =====================================================

-- =====================================================
-- 1. Phase 字段 CHECK 约束（防止无效数据）
-- =====================================================

-- 创建 ENUM 类型（更严格的类型检查）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'phase_enum') THEN
        CREATE TYPE phase_enum AS ENUM (
            'preclinical',  -- 临床前
            'I',            -- I期
            'II',           -- II期
            'III',          -- III期
            'filing',       -- 申报中
            'approved'      -- 已批准
        );
    END IF;
END $$;

-- 修改 pipeline.phase 列类型（注意：需要先处理现有数据）
-- 首先标准化现有数据
UPDATE pipeline
SET phase = CASE
    WHEN LOWER(phase) LIKE '%preclinical%' OR LOWER(phase) LIKE '%临床前%' THEN 'preclinical'
    WHEN LOWER(phase) LIKE '%phase i%' OR LOWER(phase) LIKE '%i期%' OR phase = 'I' THEN 'I'
    WHEN LOWER(phase) LIKE '%phase ii%' OR LOWER(phase) LIKE '%ii期%' OR phase = 'II' THEN 'II'
    WHEN LOWER(phase) LIKE '%phase iii%' OR LOWER(phase) LIKE '%iii期%' OR phase = 'III' THEN 'III'
    WHEN LOWER(phase) LIKE '%filing%' OR LOWER(phase) LIKE '%申报%' THEN 'filing'
    WHEN LOWER(phase) LIKE '%approved%' OR LOWER(phase) LIKE '%批准%' OR LOWER(phase) LIKE '%上市%' THEN 'approved'
    ELSE 'preclinical'  -- 默认值
END
WHERE phase::text NOT IN ('preclinical', 'I', 'II', 'III', 'filing', 'approved');

-- 修改列类型
ALTER TABLE pipeline
    ALTER COLUMN phase TYPE phase_enum
    USING phase::text::phase_enum;

-- 添加注释
COMMENT ON COLUMN pipeline.phase IS '研发阶段（标准枚举值）：preclinical/I/II/III/filing/approved';


-- =====================================================
-- 2. Target.aliases GIN 索引（提升 JSONB 查询性能）
-- =====================================================

-- 添加 GIN 索引用于 JSONB 数组查询
CREATE INDEX IF NOT EXISTS ix_target_aliases_gin
    ON target USING GIN (aliases);

COMMENT ON INDEX ix_target_aliases_gin IS 'GIN索引用于别名数组查询，支持 @> && 等操作符';


-- =====================================================
-- 3. Pipeline status CHECK 约束
-- =====================================================

-- 添加 status 约束
ALTER TABLE pipeline
    ADD CONSTRAINT chk_pipeline_status
    CHECK (status IN ('active', 'discontinued', 'suspended'));

COMMENT ON COLUMN pipeline.status IS '管线状态：active(活跃)/discontinued(已终止)/suspended(暂停)';


-- =====================================================
-- 4. Pipeline modality 常用值约束（软约束）
-- =====================================================

-- 添加 modality 注释说明允许的值
COMMENT ON COLUMN pipeline.modality IS '药物类型（常用值）：Small Molecule/ADC/Bispecific/Monoclonal Antibody/CAR-T/PROTAC/RNA/Others';


-- =====================================================
-- 5. TargetPipeline relation_type 约束
-- =====================================================

-- 添加 relation_type 约束
ALTER TABLE target_pipeline
    ADD CONSTRAINT chk_relation_type
    CHECK (relation_type IN (
        'targets',       -- 针对
        'inhibits',      -- 抑制
        'antibody_to',   -- 抗体结合
        'agonist_of',    -- 激动
        'activates',     -- 激活
        'binds_to',      -- 结合
        'degrades'       -- 降解
    ));


-- =====================================================
-- 验证脚本
-- =====================================================

-- 检查 phase 枚举是否生效
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'pipeline'
  AND column_name = 'phase';

-- 检查索引是否创建
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'target'
  AND indexname LIKE '%gin%';

-- 检查约束是否生效
SELECT
    conname,
    pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'pipeline'::regclass
  AND contype = 'c';
