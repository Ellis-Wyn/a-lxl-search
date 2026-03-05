"""
=====================================================
数据模型测试脚本
=====================================================

测试功能：
1. 数据库连接
2. ORM模型创建
3. 数据库CRUD操作
4. 关联查询

运行方式：
    python test_models.py
=====================================================
"""

from datetime import date, datetime
from loguru import logger

# 导入模型
from models import (
    Target,
    Publication,
    Pipeline,
    TargetPublication,
    TargetPipeline,
    create_target,
    create_publication,
    create_pipeline,
    link_target_publication,
    link_target_pipeline
)
from utils.database import get_db_context, init_database, check_database_connection


def test_database_connection():
    """测试数据库连接"""
    logger.info("=" * 60)
    logger.info("测试 1: 数据库连接")
    logger.info("=" * 60)

    if check_database_connection():
        logger.success("✅ 数据库连接成功")
        return True
    else:
        logger.error("❌ 数据库连接失败")
        return False


def test_create_models():
    """测试创建模型对象"""
    logger.info("=" * 60)
    logger.info("测试 2: 创建模型对象")
    logger.info("=" * 60)

    # 创建靶点
    target = create_target(
        standard_name="EGFR",
        aliases=["ERBB1", "HER1"],
        gene_id="1956",
        uniprot_id="P00533"
    )
    logger.info(f"✅ 创建靶点: {target.standard_name}")

    # 创建文献
    publication = create_publication(
        pmid="12345678",
        title="EGFR inhibitor in NSCLC",
        abstract="This is a test abstract",
        pub_date=date.today(),
        journal="J Clin Oncol",
        publication_type="Clinical Trial"
    )
    logger.info(f"✅ 创建文献: PMID {publication.pmid}")

    # 创建管线
    pipeline = create_pipeline(
        drug_code="TestDrug",
        company_name="恒瑞医药",
        indication="非小细胞肺癌",
        phase="III",
        source_url="https://example.com"
    )
    logger.info(f"✅ 创建管线: {pipeline.drug_code}")

    return target, publication, pipeline


def test_insert_to_database(target, publication, pipeline):
    """测试插入数据库"""
    logger.info("=" * 60)
    logger.info("测试 3: 插入数据库")
    logger.info("=" * 60)

    try:
        with get_db_context() as db:
            # 插入靶点
            db.add(target)
            db.flush()  # 获取target_id
            logger.info(f"✅ 插入靶点: {target.target_id}")

            # 插入文献
            db.add(publication)
            logger.info(f"✅ 插入文献: {publication.pmid}")

            # 插入管线
            db.add(pipeline)
            logger.info(f"✅ 插入管线: {pipeline.drug_code}")

            # 创建关联
            tp1 = link_target_publication(
                target, publication,
                relation_type="focus_on",
                evidence_snippet="This paper focuses on EGFR"
            )
            db.add(tp1)
            logger.info(f"✅ 创建靶点-文献关联")

            tp2 = link_target_pipeline(
                target, pipeline,
                relation_type="inhibits",
                is_primary=True
            )
            db.add(tp2)
            logger.info(f"✅ 创建靶点-管线关联")

        logger.success("✅ 所有数据插入成功")
        return True

    except Exception as e:
        logger.error(f"❌ 插入失败: {e}")
        return False


def test_query_from_database():
    """测试查询数据库"""
    logger.info("=" * 60)
    logger.info("测试 4: 查询数据库")
    logger.info("=" * 60)

    try:
        with get_db_context() as db:
            # 查询靶点
            target = db.query(Target).filter(Target.standard_name == "EGFR").first()
            if target:
                logger.info(f"✅ 查询到靶点: {target.standard_name}")
                logger.info(f"   - 别名: {target.aliases}")
                logger.info(f"   - Gene ID: {target.gene_id}")

            # 查询关联的文献
            publications = target.publications if target else []
            logger.info(f"✅ 关联文献数: {len(publications)}")

            for tp in publications:
                logger.info(f"   - PMID: {tp.pmid}, 关系: {tp.relation_type}")

            # 查询关联的管线
            pipelines = target.pipelines if target else []
            logger.info(f"✅ 关联管线数: {len(pipelines)}")

            for tp in pipelines:
                pipeline = tp.pipeline
                logger.info(f"   - 药物: {pipeline.drug_code}, 阶段: {pipeline.phase}")

        logger.success("✅ 查询成功")
        return True

    except Exception as e:
        logger.error(f"❌ 查询失败: {e}")
        return False


def test_model_methods():
    """测试模型方法"""
    logger.info("=" * 60)
    logger.info("测试 5: 模型方法")
    logger.info("=" * 60)

    try:
        with get_db_context() as db:
            # 测试靶点方法
            target = db.query(Target).filter(Target.standard_name == "EGFR").first()
            if target:
                logger.info(f"✅ 靶点所有名称: {target.get_all_names()}")
                logger.info(f"✅ 是否包含别名ERBB1: {target.has_alias('ERBB1')}")

            # 测试文献方法
            publication = db.query(Publication).filter(Publication.pmid == "12345678").first()
            if publication:
                logger.info(f"✅ 距发布天数: {publication.get_days_since_publication()}")
                logger.info(f"✅ 时效性得分: {publication.calculate_recency_score()}")

            # 测试管线方法
            pipeline = db.query(Pipeline).filter(Pipeline.drug_code == "TestDrug").first()
            if pipeline:
                logger.info(f"✅ 首次发现天数: {pipeline.get_days_since_first_seen()}")
                logger.info(f"✅ 最近更新天数: {pipeline.get_days_since_last_seen()}")
                logger.info(f"✅ 是否已消失: {pipeline.is_disappeared()}")
                logger.info(f"✅ 阶段排序值: {pipeline.get_phase_order()}")

        logger.success("✅ 所有方法测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 方法测试失败: {e}")
        return False


def test_serialization():
    """测试序列化"""
    logger.info("=" * 60)
    logger.info("测试 6: 序列化（to_dict）")
    logger.info("=" * 60)

    try:
        with get_db_context() as db:
            # 测试靶点序列化
            target = db.query(Target).filter(Target.standard_name == "EGFR").first()
            if target:
                target_dict = target.to_dict(include_relations=True)
                logger.info(f"✅ 靶点序列化: {len(target_dict)} 个字段")

            # 测试文献序列化
            publication = db.query(Publication).filter(Publication.pmid == "12345678").first()
            if publication:
                pub_dict = publication.to_dict(include_relations=True)
                logger.info(f"✅ 文献序列化: {len(pub_dict)} 个字段")

            # 测试管线序列化
            pipeline = db.query(Pipeline).filter(Pipeline.drug_code == "TestDrug").first()
            if pipeline:
                pipeline_dict = pipeline.to_dict(include_relations=True)
                logger.info(f"✅ 管线序列化: {len(pipeline_dict)} 个字段")

        logger.success("✅ 序列化测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 序列化测试失败: {e}")
        return False


def cleanup_test_data():
    """清理测试数据"""
    logger.info("=" * 60)
    logger.info("清理测试数据")
    logger.info("=" * 60)

    try:
        with get_db_context() as db:
            # 删除关联
            db.query(TargetPublication).filter(TargetPublication.pmid == "12345678").delete()
            db.query(TargetPipeline).filter(TargetPipeline.pipeline_id == Pipeline.pipeline_id).delete()

            # 删除主表
            db.query(Publication).filter(Publication.pmid == "12345678").delete()
            db.query(Pipeline).filter(Pipeline.drug_code == "TestDrug").delete()
            db.query(Target).filter(Target.standard_name == "EGFR").delete()

        logger.info("✅ 测试数据已清理")
        return True

    except Exception as e:
        logger.error(f"❌ 清理失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🚀 开始数据模型测试")
    logger.info("")

    # 测试1: 数据库连接
    if not test_database_connection():
        logger.error("数据库连接失败，请检查配置")
        return

    # 测试2: 创建模型对象
    target, publication, pipeline = test_create_models()

    # 测试3: 插入数据库
    if not test_insert_to_database(target, publication, pipeline):
        logger.error("插入数据库失败")
        return

    # 测试4: 查询数据库
    if not test_query_from_database():
        logger.error("查询数据库失败")
        cleanup_test_data()
        return

    # 测试5: 模型方法
    if not test_model_methods():
        logger.error("模型方法测试失败")
        cleanup_test_data()
        return

    # 测试6: 序列化
    if not test_serialization():
        logger.error("序列化测试失败")
        cleanup_test_data()
        return

    # 清理测试数据
    cleanup_test_data()

    # 完成
    logger.info("")
    logger.success("=" * 60)
    logger.success("✅ 所有测试通过！数据模型工作正常")
    logger.success("=" * 60)


if __name__ == "__main__":
    main()
