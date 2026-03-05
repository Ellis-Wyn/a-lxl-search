"""
=====================================================
端到端测试脚本
=====================================================

测试完整的数据流程：
1. 数据库 CRUD 操作
2. PubMed 数据入库
3. Pipeline 变化检测
4. Target-Publication/Pipeline 关联

运行方式：
    cd code/back_end
    python tests/test_e2e.py

前置条件：
    - PostgreSQL 已启动
    - 已运行 scripts/init_db.py 初始化数据库
=====================================================
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import SessionLocal, check_database_connection
from services.database_service import get_db_service
from services.pubmed_service import PubmedService
from services.pipeline_service import PipelineService
from core.logger import setup_logger, get_logger

# 初始化日志
setup_logger(app_name="e2e_test", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


# =====================================================
# 测试辅助函数
# =====================================================


def cleanup_test_data():
    """清理测试数据"""
    from utils.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        # 删除测试数据
        db.execute(text("DELETE FROM target_publication WHERE pmid = '99999999'"))
        db.execute(text("DELETE FROM target_pipeline WHERE pipeline_id IN (SELECT pipeline_id FROM pipeline WHERE drug_code = 'TEST-001')"))
        db.execute(text("DELETE FROM pipeline WHERE drug_code = 'TEST-001'"))
        db.execute(text("DELETE FROM publication WHERE pmid = '99999999'"))
        db.execute(text("DELETE FROM target WHERE standard_name = 'TEST_TARGET'"))
        db.commit()
        logger.info("✓ 测试数据已清理")
    except Exception as e:
        db.rollback()
        logger.debug(f"清理测试数据（可选）: {e}")
    finally:
        db.close()


# =====================================================
# 测试函数
# =====================================================


async def test_database_crud():
    """测试 1: 数据库 CRUD 操作"""
    logger.info("=" * 60)
    logger.info("测试 1: 数据库 CRUD 操作")
    logger.info("=" * 60)

    with get_db_service() as db:
        # 测试 1.1: 创建靶点
        logger.info("创建测试靶点...")
        target = db.create_target({
            "standard_name": "TEST_TARGET",
            "aliases": ["Test Alias", "T-Target"],
            "gene_id": "99999",
            "uniprot_id": "Q99999",
            "category": "测试激酶",
            "description": "这是一个测试靶点"
        })
        logger.info(f"  ✓ 创建成功: {target.standard_name} (ID: {target.target_id})")

        # 测试 1.2: 查询靶点
        logger.info("\n查询靶点...")
        found = db.get_target_by_name("TEST_TARGET")
        assert found is not None, "查询失败"
        assert found.standard_name == "TEST_TARGET"
        logger.info(f"  ✓ 查询成功: {found.standard_name}")

        # 测试 1.3: 搜索靶点
        logger.info("\n搜索靶点...")
        results = db.search_targets("TEST", limit=10)
        assert len(results) > 0, "搜索失败"
        logger.info(f"  ✓ 搜索成功: 找到 {len(results)} 条结果")

        # 测试 1.4: 创建文献
        logger.info("\n创建测试文献...")
        pub = db.create_publication({
            "pmid": "99999999",
            "title": "Test Article for E2E Testing",
            "abstract": "This is a test article for end-to-end testing.",
            "pub_date": datetime.now().date(),
            "journal": "Test Journal",
            "mesh_terms": ["Testing", "Quality Assurance"],
            "clinical_data_tags": [{"metric": "ORR", "value": "50%"}]
        })
        logger.info(f"  ✓ 创建成功: PMID {pub.pmid}")

        # 测试 1.5: 创建管线
        logger.info("\n创建测试管线...")
        pipeline = db.create_pipeline({
            "drug_code": "TEST-001",
            "company_name": "Test Company",
            "indication": "Test Cancer",
            "phase": "Phase 2",
            "modality": "单抗",
            "source_url": "https://test.com/pipeline/test-001",
        })
        logger.info(f"  ✓ 创建成功: {pipeline.drug_code} (ID: {pipeline.pipeline_id})")

        # 测试 1.6: 关联靶点-文献
        logger.info("\n关联靶点和文献...")
        tp_link = db.link_target_publication(
            target_id=str(target.target_id),
            pmid="99999999",
            relation_type="mentions",
            evidence_snippet="This article mentions TEST_TARGET"
        )
        logger.info(f"  ✓ 关联成功")

        # 测试 1.7: 关联靶点-管线
        logger.info("\n关联靶点和管线...")
        tgt_link = db.link_target_pipeline(
            target_id=str(target.target_id),
            pipeline_id=str(pipeline.pipeline_id),
            relation_type="inhibits",
            is_primary=True,
        )
        logger.info(f"  ✓ 关联成功")

        # 测试 1.8: 查询靶点相关文献
        logger.info("\n查询靶点相关文献...")
        publications = db.get_publications_by_target(
            target_id=str(target.target_id),
            limit=10,
        )
        logger.info(f"  ✓ 查询成功: 找到 {len(publications)} 篇文献")
        for pub in publications:
            logger.info(f"    - {pub.pmid}: {pub.title[:50]}...")

        # 测试 1.9: 查询靶点相关管线
        logger.info("\n查询靶点相关管线...")
        pipelines = db.get_pipelines_by_target(
            target_id=str(target.target_id),
            limit=10,
        )
        logger.info(f"  ✓ 查询成功: 找到 {len(pipelines)} 条管线")
        for pl in pipelines:
            logger.info(f"    - {pl.drug_code}: {pl.phase}")

    logger.info("✓ 数据库 CRUD 测试通过\n")


async def test_pubmed_integration():
    """测试 2: PubMed 集成（真实 API）"""
    logger.info("=" * 60)
    logger.info("测试 2: PubMed API 集成")
    logger.info("=" * 60)

    async with PubmedService() as service:
        # 测试 2.1: 搜索文献
        logger.info("搜索 EGFR 相关文献（限制 5 条）...")
        from services.pubmed_service import QueryConfig

        config = QueryConfig(
            max_results=5,
            date_range_days=365,
        )

        publications = await service.search_by_target(
            target_name="EGFR",
            config=config,
            custom_keywords=["inhibitor"],
        )

        logger.info(f"  ✓ 搜索完成: 找到 {len(publications)} 篇文献")

        if publications:
            # 显示前 3 篇
            for i, pub in enumerate(publications[:3], 1):
                logger.info(f"  [{i}] PMID: {pub['pmid']}")
                logger.info(f"      标题: {pub['title'][:60]}...")
                logger.info(f"      综合得分: {pub['relevance_score']}")

            # 测试 2.2: 将第一篇文献入库
            if publications:
                first_pub = publications[0]
                logger.info(f"\n将第一篇文献入库: {first_pub['pmid']}...")

                with get_db_service() as db:
                    created = db.create_publication({
                        "pmid": first_pub['pmid'],
                        "title": first_pub['title'],
                        "abstract": first_pub.get('abstract'),
                        "pub_date": datetime.strptime(first_pub['pub_date'], "%Y-%m-%d").date() if first_pub.get('pub_date') else None,
                        "journal": first_pub.get('journal'),
                        "mesh_terms": first_pub.get('mesh_terms', []),
                        "clinical_data_tags": first_pub.get('clinical_data_tags', []),
                        "publication_type": first_pub.get('publication_type'),
                    })

                    logger.info(f"  ✓ 入库成功: PMID {created.pmid}")

                    # 关联到 EGFR 靶点
                    egfr_target = db.get_target_by_name("EGFR")
                    if egfr_target:
                        db.link_target_publication(
                            target_id=str(egfr_target.target_id),
                            pmid=created.pmid,
                            relation_type="mentions",
                        )
                        logger.info(f"  ✓ 关联成功: EGFR -> PMID {created.pmid}")

    logger.info("✓ PubMed 集成测试通过\n")


async def test_pipeline_monitoring():
    """测试 3: Pipeline 变化检测"""
    logger.info("=" * 60)
    logger.info("测试 3: Pipeline 变化检测")
    logger.info("=" * 60)

    service = PipelineService()

    # 模拟旧管线数据
    old_pipelines = [
        {
            "pipeline_id": "test-001-old",
            "drug_code": "TEST-001",
            "company_name": "Test Company",
            "indication": "Test Cancer",
            "phase": "Phase 2",
            "phase_normalized": "Phase 2",
            "first_seen_at": datetime.utcnow() - timedelta(days=100),
            "last_seen_at": datetime.utcnow() - timedelta(days=10),
        },
    ]

    # 模拟新管线数据（Phase Jump）
    new_pipelines = [
        {
            "drug_code": "TEST-001",
            "indication": "Test Cancer",
            "phase": "Phase 3",  # Phase Jump: 2 -> 3
            "modality": "单抗",
            "source_url": "https://test.com/pipeline/test-001",
        },
    ]

    # 执行变化检测
    logger.info("执行变化检测...")
    report = await service.update_and_detect(
        company_name="Test Company",
        new_pipelines=new_pipelines,
        disappeared_threshold_days=180,
    )

    logger.info(f"\n检测结果:")
    logger.info(f"  总变化: {report.total_changes}")
    logger.info(f"  新增: {len(report.new_pipelines)}")
    logger.info(f"  Phase Jump: {len(report.phase_jumps)}")
    logger.info(f"  消失: {len(report.disappeared_pipelines)}")

    # 显示 Phase Jump
    if report.phase_jumps:
        logger.info(f"\n  ⚠️ Phase Jump 事件:")
        for jump in report.phase_jumps:
            logger.info(f"    - {jump.drug_code}: {jump.old_phase} -> {jump.new_phase}")

    logger.info("✓ Pipeline 变化检测测试通过\n")


def test_statistics():
    """测试 4: 统计信息"""
    logger.info("=" * 60)
    logger.info("测试 4: 数据统计")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # 统计各表数据量
        from models.target import Target
        from models.publication import Publication
        from models.pipeline import Pipeline

        target_count = db.query(Target).count()
        publication_count = db.query(Publication).count()
        pipeline_count = db.query(Pipeline).count()

        logger.info("数据统计：")
        logger.info(f"  Target（靶点）:      {target_count} 条")
        logger.info(f"  Publication（文献）: {publication_count} 条")
        logger.info(f"  Pipeline（管线）:    {pipeline_count} 条")

        # Phase 分布
        from sqlalchemy import func
        phase_dist = db.query(
            Pipeline.phase,
            func.count(Pipeline.pipeline_id)
        ).group_by(Pipeline.phase).all()

        logger.info("\nPhase 分布:")
        for phase, count in phase_dist:
            logger.info(f"  {phase}: {count} 条")

        # 公司管线数
        company_dist = db.query(
            Pipeline.company_name,
            func.count(Pipeline.pipeline_id)
        ).group_by(
            Pipeline.company_name
        ).order_by(
            func.count(Pipeline.pipeline_id).desc()
        ).limit(5).all()

        logger.info("\n公司管线数 TOP 5:")
        for company, count in company_dist:
            logger.info(f"  {company}: {count} 条")

    finally:
        db.close()

    logger.info("✓ 统计测试通过\n")


async def main():
    """主测试函数"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 16 + "端到端测试" + " " * 34 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")

    # 检查数据库连接
    logger.info("检查数据库连接...")
    if not check_database_connection():
        logger.error("❌ 数据库连接失败！")
        logger.info("\n请先运行: python scripts/init_db.py")
        return 1
    logger.info("✅ 数据库连接正常\n")

    # 清理测试数据
    logger.info("清理测试数据...")
    cleanup_test_data()

    try:
        # 测试 1: 数据库 CRUD
        await test_database_crud()

        # 测试 2: PubMed 集成
        await test_pubmed_integration()

        # 测试 3: Pipeline 监控
        await test_pipeline_monitoring()

        # 测试 4: 统计信息
        test_statistics()

        logger.info("=" * 60)
        logger.info("✅ 所有端到端测试通过！")
        logger.info("=" * 60)
        logger.info("\n系统已就绪，可以：")
        logger.info("1. 启动 API 服务: python main.py")
        logger.info("2. 访问 API 文档: http://localhost:8000/docs")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
