"""
=====================================================
PubMed 模块测试脚本
=====================================================

测试内容：
1. PubmedClient: API 客户端功能
2. PubmedParser: XML 解析功能
3. PubmedService: 智能查询和排序功能

运行方式：
    cd code/back_end
    python tests/test_pubmed.py
=====================================================
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawlers.pubmed_client import PubmedClient
from crawlers.pubmed_parser import PubmedParser
from services.pubmed_service import PubmedService, QueryConfig
from core.logger import setup_logger, get_logger

# 初始化日志
setup_logger(app_name="pubmed_test", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


# =====================================================
# 测试数据
# =====================================================

TEST_TARGET = "EGFR"
TEST_KEYWORDS = ["inhibitor", "tyrosine kinase"]
TEST_DISEASES = ["lung cancer"]
TEST_MAX_RESULTS = 5


# =====================================================
# 测试函数
# =====================================================


async def test_pubmed_client():
    """测试 PubMed API 客户端"""
    logger.info("=" * 60)
    logger.info("测试 1: PubmedClient 基础功能")
    logger.info("=" * 60)

    async with PubmedClient() as client:
        # 测试 1.1: 搜索文献
        logger.info(f"搜索靶点: {TEST_TARGET}")
        pmids = await client.search(
            query=TEST_TARGET,
            max_results=TEST_MAX_RESULTS,
        )

        logger.info(f"✓ 搜索完成，找到 {len(pmids)} 篇文献")
        if pmids:
            logger.info(f"  示例 PMID: {pmids[0]}")

        # 测试 1.2: 获取文献详情
        if pmids:
            logger.info(f"获取前 3 篇文献详情...")
            publications = await client.fetch_details(pmids[:3])

            logger.info(f"✓ 获取详情完成，共 {len(publications)} 篇")
            for pub in publications:
                logger.info(f"  PMID: {pub['pmid']}")
                logger.info(f"  标题: {pub['title'][:80]}...")
                logger.info(f"  期刊: {pub.get('journal', 'N/A')}")
                logger.info(f"  MeSH: {len(pub.get('mesh_terms', []))} 个")

        # 测试 1.3: 智能查询构建
        logger.info("测试智能查询构建...")
        query = client.build_smart_query(
            target_name=TEST_TARGET,
            keywords=TEST_KEYWORDS,
            mesh_terms=["Carcinoma, Non-Small Cell Lung"],
        )
        logger.info(f"✓ 查询字符串: {query[:100]}...")

    logger.info("✓ PubmedClient 测试通过\n")


async def test_pubmed_parser():
    """测试 PubMed 解析器"""
    logger.info("=" * 60)
    logger.info("测试 2: PubmedParser 解析功能")
    logger.info("=" * 60)

    parser = PubmedParser()

    # 测试 2.1: 从 API 获取数据并解析
    async with PubmedClient() as client:
        pmids = await client.search(
            query=f"{TEST_TARGET} inhibitor",
            max_results=2,
        )

        if pmids:
            xml_text = await client._request_efetch(pmids)
            publications = parser.parse_xml(xml_text)

            logger.info(f"✓ 解析完成，共 {len(publications)} 篇文献")

            for pub in publications:
                logger.info(f"  PMID: {pub['pmid']}")
                logger.info(f"  标题: {pub['title'][:80]}...")
                logger.info(f"  摘要长度: {len(pub.get('abstract', ''))}")
                logger.info(f"  MeSH 术语: {pub.get('mesh_terms', [])[:3]}...")
                logger.info(f"  临床数据: {pub.get('clinical_data_tags', [])}")

    # 测试 2.2: 测试来源类型识别
    logger.info("测试来源类型识别...")
    test_cases = [
        ("J Clin Oncol", "JCO"),
        ("N Engl J Med", "NEJM"),
        ("Lancet Oncol", "LANCET"),
        ("ASCO Annual Meeting", "ASCO"),
    ]

    for journal, expected in test_cases:
        source_type = parser._identify_source_type(journal)
        status = "✓" if source_type == expected else "✗"
        logger.info(f"  {status} {journal} -> {source_type} (期望: {expected})")

    logger.info("✓ PubmedParser 测试通过\n")


async def test_pubmed_service():
    """测试 PubMed 智能服务"""
    logger.info("=" * 60)
    logger.info("测试 3: PubmedService 智能查询与排序")
    logger.info("=" * 60)

    async with PubmedService() as service:
        # 测试 3.1: 智能查询
        config = QueryConfig(
            max_results=5,
            date_range_days=365,
            include_clinical_trials=True,
        )

        publications = await service.search_by_target(
            target_name=TEST_TARGET,
            config=config,
            custom_keywords=TEST_KEYWORDS,
            diseases=TEST_DISEASES,
        )

        logger.info(f"✓ 智能查询完成，找到 {len(publications)} 篇文献")

        # 显示前 3 篇
        for i, pub in enumerate(publications[:3], 1):
            logger.info(f"\n  [{i}] PMID: {pub['pmid']}")
            logger.info(f"      标题: {pub['title'][:80]}...")
            logger.info(f"      综合得分: {pub['relevance_score']}")
            logger.info(f"      - 时效性: {pub['recency_score']}")
            logger.info(f"      - 临床数据: {pub['clinical_score']}")
            logger.info(f"      - 来源: {pub['source_score']}")
            logger.info(f"      - 关键词匹配: {pub['keyword_match_score']}")
            logger.info(f"      来源: {pub.get('source_type') or pub.get('journal', 'N/A')}")

        # 测试 3.2: 智能查询构建
        logger.info("\n测试智能查询字符串构建...")
        query = service.build_smart_query(
            target_name=TEST_TARGET,
            keywords=TEST_KEYWORDS,
            diseases=TEST_DISEASES,
        )
        logger.info(f"✓ 智能查询: {query[:150]}...")

        # 测试 3.3: MeSH 同义词扩展
        logger.info("\n测试 MeSH 同义词扩展...")
        for target in ["EGFR", "HER2", "PD-1"]:
            query = service._build_target_query(target, use_synonyms=True)
            logger.info(f"  {target}: {query[:80]}...")

    logger.info("✓ PubmedService 测试通过\n")


async def test_ranking_algorithm():
    """测试排序算法细节"""
    logger.info("=" * 60)
    logger.info("测试 4: 排序算法细节")
    logger.info("=" * 60)

    service = PubmedService()

    # 模拟文献数据
    mock_pubs = [
        {
            "pmid": "12345678",
            "title": "Phase III trial of EGFR inhibitor in NSCLC with ORR 45%",
            "abstract": "This study shows ORR 45% and PFS 11.2 months.",
            "journal": "J Clin Oncol",
            "pub_date": "2024-01-15",  # 最近
            "publication_type": "Clinical Trial",
            "source_type": "JCO",
            "clinical_data_tags": [
                {"metric": "ORR", "value": "45%"},
                {"metric": "PFS", "value": "11.2m"},
            ],
            "mesh_terms": [],
        },
        {
            "pmid": "87654321",
            "title": "EGFR mutations in cancer",
            "abstract": "Review of EGFR biology.",
            "journal": "Nature",
            "pub_date": "2023-06-01",  # 较早
            "publication_type": "Review",
            "source_type": "NATURE",
            "clinical_data_tags": [],
            "mesh_terms": [],
        },
        {
            "pmid": "11112222",
            "title": "ASCO: EGFR TKI in lung cancer",
            "abstract": "n=200, ORR 55%, OS 25 months",
            "journal": "J Clin Oncol",
            "pub_date": "2023-12-01",
            "publication_type": "Clinical Trial",
            "source_type": "ASCO",
            "clinical_data_tags": [
                {"metric": "ORR", "value": "55%"},
                {"metric": "OS", "value": "25m"},
            ],
            "mesh_terms": [],
        },
    ]

    ranked = service.rank_publications(
        publications=mock_pubs,
        target_name="EGFR",
        keywords=["inhibitor", "TKI"],
    )

    logger.info("排序结果：")
    for i, pub in enumerate(ranked, 1):
        logger.info(f"\n  [{i}] PMID: {pub['pmid']}")
        logger.info(f"      综合得分: {pub['relevance_score']}")
        logger.info(f"      时效性: {pub['recency_score']}")
        logger.info(f"      临床: {pub['clinical_score']}")
        logger.info(f"      来源: {pub['source_score']}")
        logger.info(f"      关键词: {pub['keyword_match_score']}")

    await service.close()
    logger.info("✓ 排序算法测试通过\n")


async def main():
    """主测试函数"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 10 + "PubMed 模块测试" + " " * 36 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")

    try:
        # 测试 1: 客户端
        await test_pubmed_client()

        # 测试 2: 解析器
        await test_pubmed_parser()

        # 测试 3: 服务
        await test_pubmed_service()

        # 测试 4: 排序算法
        await test_ranking_algorithm()

        logger.info("=" * 60)
        logger.info("✓ 所有测试通过！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
