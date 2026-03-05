"""
=====================================================
统一搜索服务（Unified Search Service）
=====================================================

提供跨实体的统一搜索功能：
- 同时搜索管线（Pipeline）、文献（Publication）、靶点（Target）
- 智能查询扩展（同义词、全名）
- 相关性评分排序
- 多维度筛选（公司、阶段、MoA类型等）
- 支持通过靶点关联查询管线

使用示例：
    from services.unified_search_service import UnifiedSearchService

    service = UnifiedSearchService()

    # 统一搜索
    results = service.search(
        query="EGFR",
        entity_type="all",
        filters={"company": "恒瑞医药", "phase": "Phase 3"},
        limit=20
    )

    print(results)
    # {
    #     "query": "EGFR",
    #     "total_count": 150,
    #     "results": {
    #         "pipelines": {"count": 50, "items": [...]},
    #         "publications": {"count": 80, "items": [...]},
    #         "targets": {"count": 20, "items": [...]}
    #     },
    #     "facets": {...}
    # }
=====================================================
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from utils.database import SessionLocal
from models.pipeline import Pipeline
from models.publication import Publication
from models.target import Target
from models.relationships import TargetPipeline
from utils.target_gene_mapping import expand_search_query
from core.logger import get_logger

logger = get_logger(__name__)


class UnifiedSearchService:
    """统一搜索服务"""

    def __init__(self, cache_service=None):
        """
        初始化搜索服务

        Args:
            cache_service: 可选的缓存服务实例
        """
        self.cache_service = cache_service

    def search(
        self,
        query: str,
        entity_type: str = "all",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        统一搜索入口

        Args:
            query: 搜索关键词
            entity_type: 实体类型 (all/pipeline/publication/target)
            filters: 筛选条件
                - company: 公司名称
                - phase: 阶段
                - moa_type: MoA类型
                - date_from/date_to: 日期范围（仅文献）
            limit: 结果数量限制

        Returns:
            聚合搜索结果
        """
        # 查询扩展（同义词、全名）
        queries = self._expand_query(query)

        results = {}
        total_count = 0

        # 搜索管线
        if entity_type in ["all", "pipeline"]:
            pipeline_results = self.search_pipelines(queries, filters, limit)
            results["pipelines"] = pipeline_results
            total_count += pipeline_results["count"]

        # 搜索文献
        if entity_type in ["all", "publication"]:
            publication_results = self.search_publications(queries, filters, limit)
            results["publications"] = publication_results
            total_count += publication_results["count"]

        # 搜索靶点
        if entity_type in ["all", "target"]:
            target_results = self.search_targets(queries, limit)
            results["targets"] = target_results
            total_count += target_results["count"]

        return {
            "query": query,
            "total_count": total_count,
            "results": results,
            "facets": {}  # TODO: 实现聚合统计
        }

    def search_pipelines(
        self,
        queries: List[str],
        filters: Optional[Dict[str, Any]],
        limit: int
    ) -> Dict[str, Any]:
        """
        搜索管线（支持通过靶点关联查询）

        Args:
            queries: 查询词列表
            filters: 筛选条件
            limit: 结果数量限制

        Returns:
            管线搜索结果
        """
        db = SessionLocal()
        try:
            # 步骤1: 通过靶点查找相关管线ID（如果有靶点关联）
            target_pipeline_ids = set()
            try:
                for q in queries:
                    # 查找匹配的靶点
                    matching_targets = db.query(Target).filter(
                        Target.standard_name.ilike(f"%{q}%")
                    ).all()

                    logger.info(f"查询词 '{q}' 找到 {len(matching_targets)} 个靶点")

                    # 获取这些靶点关联的管线ID
                    if matching_targets:
                        target_ids = [t.target_id for t in matching_targets]
                        links = db.query(TargetPipeline).filter(
                            TargetPipeline.target_id.in_(target_ids)
                        ).all()
                        for link in links:
                            target_pipeline_ids.add(str(link.pipeline_id))

                logger.info(f"通过靶点关联找到 {len(target_pipeline_ids)} 个管线ID: {list(target_pipeline_ids)}")
            except Exception as e:
                logger.warning(f"通过靶点查询管线失败: {e}")

            # 步骤2: 构建主查询
            query_obj = db.query(Pipeline)

            # 构建关键词匹配条件
            conditions = []
            for q in queries:
                conditions.append(Pipeline.drug_code.ilike(f"%{q}%"))
                conditions.append(Pipeline.indication.ilike(f"%{q}%"))

            # 添加通过靶点关联的管线ID条件
            if target_pipeline_ids:
                conditions.append(Pipeline.pipeline_id.in_(list(target_pipeline_ids)))
                logger.info(f"添加靶点关联条件: {len(target_pipeline_ids)} 个管线ID")

            if conditions:
                query_obj = query_obj.filter(or_(*conditions))
                logger.info(f"应用 {len(conditions)} 个查询条件")

            # 应用筛选
            if filters:
                if "company" in filters:
                    query_obj = query_obj.filter(
                        Pipeline.company_name == filters["company"]
                    )

                if "phase" in filters:
                    query_obj = query_obj.filter(
                        Pipeline.phase == filters["phase"]
                    )

                if "moa_type" in filters:
                    query_obj = query_obj.filter(
                        Pipeline.modality == filters["moa_type"]
                    )

            # 执行查询（取更多记录以确保包含通过靶点关联的管线）
            pipelines = query_obj.limit(limit * 10).all()  # 取更多，排序后再限制

            logger.info(f"查询返回 {len(pipelines)} 条管线记录")

            # 计算相关性得分
            results = []
            for p in pipelines:
                score = self._calculate_pipeline_relevance(p, queries)
                results.append({
                    "id": str(p.pipeline_id),
                    "drug_code": p.drug_code,
                    "company_name": p.company_name,
                    "indication": p.indication,
                    "phase": p.phase,
                    "phase_raw": p.phase_raw,
                    "modality": p.modality,
                    "source_url": p.source_url,
                    "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
                    "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
                    "relevance_score": score
                })

            # 按相关性排序
            results.sort(key=lambda x: x["relevance_score"], reverse=True)

            # 限制返回数量
            results = results[:limit]

            return {
                "count": len(results),
                "items": results
            }
        finally:
            db.close()

    def search_publications(
        self,
        queries: List[str],
        filters: Optional[Dict[str, Any]],
        limit: int
    ) -> Dict[str, Any]:
        """
        搜索文献

        Args:
            queries: 查询词列表
            filters: 筛选条件
            limit: 结果数量限制

        Returns:
            文献搜索结果
        """
        db = SessionLocal()
        try:
            query_obj = db.query(Publication)

            # 构建关键词匹配条件
            conditions = []
            for q in queries:
                conditions.append(Publication.title.contains(q))
                conditions.append(Publication.abstract.contains(q))

            if conditions:
                query_obj = query_obj.filter(or_(*conditions))

            # 应用筛选
            if filters:
                if "journal" in filters:
                    query_obj = query_obj.filter(
                        Publication.journal == filters["journal"]
                    )

                if "publication_type" in filters:
                    query_obj = query_obj.filter(
                        Publication.publication_type == filters["publication_type"]
                    )

                if "date_from" in filters:
                    query_obj = query_obj.filter(
                        Publication.publication_date >= filters["date_from"]
                    )

                if "date_to" in filters:
                    query_obj = query_obj.filter(
                        Publication.publication_date <= filters["date_to"]
                    )

            # 执行查询
            publications = query_obj.limit(limit * 2).all()

            # 计算相关性得分
            results = []
            for p in publications:
                score = self._calculate_publication_relevance(p, queries)
                results.append({
                    "id": p.id,
                    "title": p.title,
                    "abstract": p.abstract,
                    "authors": p.authors,
                    "journal": p.journal,
                    "publication_date": p.publication_date.isoformat() if p.publication_date else None,
                    "publication_type": p.publication_type,
                    "doi": p.doi,
                    "pmid": p.pmid,
                    "relevance_score": score
                })

            # 按相关性排序
            results.sort(key=lambda x: x["relevance_score"], reverse=True)

            # 限制返回数量
            results = results[:limit]

            return {
                "count": len(results),
                "items": results
            }
        finally:
            db.close()

    def search_targets(
        self,
        queries: List[str],
        limit: int
    ) -> Dict[str, Any]:
        """
        搜索靶点

        Args:
            queries: 查询词列表
            limit: 结果数量限制

        Returns:
            靶点搜索结果
        """
        db = SessionLocal()
        try:
            query_obj = db.query(Target)

            # 构建关键词匹配条件
            conditions = []
            for q in queries:
                conditions.append(Target.standard_name.ilike(f"%{q}%"))

            if conditions:
                query_obj = query_obj.filter(or_(*conditions))

            # 执行查询
            targets = query_obj.limit(limit * 2).all()

            # 计算相关性得分
            results = []
            for t in targets:
                score = self._calculate_target_relevance(t, queries)
                results.append({
                    "id": str(t.target_id),
                    "standard_name": t.standard_name,
                    "full_name": t.standard_name,  # 使用 standard_name 作为 full_name
                    "gene_name": t.gene_id if t.gene_id else "",
                    "category": t.category if t.category else "",
                    "aliases": t.aliases if t.aliases else [],
                    "relevance_score": score
                })

            # 按相关性排序
            results.sort(key=lambda x: x["relevance_score"], reverse=True)

            # 限制返回数量
            results = results[:limit]

            return {
                "count": len(results),
                "items": results
            }
        finally:
            db.close()

    def _expand_query(self, query: str) -> List[str]:
        """
        查询扩展（同义词、全名）

        Args:
            query: 原始查询词

        Returns:
            扩展后的查询词列表
        """
        queries = [query]

        try:
            # 使用靶点-基因映射扩展查询
            expanded = expand_search_query(query)
            if expanded:
                queries.extend(expanded)
        except Exception as e:
            logger.debug(f"Query expansion failed for '{query}': {e}")

        return list(set(queries))  # 去重

    def _calculate_pipeline_relevance(
        self,
        pipeline: Pipeline,
        queries: List[str]
    ) -> float:
        """
        计算管线相关性得分

        Args:
            pipeline: 管线对象
            queries: 查询词列表

        Returns:
            相关性得分
        """
        score = 0.0

        for q in queries:
            q_lower = q.lower()

            # 药物代码匹配（权重最高）
            if pipeline.drug_code and q_lower in pipeline.drug_code.lower():
                score += 5.0

            # 适应症匹配
            if pipeline.indication and q_lower in pipeline.indication.lower():
                score += 3.0

            # 公司名称匹配
            if pipeline.company_name and q_lower in pipeline.company_name.lower():
                score += 2.0

            # MoA 匹配
            if pipeline.modality and q_lower in pipeline.modality.lower():
                score += 1.0

        return score

    def _calculate_publication_relevance(
        self,
        publication: Publication,
        queries: List[str]
    ) -> float:
        """
        计算文献相关性得分

        Args:
            publication: 文献对象
            queries: 查询词列表

        Returns:
            相关性得分
        """
        score = 0.0

        for q in queries:
            q_lower = q.lower()

            # 标题匹配（权重最高）
            if publication.title and q_lower in publication.title.lower():
                score += 5.0

            # 摘要匹配
            if publication.abstract and q_lower in publication.abstract.lower():
                score += 2.0

            # 作者匹配
            if publication.authors and q_lower in publication.authors.lower():
                score += 1.0

        return score

    def _calculate_target_relevance(
        self,
        target: Target,
        queries: List[str]
    ) -> float:
        """
        计算靶点相关性得分

        Args:
            target: 靶点对象
            queries: 查询词列表

        Returns:
            相关性得分
        """
        score = 0.0

        for q in queries:
            q_lower = q.lower()

            # 标准名称完全匹配（权重最高）
            if target.standard_name and q_lower == target.standard_name.lower():
                score += 5.0

            # 别名匹配
            if target.aliases:
                for alias in target.aliases:
                    if q_lower == alias.lower():
                        score += 3.0
                        break

            # 标准名称包含查询词
            if target.standard_name and q_lower in target.standard_name.lower():
                score += 2.0

        return score
