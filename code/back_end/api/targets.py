"""
=====================================================
Targets API 路由
=====================================================

提供靶点（Target）相关的 RESTful API 接口：
- GET /api/v1/targets: 获取靶点列表（支持搜索、分页）
- GET /api/v1/targets/{id}: 获取靶点详情
- GET /api/v1/targets/{id}/publications: 获取靶点相关文献
- GET /api/v1/targets/{id}/pipelines: 获取靶点相关管线

使用示例（FastAPI 自动文档）：
访问 http://localhost:8000/docs 查看完整 API 文档
=====================================================
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import uuid

from utils.database import get_db
from utils.serializers import (
    TargetListItemSerializer,
    TargetDetailSerializer,
    PublicationListItemSerializer,
    PipelineListItemSerializer,
    TargetStatsSerializer,
)
from utils.validators import TargetCreateRequest, TargetUpdateRequest
from models.target import Target
from models.publication import Publication
from models.pipeline import Pipeline
from services.database_service import DatabaseService
from core.logger import get_logger

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/api/v1/targets", tags=["Targets"])


# =====================================================
# API 接口
# =====================================================


@router.get("")
async def list_targets(
    keyword: Optional[str] = Query(None, description="搜索关键词（标准名称）"),
    category: Optional[str] = Query(None, description="分类过滤（如：激酶、受体）"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量（分页）"),
    db: Session = Depends(get_db)
):
    """
    获取靶点列表

    支持功能：
    - 搜索：按标准名称模糊搜索
    - 过滤：按分类过滤
    - 分页：支持 limit + offset
    """
    try:
        logger.info(f"Fetching targets with filters: keyword={keyword}, category={category}, limit={limit}")

        # 构建查询
        query = db.query(Target)

        # 关键词搜索
        if keyword:
            query = query.filter(Target.standard_name.ilike(f"%{keyword}%"))

        # 分类过滤
        if category:
            query = query.filter(Target.category == category)

        # 排序：按标准名称
        query = query.order_by(Target.standard_name)

        # 分页
        query = query.offset(offset).limit(limit)

        targets = query.all()

        logger.info(f"Found {len(targets)} targets")

        # 使用序列化器转换
        return [TargetListItemSerializer.model_validate(t) for t in targets]

    except Exception as e:
        logger.error(f"Error fetching targets: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("")
async def create_target(
    request: TargetCreateRequest,
    db: Session = Depends(get_db)
):
    """
    创建靶点

    使用 Pydantic 验证数据：
    - standard_name: 标准名称（必填，字母数字和连字符，必须以字母开头）
    - aliases: 别名列表（自动去重）
    - gene_id: Gene ID（必须是数字）
    - uniprot_id: UniProt ID
    - category: 分类
    - description: 描述

    返回：
    - 创建的靶点详情
    """
    try:
        # 检查是否已存在
        existing = db.query(Target).filter(Target.standard_name == request.standard_name).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Target already exists: {request.standard_name}"
            )

        # 使用 DatabaseService 创建靶点
        with DatabaseService() as db_service:
            # 使用 validator 的 to_model() 方法转换为 ORM 模型
            target = request.to_model()
            # 或者使用 to_dict() + create_target
            target = db_service.create_target(request.to_dict())

        logger.info(f"Created target: {target.standard_name}")

        return TargetDetailSerializer.model_validate(target)

    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic 验证错误
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating target: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/stats")
async def get_targets_stats(
    db: Session = Depends(get_db)
):
    """
    获取靶点统计信息

    返回：
    - 总数
    - 分类分布
    - 有文献的靶点数
    - 有管线的靶点数
    """
    try:
        from sqlalchemy import func

        # 总数
        total = db.query(Target).count()

        # 分类分布
        category_dist = db.query(
            Target.category,
            func.count(Target.target_id)
        ).group_by(Target.category).all()

        # 有文献的靶点数
        from models.relationships import TargetPublication
        with_pubs = db.query(TargetPublication.target_id).distinct().count()

        # 有管线的靶点数
        from models.relationships import TargetPipeline
        with_pipelines = db.query(TargetPipeline.target_id).distinct().count()

        return {
            "total": total,
            "with_publications": with_pubs,
            "with_pipelines": with_pipelines,
            "category_distribution": [
                {"category": cat or "未分类", "count": count}
                for cat, count in category_dist
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{target_id}")
async def get_target_detail(
    target_id: str,
    db: Session = Depends(get_db)
):
    """
    获取靶点详情

    参数：
    - target_id: 靶点 UUID
    """
    try:
        # 验证 UUID 格式
        try:
            uuid.UUID(target_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        target = db.query(Target).filter(Target.target_id == target_id).first()

        if not target:
            raise HTTPException(status_code=404, detail=f"Target not found: {target_id}")

        return TargetDetailSerializer.model_validate(target)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching target detail: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{target_id}/publications")
async def get_target_publications(
    target_id: str,
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    获取靶点相关文献

    参数：
    - target_id: 靶点 UUID
    - limit: 返回数量限制
    - offset: 偏移量

    返回：
    - 文献列表（按发布日期降序）
    """
    try:
        # 验证 UUID 格式
        try:
            uuid.UUID(target_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        # 验证靶点存在
        target = db.query(Target).filter(Target.target_id == target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail=f"Target not found: {target_id}")

        # 查询相关文献
        from models.relationships import TargetPublication

        publications = db.query(Publication).join(
            TargetPublication,
            TargetPublication.pmid == Publication.pmid
        ).filter(
            TargetPublication.target_id == target_id
        ).order_by(
            Publication.pub_date.desc()
        ).offset(offset).limit(limit).all()

        logger.info(f"Found {len(publications)} publications for target {target_id}")

        # 使用序列化器转换
        return [PublicationListItemSerializer.model_validate(p) for p in publications]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching publications: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{target_id}/pipelines")
async def get_target_pipelines(
    target_id: str,
    phase: Optional[str] = Query(None, description="阶段过滤（如：Phase 3）"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    获取靶点相关管线

    参数：
    - target_id: 靶点 UUID
    - phase: 阶段过滤
    - limit: 返回数量限制
    - offset: 偏移量

    返回：
    - 管线列表（按最后见到时间降序）
    """
    try:
        # 验证 UUID 格式
        try:
            uuid.UUID(target_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        # 验证靶点存在
        target = db.query(Target).filter(Target.target_id == target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail=f"Target not found: {target_id}")

        # 查询相关管线
        from models.relationships import TargetPipeline

        query = db.query(Pipeline).join(
            TargetPipeline,
            TargetPipeline.pipeline_id == Pipeline.pipeline_id
        ).filter(
            TargetPipeline.target_id == target_id
        )

        # 阶段过滤
        if phase:
            query = query.filter(Pipeline.phase == phase)

        # 排序和分页
        pipelines = query.order_by(
            Pipeline.last_seen_at.desc()
        ).offset(offset).limit(limit).all()

        logger.info(f"Found {len(pipelines)} pipelines for target {target_id}")

        # 使用序列化器转换
        return [PipelineListItemSerializer.model_validate(p) for p in pipelines]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pipelines: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
