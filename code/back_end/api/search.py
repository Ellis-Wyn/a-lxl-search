"""
=====================================================
统一搜索 API 路由（Unified Search API）
=====================================================

提供跨实体的统一搜索功能：
- GET /api/search/unified: 统一搜索（管线+文献+靶点+CDE事件）
- GET /api/search/suggestions: 搜索建议/自动补全
- GET /api/search/facets: 获取筛选facet统计

使用示例：
    # 统一搜索
    curl "http://localhost:8000/api/search/unified?q=EGFR&type=all&limit=20"

    # 只搜索管线
    curl "http://localhost:8000/api/search/unified?q=EGFR&type=pipeline&company=恒瑞医药"

    # 只搜索CDE事件
    curl "http://localhost:8000/api/search/unified?q=EGFR&type=cde_event&event_type=IND"

    # 搜索建议
    curl "http://localhost:8000/api/search/suggestions?q=EGR"
=====================================================
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services.unified_search_service import UnifiedSearchService
from core.logger import get_logger
from core.container import get_container

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/api/search", tags=["Search"])


# =====================================================
# 请求/响应模型
# =====================================================


class UnifiedSearchRequest(BaseModel):
    """统一搜索请求"""
    query: str = Field(..., description="搜索关键词")
    entity_type: str = Field("all", description="实体类型: all/pipeline/publication/target/cde_event")
    filters: Optional[Dict[str, Any]] = Field(None, description="筛选条件")
    limit: int = Field(20, ge=1, le=100, description="结果数量限制")


class FacetItem(BaseModel):
    """Facet项"""
    name: str
    count: int


class FacetsResponse(BaseModel):
    """Facet统计响应"""
    companies: Dict[str, int]
    phases: Dict[str, int]
    moa_types: Dict[str, int]


class SearchSuggestion(BaseModel):
    """搜索建议"""
    text: str
    type: str  # "pipeline" / "target" / "publication" / "cde_event"
    score: float


# =====================================================
# API 路由
# =====================================================


@router.get("/unified")
async def unified_search(
    q: str = Query(..., description="搜索关键词（必需）", min_length=1),
    type: str = Query("all", description="实体类型: all/pipeline/publication/target/cde_event"),
    company: Optional[str] = Query(None, description="公司名称筛选（仅管线）"),
    phase: Optional[str] = Query(None, description="阶段筛选（仅管线）"),
    moa_type: Optional[str] = Query(None, description="MoA类型筛选（仅管线）"),
    journal: Optional[str] = Query(None, description="期刊筛选（仅文献）"),
    date_from: Optional[str] = Query(None, description="起始日期（仅文献/CDE）YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期（仅文献/CDE）YYYY-MM-DD"),
    event_type: Optional[str] = Query(None, description="CDE事件类型筛选（仅CDE事件）IND/CTA/NDA/BLA"),
    applicant: Optional[str] = Query(None, description="CDE申请人筛选（仅CDE事件）"),
    limit: int = Query(20, ge=1, le=100, description="每类结果数量限制"),
):
    """
    统一搜索API（同时搜索管线、文献、靶点、CDE事件）

    功能：
    - 一次调用搜索所有实体类型
    - 智能查询扩展（同义词、全名）
    - 相关性评分排序
    - 多维度筛选
    - 数据可追溯性（返回原始URL）

    参数：
    - q: 搜索关键词（必需）
    - type: 实体类型
      - all: 搜索所有（默认）
      - pipeline: 只搜索管线
      - publication: 只搜索文献
      - target: 只搜索靶点
      - cde_event: 只搜索CDE事件
    - company: 公司名称筛选（仅管线）
    - phase: 阶段筛选（仅管线）
    - moa_type: MoA类型筛选（仅管线）
    - journal: 期刊筛选（仅文献）
    - date_from/date_to: 日期范围（仅文献/CDE）
    - event_type: CDE事件类型（仅CDE事件）IND/CTA/NDA/BLA
    - applicant: CDE申请人（仅CDE事件）
    - limit: 每类结果数量限制

    返回：
    ```json
    {
      "query": "EGFR",
      "total_count": 170,
      "results": {
        "pipelines": {"count": 50, "items": [...]},
        "publications": {"count": 80, "items": [...]},
        "targets": {"count": 20, "items": [...]},
        "cde_events": {"count": 20, "items": [...]}
      },
      "facets": {
        "companies": {"恒瑞医药": 30, "百济神州": 20},
        "phases": {"Phase 3": 25, "Phase 2": 15},
        "moa_types": {"Small Molecule": 35, "ADC": 10}
      }
    }
    ```

    示例：
    ```bash
    # 搜索EGFR相关所有内容
    curl "http://localhost:8000/api/search/unified?q=EGFR&type=all&limit=10"

    # 只搜索恒瑞医药的管线
    curl "http://localhost:8000/api/search/unified?q=EGFR&type=pipeline&company=恒瑞医药"

    # 搜索CDE的IND事件
    curl "http://localhost:8000/api/search/unified?q=EGFR&type=cde_event&event_type=IND"

    # 搜索Phase 3的管线
    curl "http://localhost:8000/api/search/unified?q=EGFR&type=pipeline&phase=Phase 3"
    ```
    """
    try:
        # 参数验证
        valid_types = ["all", "pipeline", "publication", "target", "cde_event"]
        if type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entity_type '{type}'. Must be one of: {valid_types}"
            )

        # 构建筛选条件
        filters = {}

        # 管线筛选
        if company:
            filters["company"] = company
        if phase:
            filters["phase"] = phase
        if moa_type:
            filters["moa_type"] = moa_type

        # 文献筛选
        if journal:
            filters["journal"] = journal
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to

        # CDE事件筛选
        if event_type:
            filters["event_type"] = event_type
        if applicant:
            filters["applicant"] = applicant

        # 执行搜索
        # 尝试从容器获取缓存服务
        cache_service = None
        try:
            container = get_container()
            if container.has("cache"):
                cache_service = container.get("cache")
        except Exception:
            pass

        service = UnifiedSearchService(cache_service=cache_service)
        results = service.search(
            query=q,
            entity_type=type,
            filters=filters if filters else None,
            limit=limit
        )

        logger.info(
            f"Unified search completed",
            extra={
                "query": q,
                "entity_type": type,
                "total_count": results["total_count"],
                "filters": filters
            }
        )

        return results

    except Exception as e:
        logger.error(f"Unified search failed: {e}", extra={"query": q, "type": type})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions", response_model=List[SearchSuggestion])
async def search_suggestions(
    q: str = Query(..., description="搜索关键词（必需）", min_length=1),
    limit: int = Query(10, ge=1, le=50, description="建议数量限制"),
):
    """
    搜索建议/自动补全

    功能：
    - 根据输入提供搜索建议
    - 返回匹配的管线、靶点、文献、CDE事件
    - 按相关性排序

    参数：
    - q: 搜索关键词（必需）
    - limit: 建议数量限制

    返回：
    ```json
    [
      {"text": "EGFR", "type": "target", "score": 1.0},
      {"text": "EGFR抑制剂", "type": "pipeline", "score": 0.9},
      {"text": "EGFR突变", "type": "publication", "score": 0.85},
      {"text": "EGFR抑制剂 - IND受理", "type": "cde_event", "score": 0.8}
    ]
    ```

    示例：
    ```bash
    curl "http://localhost:8000/api/search/suggestions?q=EGR&limit=10"
    ```
    """
    try:
        service = UnifiedSearchService()

        # 搜索管线（取前几个）
        pipelines = service.search_pipelines([q], None, limit)
        suggestions = []

        for p in pipelines["items"]:
            suggestions.append(SearchSuggestion(
                text=f"{p['drug_code']} - {p.get('indication', '')}",
                type="pipeline",
                score=p["relevance_score"]
            ))

        # 搜索靶点（取前几个）
        targets = service.search_targets([q], None, limit)

        for t in targets["items"]:
            suggestions.append(SearchSuggestion(
                text=f"{t['standard_name']} ({t.get('full_name', '')})",
                type="target",
                score=t["relevance_score"]
            ))

        # 搜索文献（取前几个）
        publications = service.search_publications([q], None, limit)

        for pub in publications["items"]:
            suggestions.append(SearchSuggestion(
                text=pub['title'][:80],  # 限制标题长度
                type="publication",
                score=pub["relevance_score"]
            ))

        # 搜索CDE事件（取前几个）
        cde_events = service.search_cde_events([q], None, limit)

        for event in cde_events["items"]:
            suggestions.append(SearchSuggestion(
                text=f"{event['drug_name']} - {event['event_type']}",
                type="cde_event",
                score=event["relevance_score"]
            ))

        # 按相关性排序并限制数量
        suggestions.sort(key=lambda x: x.score, reverse=True)
        suggestions = suggestions[:limit]

        logger.info(f"Search suggestions generated: {len(suggestions)} items")

        return suggestions

    except Exception as e:
        logger.error(f"Search suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facets", response_model=FacetsResponse)
async def get_search_facets(
    q: str = Query(..., description="搜索关键词（必需）", min_length=1),
):
    """
    获取筛选facet统计

    功能：
    - 返回当前搜索结果的各种筛选选项统计
    - 用于前端展示筛选器（如：公司A有30条，公司B有20条）

    参数：
    - q: 搜索关键词（必需）

    返回：
    ```json
    {
      "companies": {"恒瑞医药": 30, "百济神州": 20},
      "phases": {"Phase 3": 25, "Phase 2": 15, "Phase 1": 10},
      "moa_types": {"Small Molecule": 35, "ADC": 10, "CAR-T": 5}
    }
    ```

    示例：
    ```bash
    curl "http://localhost:8000/api/search/facets?q=EGFR"
    ```
    """
    try:
        service = UnifiedSearchService()

        # 执行搜索以获取facets
        results = service.search(
            query=q,
            entity_type="all",
            filters=None,
            limit=100  # 取足够多的结果来统计facet
        )

        facets = results.get("facets", {})

        logger.info(f"Search facets retrieved: {facets}")

        return FacetsResponse(
            companies=facets.get("companies", {}),
            phases=facets.get("phases", {}),
            moa_types=facets.get("moa_types", {})
        )

    except Exception as e:
        logger.error(f"Get search facets failed: {e}")
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
        "service": "Unified Search API",
    }


# =====================================================
# 导出
# =====================================================

__all__ = ["router"]
