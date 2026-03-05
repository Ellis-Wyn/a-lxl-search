"""
=====================================================
Publications API 路由
=====================================================

提供文献（Publication）相关的 RESTful API 接口：
- GET /api/v1/publications: 获取文献列表（支持搜索、分页、日期过滤）
- GET /api/v1/publications/{pmid}: 获取文献详情
- POST /api/v1/publications/link: 关联文献到靶点

使用示例（FastAPI 自动文档）：
访问 http://localhost:8000/docs 查看完整 API 文档
=====================================================
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from utils.database import get_db
from utils.serializers import (
    PublicationListItemSerializer,
    PublicationDetailSerializer,
    PublicationStatsSerializer,
)
from utils.validators import TargetPublicationLinkRequest, PublicationCreateRequest
from models.publication import Publication
from models.target import Target
from services.database_service import DatabaseService
from core.logger import get_logger

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/api/v1/publications", tags=["Publications"])


class LinkResponse(BaseModel):
    """关联响应"""
    success: bool
    message: str
    target_id: Optional[str] = None
    pmid: Optional[str] = None


# =====================================================
# API 接口
# =====================================================


@router.get("")
async def list_publications(
    keyword: Optional[str] = Query(None, description="搜索关键词（标题/摘要）"),
    journal: Optional[str] = Query(None, description="期刊过滤"),
    publication_type: Optional[str] = Query(None, description="文献类型（如：Clinical Trial）"),
    date_from: Optional[str] = Query(None, description="起始日期（YYYY-MM-DD）"),
    date_to: Optional[str] = Query(None, description="结束日期（YYYY-MM-DD）"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量（分页）"),
    db: Session = Depends(get_db)
):
    """
    获取文献列表

    支持功能：
    - 搜索：按标题/摘要关键词
    - 过滤：按期刊、类型、日期范围
    - 分页：支持 limit + offset
    """
    try:
        logger.info(f"Fetching publications with filters: keyword={keyword}, journal={journal}, limit={limit}")

        # 构建查询
        query = db.query(Publication)

        # 关键词搜索（标题和摘要）
        if keyword:
            query = query.filter(
                Publication.title.ilike(f"%{keyword}%")
            )

        # 期刊过滤
        if journal:
            query = query.filter(Publication.journal.ilike(f"%{journal}%"))

        # 文献类型过滤
        if publication_type:
            query = query.filter(Publication.publication_type.ilike(f"%{publication_type}%"))

        # 日期范围过滤
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Publication.pub_date >= date_from_obj)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid date_from format: {date_from}")

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(Publication.pub_date <= date_to_obj)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid date_to format: {date_to}")

        # 排序：按发布日期降序
        query = query.order_by(Publication.pub_date.desc())

        # 分页
        query = query.offset(offset).limit(limit)

        publications = query.all()

        logger.info(f"Found {len(publications)} publications")

        # 使用序列化器转换
        return [PublicationListItemSerializer.model_validate(p) for p in publications]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching publications: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("")
async def create_publication(
    request: PublicationCreateRequest,
    db: Session = Depends(get_db)
):
    """
    创建文献

    使用 Pydantic 验证数据：
    - pmid: PubMed ID（必填，必须是数字，最多10位）
    - title: 标题（必填）
    - abstract: 摘要
    - pub_date: 发布日期
    - journal: 期刊名称
    - publication_type: 文献类型
    - authors: 作者列表（自动去重）
    - mesh_terms: MeSH 主题词
    - clinical_data_tags: 临床数据标签

    返回：
    - 创建的文献详情
    """
    try:
        # 检查是否已存在
        existing = db.query(Publication).filter(Publication.pmid == request.pmid).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Publication already exists: {request.pmid}"
            )

        # 使用 DatabaseService 创建文献
        with DatabaseService() as db_service:
            publication = db_service.create_publication(request.to_dict())

        logger.info(f"Created publication: {publication.pmid}")

        return PublicationDetailSerializer.model_validate(publication)

    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic 验证错误
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating publication: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/stats")
async def get_publications_stats(
    db: Session = Depends(get_db)
):
    """
    获取文献统计信息

    返回：
    - 总数
    - 期刊分布（Top 10）
    - 文献类型分布
    - 最新文献日期
    """
    try:
        from sqlalchemy import func

        # 总数
        total = db.query(Publication).count()

        # 期刊分布（Top 10）
        journal_dist = db.query(
            Publication.journal,
            func.count(Publication.pmid)
        ).group_by(
            Publication.journal
        ).order_by(
            func.count(Publication.pmid).desc()
        ).limit(10).all()

        # 文献类型分布
        type_dist = db.query(
            Publication.publication_type,
            func.count(Publication.pmid)
        ).group_by(
            Publication.publication_type
        ).order_by(
            func.count(Publication.pmid).desc()
        ).all()

        # 最新文献日期
        latest = db.query(Publication).order_by(Publication.pub_date.desc()).first()
        latest_date = latest.pub_date.isoformat() if latest and latest.pub_date else None

        return {
            "total": total,
            "latest_date": latest_date,
            "journal_distribution": [
                {"journal": journal or "Unknown", "count": count}
                for journal, count in journal_dist
            ],
            "type_distribution": [
                {"type": pub_type or "Unknown", "count": count}
                for pub_type, count in type_dist
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{pmid}")
async def get_publication_detail(
    pmid: str,
    db: Session = Depends(get_db)
):
    """
    获取文献详情

    参数：
    - pmid: PubMed ID
    """
    try:
        publication = db.query(Publication).filter(Publication.pmid == pmid).first()

        if not publication:
            raise HTTPException(status_code=404, detail=f"Publication not found: {pmid}")

        return PublicationDetailSerializer.model_validate(publication)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching publication detail: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{pmid}/link", response_model=LinkResponse)
async def link_publication_to_target(
    pmid: str,
    request: TargetPublicationLinkRequest,
    db: Session = Depends(get_db)
):
    """
    关联文献到靶点

    参数：
    - pmid: PubMed ID
    - request: 关联请求（包含 target_id、relation_type、evidence_snippet）

    返回：
    - 关联结果
    """
    try:
        # 验证文献存在
        publication = db.query(Publication).filter(Publication.pmid == pmid).first()
        if not publication:
            raise HTTPException(status_code=404, detail=f"Publication not found: {pmid}")

        # 验证靶点存在
        target = db.query(Target).filter(Target.target_id == request.target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail=f"Target not found: {request.target_id}")

        # 使用 DatabaseService 创建关联
        with DatabaseService() as db_service:
            db_service.link_target_publication(
                target_id=request.target_id,
                pmid=pmid,
                relation_type=request.relation_type,
                evidence_snippet=request.evidence_snippet
            )

        logger.info(f"Linked publication {pmid} to target {request.target_id}")

        return LinkResponse(
            success=True,
            message="Successfully linked publication to target",
            target_id=request.target_id,
            pmid=pmid
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic 验证错误
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error linking publication: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{pmid}/targets")
async def get_publication_targets(
    pmid: str,
    db: Session = Depends(get_db)
):
    """
    获取文献关联的靶点列表

    参数：
    - pmid: PubMed ID

    返回：
    - 靶点列表
    """
    try:
        # 验证文献存在
        publication = db.query(Publication).filter(Publication.pmid == pmid).first()
        if not publication:
            raise HTTPException(status_code=404, detail=f"Publication not found: {pmid}")

        # 查询关联的靶点
        from models.relationships import TargetPublication

        targets = db.query(Target).join(
            TargetPublication,
            TargetPublication.target_id == Target.target_id
        ).filter(
            TargetPublication.pmid == pmid
        ).all()

        return [
            {
                "target_id": t.target_id,
                "standard_name": t.standard_name,
                "aliases": t.aliases,
                "relation_type": next(
                    (tp.relation_type for tp in db.query(TargetPublication).filter(
                        TargetPublication.pmid == pmid,
                        TargetPublication.target_id == t.target_id
                    ).all()),
                    "unknown"
                )
            }
            for t in targets
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching targets: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
