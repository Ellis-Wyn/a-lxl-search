"""
=====================================================
PubMed 智能查询服务
=====================================================

功能：
- 智能查询构建（关键词扩展 + MeSH 同义词）
- 文献排序算法（相关性 + 时效性 + 临床数据）
- Target-Publication 关联逻辑
- 缓存管理（避免重复查询）

使用示例：
    service = PubmedService()

    # 查询 EGFR 相关文献
    results = await service.search_by_target(
        target_name="EGFR",
        max_results=50
    )

    for pub in results:
        print(f"{pub['title']}: {pub['relevance_score']}")
=====================================================
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass

from crawlers.pubmed_client import PubmedClient
from crawlers.pubmed_parser import PubmedParser
from core.logger import get_logger
from core.retry import RetryPolicy
from services.cache_service import CacheService

# 集成新工具模块
from utils.target_gene_mapping import expand_search_query, add_clinical_filter
from utils.scoring_algorithms import calculate_publication_score

logger = get_logger(__name__)


# MeSH 同义词字典（常见靶点）
MESH_SYNONYMS = {
    "EGFR": ["Epidermal Growth Factor Receptor", "ErbB1"],
    "HER2": ["ERBB2", "Human Epidermal Growth Factor Receptor 2"],
    "VEGFR": ["Vascular Endothelial Growth Factor Receptor"],
    "PD-1": ["PDCD1", "Programmed Cell Death 1"],
    "PD-L1": ["CD274", "Programmed Cell Death Ligand 1"],
    "CTLA-4": ["CTLA4", "Cytotoxic T-Lymphocyte Antigen 4"],
    "ALK": ["Anaplastic Lymphoma Kinase"],
    "ROS1": ["ROS Proto-Oncogene 1"],
    "BRAF": ["B-Raf Proto-Oncogene"],
    "KRAS": ["Kirsten Rat Sarcoma Viral Oncogene"],
    "PI3K": ["Phosphatidylinositol 3-Kinase"],
}


# 疾病 MeSH 术语
DISEASE_MESH_TERMS = {
    "lung cancer": ["Carcinoma, Non-Small Cell Lung", "Lung Neoplasms"],
    "breast cancer": ["Breast Neoplasms"],
    "colorectal cancer": ["Colorectal Neoplasms"],
    "glioblastoma": ["Glioblastoma"],
    "melanoma": ["Melanoma"],
}


@dataclass
class QueryConfig:
    """查询配置"""
    max_results: int = 100
    date_range_days: int = 365  # 默认最近一年
    include_clinical_trials: bool = True
    include_reviews: bool = False
    min_relevance_score: float = 0.0


@dataclass
class PublicationScore:
    """文献得分"""
    pmid: str
    title: str
    relevance_score: float  # 综合得分
    recency_score: int  # 时效性得分
    clinical_score: int  # 临床数据得分
    source_score: int  # 来源期刊得分
    keyword_match_score: float  # 关键词匹配得分


class PubmedService:
    """
    PubMed 智能查询服务

    核心功能：
    1. search_by_target(): 根据靶点搜索文献
    2. build_smart_query(): 构建智能查询（支持同义词扩展）
    3. rank_publications(): 文献排序
    4. save_to_database(): 保存到数据库
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_enabled: bool = True,
        cache_service: Optional[CacheService] = None,
    ):
        """
        初始化服务

        Args:
            api_key: NCBI API Key
            cache_enabled: 是否启用缓存（已废弃，使用 cache_service）
            cache_service: Redis 缓存服务
        """
        self.client = PubmedClient(api_key=api_key)
        self.parser = PubmedParser()
        self.cache_enabled = cache_enabled
        self._query_cache: Dict[str, List[Dict]] = {}
        self.cache = cache_service  # Redis 缓存服务

    @RetryPolicy.create_retry("EXTERNAL_API")
    async def search_by_target(
        self,
        target_name: str,
        config: Optional[QueryConfig] = None,
        custom_keywords: Optional[List[str]] = None,
        diseases: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据靶点搜索文献（智能查询）

        带重试机制：网络失败时自动重试，最多5次，指数退避

        Args:
            target_name: 靶点名称，如 "EGFR"
            config: 查询配置
            custom_keywords: 自定义关键词，如 ["inhibitor", "TKI"]
            diseases: 疾病类型，如 ["lung cancer"]

        Returns:
            排序后的文献列表

        Example:
            >>> service = PubmedService()
            >>> results = await service.search_by_target("EGFR")
            >>> print(len(results))
            50
        """
        config = config or QueryConfig()

        # =====================================================
        # 缓存检查
        # =====================================================
        if self.cache:
            cache_key = CacheService.generate_pubmed_cache_key(
                target=target_name,
                keywords=custom_keywords
            )
            cached_result = self.cache.get(cache_key)

            if cached_result is not None:
                logger.info(f"Cache hit for PubMed search: {target_name}")
                return cached_result

        # 构建智能查询
        query = self.build_smart_query(
            target_name=target_name,
            keywords=custom_keywords,
            diseases=diseases,
        )

        # 计算日期范围
        date_range = self._calculate_date_range(config.date_range_days)

        # 构建文献类型过滤
        pub_types = []
        if config.include_clinical_trials:
            pub_types.append("Clinical Trial")
        if config.include_reviews:
            pub_types.append("Review")

        # 执行查询
        publications = await self.client.search_and_fetch(
            query=query,
            max_results=config.max_results,
            date_range=date_range,
            publication_types=pub_types if pub_types else None,
        )

        # 计算得分并排序
        ranked = self.rank_publications(
            publications=publications,
            target_name=target_name,
            keywords=custom_keywords,
        )

        # 过滤低分结果
        if config.min_relevance_score > 0:
            ranked = [
                p for p in ranked
                if p["relevance_score"] >= config.min_relevance_score
            ]

        logger.info(
            f"Search completed for target: {target_name}",
            extra={
                "total_results": len(ranked),
                "query": query[:100],
            }
        )

        # =====================================================
        # 写入缓存
        # =====================================================
        if self.cache and ranked:
            cache_key = CacheService.generate_pubmed_cache_key(
                target=target_name,
                keywords=custom_keywords
            )
            self.cache.set(cache_key, ranked, ttl=7200)  # 2小时
            logger.debug(f"Cached PubMed search result: {target_name}")

        return ranked

    def build_smart_query(
        self,
        target_name: str,
        keywords: Optional[List[str]] = None,
        diseases: Optional[List[str]] = None,
        use_synonyms: bool = True,
    ) -> str:
        """
        构建智能查询字符串（集成靶点-基因映射表）

        Args:
            target_name: 靶点名称
            keywords: 额外关键词
            diseases: 疾病类型
            use_synonyms: 是否使用同义词扩展（已废弃，默认使用扩展查询）

        Returns:
            PubMed 查询字符串

        Example:
            >>> service = PubmedService()
            >>> query = service.build_smart_query("EGFR", diseases=["lung cancer"])
            >>> print(query)
            '(("EGFR"[Gene/Protein Name] OR "ERBB1"[Gene/Protein Name] OR "HER1"[Gene/Protein Name] OR "Epidermal Growth Factor Receptor"[Title/Abstract])) AND (Clinical Trial[Filter] OR "Phase") AND ("lung cancer"[MeSH Terms])'
        """
        query_parts = []

        # 1. 使用新的智能查询扩展器（替代原有的_build_target_query）
        try:
            expanded_query = expand_search_query(
                target_name,
                include_full_name=True,
                include_gene_name=True,
                include_aliases=True
            )

            # 添加临床试验过滤器
            target_query = add_clinical_filter(expanded_query)
            query_parts.append(target_query)

            logger.info(f"Expanded query for {target_name}: {target_query[:200]}...")

        except Exception as e:
            # 如果扩展失败，降级到简单的查询
            logger.warning(f"Query expansion failed for {target_name}, using fallback: {e}")
            target_query = self._build_target_query(target_name, use_synonyms)
            query_parts.append(target_query)

        # 2. 关键词搜索
        if keywords:
            keyword_query = " OR ".join([f'"{kw}"[Ti/Ab]' for kw in keywords])
            query_parts.append(f"({keyword_query})")

        # 3. 疾病 MeSH 术语
        if diseases:
            mesh_terms = []
            for disease in diseases:
                if disease in DISEASE_MESH_TERMS:
                    mesh_terms.extend(DISEASE_MESH_TERMS[disease])
                else:
                    mesh_terms.append(disease)

            mesh_query = " OR ".join([f'"{term}"[MeSH Terms]' for term in mesh_terms])
            query_parts.append(f"({mesh_query})")

        return " AND ".join(query_parts)

    def _build_target_query(self, target_name: str, use_synonyms: bool) -> str:
        """
        构建靶点查询（包含同义词）

        Args:
            target_name: 靶点名称
            use_synonyms: 是否使用同义词

        Returns:
            靶点查询字符串
        """
        # 靶点名称（标题/摘要搜索）
        terms = [f'"{target_name}"[Ti/Ab]']

        # 添加同义词
        if use_synonyms and target_name in MESH_SYNONYMS:
            for synonym in MESH_SYNONYMS[target_name]:
                terms.append(f'"{synonym}"[Ti/Ab]')

        return "(" + " OR ".join(terms) + ")"

    def _calculate_date_range(self, days: int) -> Optional[Tuple[str, str]]:
        """
        计算日期范围

        Args:
            days: 向前推算的天数

        Returns:
            (start_date, end_date) 格式为 "YYYY/MM/DD"
        """
        if days <= 0:
            return None

        end = date.today()
        start = end - timedelta(days=days)

        return (
            start.strftime("%Y/%m/%d"),
            end.strftime("%Y/%m/%d"),
        )

    def rank_publications(
        self,
        publications: List[Dict[str, Any]],
        target_name: str,
        keywords: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        文献排序算法（集成多维度评分系统）

        得分规则（新的评分算法）：
        1. 时效性得分（40%权重）：0-100分
        2. 临床数据得分（25%权重）：0-100分（ORR/PFS/OS等）
        3. 来源质量得分（15%权重）：0-40分（ASCO/NEJM等）
        4. 阶段得分（10%权重）：0-40分（Phase III/NDA等）
        5. 监管认定得分（10%权重）：0-30分（Breakthrough Therapy等）

        Args:
            publications: 文献列表
            target_name: 靶点名称（用于计算匹配度，已废弃）
            keywords: 关键词列表（已废弃）

        Returns:
            排序后的文献列表（添加 score 和 score_breakdown 字段）
        """
        scored_publications = []

        for pub in publications:
            try:
                # 使用新的多维度评分算法
                score_result = calculate_publication_score(
                    title=pub.get('title', ''),
                    pub_date=pub.get('publication_date') or pub.get('pub_date'),
                    abstract=pub.get('abstract', ''),
                    journal=pub.get('journal', ''),
                    source_type=pub.get('source', ''),
                    publication_type=pub.get('publication_type', '')
                )

                # 构建增强的文献信息
                pub_with_score = {
                    **pub,
                    # 总分
                    "score": score_result.total_score,
                    "relevance_score": score_result.total_score,
                    # 详细得分（展开到顶层）
                    "recency_score": score_result.recency_score,
                    "clinical_score": score_result.clinical_score,
                    "phase_score": score_result.phase_score,
                    "regulatory_score": score_result.regulatory_score,
                    "source_score": score_result.source_score,
                    "penalty_score": score_result.penalty_score,
                    # 向后兼容字段（已废弃，但保留以兼容旧代码）
                    "keyword_match_score": 0.0,  # 新算法不再单独计算
                    # 得分明细（字典形式）
                    "score_breakdown": score_result.to_dict(),
                }

                scored_publications.append(pub_with_score)

                # 记录高分文献
                if score_result.total_score >= 70:
                    logger.info(
                        f"High score publication: {pub.get('title', '')[:60]}... "
                        f"(score: {score_result.total_score})"
                    )

            except Exception as e:
                # 如果评分失败，记录警告并使用默认得分
                logger.warning(f"Failed to score publication {pub.get('pmid', 'unknown')}: {e}")
                pub_with_score = {
                    **pub,
                    # 总分
                    "score": 0.0,
                    "relevance_score": 0.0,
                    # 详细得分（默认值）
                    "recency_score": 0.0,
                    "clinical_score": 0.0,
                    "phase_score": 0.0,
                    "regulatory_score": 0.0,
                    "source_score": 0.0,
                    "penalty_score": 0.0,
                    # 向后兼容字段
                    "keyword_match_score": 0.0,
                    # 得分明细（空）
                    "score_breakdown": {},
                }
                scored_publications.append(pub_with_score)

        # 按综合得分降序排序
        scored_publications.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"Ranked {len(scored_publications)} publications")

        return scored_publications

    def _calculate_recency_score(self, pub: Dict[str, Any]) -> int:
        """
        计算时效性得分（0-100）

        得分规则：
        - 0-30天：100分
        - 31-90天：80分
        - 91-365天：60分
        - 366-730天：40分
        - 超过730天：20分
        """
        pub_date_str = pub.get("pub_date")
        if not pub_date_str:
            return 20

        try:
            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
        except ValueError:
            return 20

        days = (date.today() - pub_date).days

        if days <= 30:
            return 100
        elif days <= 90:
            return 80
        elif days <= 365:
            return 60
        elif days <= 730:
            return 40
        else:
            return 20

    def _calculate_clinical_score(self, pub: Dict[str, Any]) -> int:
        """
        计算临床数据得分（0-50）

        得分规则：
        - 每个临床指标（ORR/PFS/OS/DCR）：+10分
        - 有样本量（n=）：+5分
        - 文献类型为 Clinical Trial：+10分
        """
        score = 0

        clinical_tags = pub.get("clinical_data_tags", [])
        score += min(len(clinical_tags) * 10, 40)  # 最多 40 分

        # Clinical Trial 额外加分
        if pub.get("publication_type") == "Clinical Trial":
            score += 10

        return min(score, 50)

    def _calculate_source_score(self, pub: Dict[str, Any]) -> int:
        """
        计算来源期刊得分（0-30）

        得分规则：
        - ASCO/AACR/ESMO：30分
        - NEJM/LANCET/JAMA/NATURE/SCIENCE：25分
        - JCO：20分
        - 其他期刊：10分
        """
        source_type = pub.get("source_type")

        if source_type in ["ASCO", "AACR", "ESMO"]:
            return 30
        elif source_type in ["NEJM", "LANCET", "JAMA", "NATURE", "SCIENCE"]:
            return 25
        elif source_type == "JCO":
            return 20
        elif pub.get("journal"):
            return 10
        else:
            return 0

    def _calculate_keyword_match_score(
        self,
        pub: Dict[str, Any],
        target_name: str,
        keywords: List[str],
    ) -> float:
        """
        计算关键词匹配得分（0-100）

        得分规则：
        - 标题包含靶点：+50分
        - 摘要包含靶点：+20分
        - 标题/摘要包含关键词：每个 +5分
        """
        score = 0.0

        title = (pub.get("title") or "").lower()
        abstract = (pub.get("abstract") or "").lower()

        # 靶点匹配
        if target_name.lower() in title:
            score += 50
        if target_name.lower() in abstract:
            score += 20

        # 关键词匹配
        all_keywords = [target_name] + keywords
        for kw in all_keywords:
            if kw.lower() in title:
                score += 5
            if kw.lower() in abstract:
                score += 2

        return min(score, 100.0)

    async def link_target_publication(
        self,
        target_id: int,
        pmid: str,
        relation_type: str = "mentions",
        evidence_snippet: Optional[str] = None,
    ) -> None:
        """
        关联 Target 和 Publication

        注意：此功能需要数据库连接支持，当前版本仅记录日志
        完整实现需要在数据库 Schema 创建后进行

        Args:
            target_id: 靶点 ID
            pmid: PubMed ID
            relation_type: 关系类型（mentions/targets/inhibits）
            evidence_snippet: 证据片段
        """
        # TODO: 数据库关联功能需要在数据库就绪后启用
        logger.info(
            f"Link Target-Publication (pending database)",
            extra={
                "target_id": target_id,
                "pmid": pmid,
                "relation_type": relation_type,
            }
        )

    async def close(self) -> None:
        """关闭服务"""
        await self.client.close()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


__all__ = [
    "PubmedService",
    "QueryConfig",
    "PublicationScore",
]
