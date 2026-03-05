"""
=====================================================
PubMed API 路由
=====================================================

提供 PubMed 相关的 RESTful API 接口：
- POST /api/pubmed/search: 搜索文献
- GET /api/pubmed/publication/{pmid}: 获取文献详情
- POST /api/pubmed/target/{target_id}/link: 关联文献到靶点

使用示例（FastAPI 自动文档）：
访问 http://localhost:8000/docs 查看完整 API 文档
=====================================================
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services.pubmed_service import PubmedService, QueryConfig
from core.logger import get_logger

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/api/pubmed", tags=["PubMed"])


# =====================================================
# 请求/响应模型
# =====================================================


class SearchRequest(BaseModel):
    """文献搜索请求"""
    target_name: str = Field(..., description="靶点名称，如 EGFR")
    keywords: Optional[List[str]] = Field(None, description="额外关键词")
    diseases: Optional[List[str]] = Field(None, description="疾病类型")
    max_results: int = Field(50, ge=1, le=500, description="最大结果数")
    date_range_days: int = Field(365, ge=0, description="日期范围（天）")
    include_clinical_trials: bool = Field(True, description="是否包含临床试验")
    include_reviews: bool = Field(False, description="是否包含综述")
    min_relevance_score: float = Field(0.0, ge=0.0, le=100.0, description="最小相关性得分")


class PublicationResponse(BaseModel):
    """文献响应"""
    pmid: str
    title: str
    abstract: Optional[str]
    journal: Optional[str]
    pub_date: Optional[str]
    mesh_terms: List[str]
    publication_type: Optional[str]
    source_type: Optional[str]
    clinical_data_tags: List[dict]

    # 得分信息
    relevance_score: float
    recency_score: int
    clinical_score: int
    source_score: int
    keyword_match_score: float


class SearchResponse(BaseModel):
    """搜索响应"""
    total: int
    publications: List[PublicationResponse]


class LinkRequest(BaseModel):
    """关联请求"""
    pmid: str = Field(..., description="PubMed ID")
    relation_type: str = Field("mentions", description="关系类型")
    evidence_snippet: Optional[str] = Field(None, description="证据片段")


# =====================================================
# 依赖项
# =====================================================


async def get_pubmed_service():
    """
    获取 PubmedService 实例（依赖注入）

    Yields:
        PubmedService 实例
    """
    # 尝试从容器获取缓存服务
    cache_service = None
    try:
        from core.container import get_container
        container = get_container()
        if container.has("cache"):
            cache_service = container.get("cache")
    except Exception:
        pass

    service = PubmedService(cache_service=cache_service)
    try:
        yield service
    finally:
        await service.close()


# =====================================================
# API 路由
# =====================================================


@router.post("/search", response_model=SearchResponse)
async def search_publications(
    request: SearchRequest,
    service: PubmedService = Depends(get_pubmed_service),
):
    """
    搜索 PubMed 文献（智能查询）

    功能：
    - 根据靶点名称智能搜索文献
    - 支持关键词扩展和 MeSH 同义词
    - 自动按相关性排序

    示例：
    ```json
    {
      "target_name": "EGFR",
      "keywords": ["inhibitor", "TKI"],
      "diseases": ["lung cancer"],
      "max_results": 50
    }
    ```
    """
    try:
        # 构建查询配置
        config = QueryConfig(
            max_results=request.max_results,
            date_range_days=request.date_range_days,
            include_clinical_trials=request.include_clinical_trials,
            include_reviews=request.include_reviews,
            min_relevance_score=request.min_relevance_score,
        )

        # 执行搜索
        publications = await service.search_by_target(
            target_name=request.target_name,
            config=config,
            custom_keywords=request.keywords,
            diseases=request.diseases,
        )

        logger.info(
            f"Search completed",
            extra={
                "target_name": request.target_name,
                "results_count": len(publications),
            }
        )

        return SearchResponse(
            total=len(publications),
            publications=publications,
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/publication/{pmid}", response_model=PublicationResponse)
async def get_publication(
    pmid: str,
    service: PubmedService = Depends(get_pubmed_service),
):
    """
    获取单个文献详情

    Args:
        pmid: PubMed ID

    Returns:
        文献详细信息
    """
    try:
        # 获取文献详情
        publications = await service.client.fetch_details([pmid])

        if not publications:
            raise HTTPException(status_code=404, detail=f"Publication {pmid} not found")

        pub = publications[0]

        # 计算得分
        ranked = service.rank_publications([pub], target_name="")

        return PublicationResponse(**ranked[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get publication failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/target/{target_id}/link")
async def link_target_publication(
    target_id: int,
    request: LinkRequest,
    service: PubmedService = Depends(get_pubmed_service),
):
    """
    关联文献到靶点

    功能：
    - 创建 Target-Publication 关联
    - 保存关系类型和证据片段

    Args:
        target_id: 靶点 ID
        request: 关联请求

    Returns:
        操作结果
    """
    try:
        await service.link_target_publication(
            target_id=target_id,
            pmid=request.pmid,
            relation_type=request.relation_type,
            evidence_snippet=request.evidence_snippet,
        )

        return {
            "success": True,
            "message": f"Linked PMID {request.pmid} to target {target_id}",
            "target_id": target_id,
            "pmid": request.pmid,
        }

    except Exception as e:
        logger.error(f"Link failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    健康检查

    Returns:
        服务状态
    """
    return {
        "status": "healthy",
        "service": "PubMed API",
    }


# =====================================================
# 导出
# =====================================================

__all__ = ["router"]
