"""
=====================================================
Admin API - 管理功能接口
=====================================================

提供管理员功能的 API 端点：
- 软删除/恢复管线
- 软删除/恢复靶点
- 查看已删除数据

作者：A_lxl_search Team
创建日期：2026-03-12
=====================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from uuid import UUID

from utils.database import get_db
from models.pipeline import Pipeline
from models.target import Target
from loguru import logger

router = APIRouter(prefix="/api/admin", tags=["admin"])


# =====================================================
# 请求/响应模型
# =====================================================

class SoftDeleteResponse(BaseModel):
    """软删除响应"""
    success: bool
    message: str
    id: str = None


class RestoreResponse(BaseModel):
    """恢复响应"""
    success: bool
    message: str
    id: str = None


class DeletedItemResponse(BaseModel):
    """已删除项目响应"""
    id: str
    name: str
    deleted_at: str
    type: str


# =====================================================
# Pipeline 软删除端点
# =====================================================

@router.post("/pipeline/{pipeline_id}/soft-delete", response_model=SoftDeleteResponse)
def soft_delete_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    软删除管线

    将管线标记为已删除，数据不会真正从数据库删除
    """
    try:
        pipeline = db.query(Pipeline).filter(
            Pipeline.pipeline_id == UUID(pipeline_id)
        ).first()

        if not pipeline:
            raise HTTPException(status_code=404, detail="管线不存在")

        if pipeline.is_deleted():
            raise HTTPException(status_code=400, detail="该管线已被删除")

        pipeline.soft_delete()
        db.commit()

        logger.info(f"软删除管线: {pipeline.drug_code} by {pipeline.company_name}")

        return SoftDeleteResponse(
            success=True,
            message=f"管线 {pipeline.drug_code} 已软删除",
            id=str(pipeline.pipeline_id)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的UUID格式: {pipeline_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"软删除管线失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/{pipeline_id}/restore", response_model=RestoreResponse)
def restore_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    恢复已删除的管线
    """
    try:
        pipeline = db.query(Pipeline).filter(
            Pipeline.pipeline_id == UUID(pipeline_id)
        ).first()

        if not pipeline:
            raise HTTPException(status_code=404, detail="管线不存在")

        if not pipeline.is_deleted():
            raise HTTPException(status_code=400, detail="该管线未被删除")

        pipeline.restore()
        db.commit()

        logger.info(f"恢复管线: {pipeline.drug_code} by {pipeline.company_name}")

        return RestoreResponse(
            success=True,
            message=f"管线 {pipeline.drug_code} 已恢复",
            id=str(pipeline.pipeline_id)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的UUID格式: {pipeline_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"恢复管线失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# Target 软删除端点
# =====================================================

@router.post("/target/{target_id}/soft-delete", response_model=SoftDeleteResponse)
def soft_delete_target(
    target_id: str,
    db: Session = Depends(get_db)
):
    """
    软删除靶点

    将靶点标记为已删除，数据不会真正从数据库删除
    """
    try:
        target = db.query(Target).filter(
            Target.target_id == UUID(target_id)
        ).first()

        if not target:
            raise HTTPException(status_code=404, detail="靶点不存在")

        if target.is_deleted():
            raise HTTPException(status_code=400, detail="该靶点已被删除")

        target.soft_delete()
        db.commit()

        logger.info(f"软删除靶点: {target.standard_name}")

        return SoftDeleteResponse(
            success=True,
            message=f"靶点 {target.standard_name} 已软删除",
            id=str(target.target_id)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的UUID格式: {target_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"软删除靶点失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/target/{target_id}/restore", response_model=RestoreResponse)
def restore_target(
    target_id: str,
    db: Session = Depends(get_db)
):
    """
    恢复已删除的靶点
    """
    try:
        target = db.query(Target).filter(
            Target.target_id == UUID(target_id)
        ).first()

        if not target:
            raise HTTPException(status_code=404, detail="靶点不存在")

        if not target.is_deleted():
            raise HTTPException(status_code=400, detail="该靶点未被删除")

        target.restore()
        db.commit()

        logger.info(f"恢复靶点: {target.standard_name}")

        return RestoreResponse(
            success=True,
            message=f"靶点 {target.standard_name} 已恢复",
            id=str(target.target_id)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的UUID格式: {target_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"恢复靶点失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 查询已删除数据
# =====================================================

@router.get("/deleted/pipelines", response_model=List[dict])
def get_deleted_pipelines(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    获取已删除的管线列表

    用于管理员查看和恢复
    """
    pipelines = db.query(Pipeline).filter(
        Pipeline.deleted_at.isnot(None)
    ).order_by(
        Pipeline.deleted_at.desc()
    ).offset(offset).limit(limit).all()

    return [p.to_dict() for p in pipelines]


@router.get("/deleted/targets", response_model=List[dict])
def get_deleted_targets(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    获取已删除的靶点列表

    用于管理员查看和恢复
    """
    targets = db.query(Target).filter(
        Target.deleted_at.isnot(None)
    ).order_by(
        Target.deleted_at.desc()
    ).offset(offset).limit(limit).all()

    return [t.to_dict() for t in targets]


@router.get("/stats/deleted")
def get_deleted_stats(db: Session = Depends(get_db)):
    """
    获取删除统计信息

    返回活跃/已删除数据的数量对比
    """
    pipeline_stats = db.execute("""
        SELECT
            COUNT(*) FILTER (WHERE deleted_at IS NULL) AS active,
            COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted
        FROM pipeline
    """).fetchone()

    target_stats = db.execute("""
        SELECT
            COUNT(*) FILTER (WHERE deleted_at IS NULL) AS active,
            COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted
        FROM target
    """).fetchone()

    return {
        "pipeline": {
            "active": pipeline_stats[0] if pipeline_stats else 0,
            "deleted": pipeline_stats[1] if pipeline_stats else 0
        },
        "target": {
            "active": target_stats[0] if target_stats else 0,
            "deleted": target_stats[1] if target_stats else 0
        }
    }
