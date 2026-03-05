"""
=====================================================
数据库初始化脚本
=====================================================

功能：
1. 检查数据库连接
2. 创建所有表（通过 ORM）
3. 插入种子数据（示例靶点）
4. 验证数据完整性

运行方式：
    cd code/back_end
    python scripts/init_db.py
=====================================================
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import engine, SessionLocal, check_database_connection, init_database
from core.logger import setup_logger, get_logger

# 导入所有模型（确保 ORM 能识别所有表）
from models.target import Target
from models.publication import Publication
from models.pipeline import Pipeline
from models.relationships import TargetPublication, TargetPipeline
from models.cde_event import CDEEvent
from models.crawler_execution_log import CrawlerExecutionLog
from models.crawler_statistics import CrawlerStatistics

# 初始化日志
setup_logger(app_name="init_db", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


# =====================================================
# 种子数据
# =====================================================

SEED_TARGETS = [
    {
        "standard_name": "EGFR",
        "aliases": ["ERBB1", "HER1"],
        "gene_id": "1956",
        "uniprot_id": "P00533",
        "category": "激酶",
        "description": "表皮生长因子受体，肺癌靶向治疗的主要靶点"
    },
    {
        "standard_name": "HER2",
        "aliases": ["ERBB2", "c-ErbB2"],
        "gene_id": "2064",
        "uniprot_id": "P04626",
        "category": "激酶",
        "description": "人表皮生长因子受体2，乳腺癌重要靶点"
    },
    {
        "standard_name": "PD-1",
        "aliases": ["PDCD1", "CD279"],
        "gene_id": "5133",
        "uniprot_id": "Q15116",
        "category": "免疫检查点",
        "description": "程序性死亡受体1，免疫治疗关键靶点"
    },
    {
        "standard_name": "PD-L1",
        "aliases": ["CD274"],
        "gene_id": "29126",
        "uniprot_id": "Q9NZQ7",
        "category": "免疫检查点",
        "description": "程序性死亡配体1"
    },
    {
        "standard_name": "ALK",
        "aliases": ["Anaplastic Lymphoma Kinase"],
        "gene_id": "238",
        "uniprot_id": "Q9UM73",
        "category": "激酶",
        "description": "间变性淋巴瘤激酶，NSCLC 靶向治疗靶点"
    },
    {
        "standard_name": "VEGFR",
        "aliases": ["VEGFR1", "FLT1"],
        "gene_id": "2321",
        "uniprot_id": "P17948",
        "category": "激酶",
        "description": "血管内皮生长因子受体"
    },
]


# =====================================================
# 初始化函数
# =====================================================


def check_and_create_database():
    """检查并创建数据库"""
    logger.info("=" * 60)
    logger.info("步骤 1: 检查数据库连接")
    logger.info("=" * 60)

    if not check_database_connection():
        logger.error("❌ 数据库连接失败！")
        logger.info("\n请检查：")
        logger.info("1. PostgreSQL 是否已安装并启动")
        logger.info("2. 数据库用户名密码是否正确（.env 文件）")
        logger.info("3. 数据库是否已创建")
        return False

    logger.info("✅ 数据库连接正常\n")
    return True


def create_tables():
    """创建所有表"""
    logger.info("=" * 60)
    logger.info("步骤 2: 创建数据表")
    logger.info("=" * 60)

    try:
        init_database()
        logger.info("✅ 所有表创建成功\n")
        return True
    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}\n")
        return False


def insert_seed_data():
    """插入种子数据"""
    logger.info("=" * 60)
    logger.info("步骤 3: 插入种子数据")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing_count = db.query(Target).count()
        if existing_count > 0:
            logger.info(f"数据库已有 {existing_count} 条靶点数据，跳过插入\n")
            return True

        # 插入靶点数据
        for target_data in SEED_TARGETS:
            target = Target(**target_data)
            db.add(target)

        db.commit()

        logger.info(f"✅ 成功插入 {len(SEED_TARGETS)} 条靶点数据")
        for target in SEED_TARGETS:
            logger.info(f"  - {target['standard_name']}: {target['description'][:30]}...")

        logger.info("")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 插入种子数据失败: {e}\n")
        return False
    finally:
        db.close()


def verify_data():
    """验证数据完整性"""
    logger.info("=" * 60)
    logger.info("步骤 4: 验证数据完整性")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # 统计各表数据量
        target_count = db.query(Target).count()
        publication_count = db.query(Publication).count()
        pipeline_count = db.query(Pipeline).count()
        cde_event_count = db.query(CDEEvent).count()

        logger.info("数据统计：")
        logger.info(f"  Target（靶点）:        {target_count} 条")
        logger.info(f"  Publication（文献）:   {publication_count} 条")
        logger.info(f"  Pipeline（管线）:      {pipeline_count} 条")
        logger.info(f"  CDEEvent（CDE事件）:   {cde_event_count} 条")

        # 显示靶点列表
        if target_count > 0:
            logger.info("\n靶点列表：")
            targets = db.query(Target).all()
            for t in targets:
                aliases_str = ", ".join(t.aliases[:2]) if t.aliases else "无"
                logger.info(f"  - {t.standard_name} (别名: {aliases_str})")

        # 显示CDE事件统计（如果有）
        if cde_event_count > 0:
            logger.info("\nCDE事件统计：")
            from sqlalchemy import func
            event_type_stats = db.query(
                CDEEvent.event_type,
                func.count(CDEEvent.acceptance_no)
            ).group_by(CDEEvent.event_type).all()

            for event_type, count in event_type_stats:
                logger.info(f"  - {event_type}: {count} 条")

        logger.info("\n✅ 数据验证通过\n")
        return True

    except Exception as e:
        logger.error(f"❌ 数据验证失败: {e}\n")
        return False
    finally:
        db.close()


def print_next_steps():
    """打印后续步骤"""
    logger.info("=" * 60)
    logger.info("数据库初始化完成！")
    logger.info("=" * 60)
    logger.info("\n下一步：")
    logger.info("1. 运行端到端测试：")
    logger.info("   python tests/test_e2e.py")
    logger.info("\n2. 启动 API 服务：")
    logger.info("   python main.py")
    logger.info("\n3. 访问 API 文档：")
    logger.info("   http://localhost:8000/docs")
    logger.info("=" * 60)


# =====================================================
# 主函数
# =====================================================


def main():
    """主函数"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 18 + "数据库初始化" + " " * 30 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")

    # 步骤 1: 检查数据库连接
    if not check_and_create_database():
        return 1

    # 步骤 2: 创建表
    if not create_tables():
        return 1

    # 步骤 3: 插入种子数据
    if not insert_seed_data():
        return 1

    # 步骤 4: 验证数据
    if not verify_data():
        return 1

    # 打印后续步骤
    print_next_steps()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
