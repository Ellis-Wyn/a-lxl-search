"""
=====================================================
Pipeline API 路由
=====================================================

提供 Pipeline 相关的 RESTful API 接口：
- POST /api/pipeline: 创建管线
- GET /api/pipeline/search: 搜索管线
- GET /api/pipeline/company/{name}: 获取公司管线
- GET /api/pipeline/target/{id}: 获取靶点管线
- POST /api/pipeline/update-and-detect: 更新并检测变化

使用示例（FastAPI 自动文档）：
访问 http://localhost:8000/docs 查看完整 API 文档
=====================================================
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services.pipeline_service import PipelineService, get_pipeline_service, PipelineStats
from services.phase_mapper import StandardPhase
from utils.validators import PipelineCreateRequest as PipelineCreateRequestValidator
from core.logger import get_logger

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


# =====================================================
# 请求/响应模型
# =====================================================


# 使用 utils/validators.py 中的 PipelineCreateRequest 替代本地定义
# PipelineCreateRequest = PipelineCreateRequestValidator


class PipelineResponse(BaseModel):
    """管线响应"""
    pipeline_id: str
    drug_code: str
    company_name: str
    indication: str
    phase: str
    phase_normalized: str
    modality: Optional[str] = None
    source_url: str
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None


class PipelineSearchRequest(BaseModel):
    """管线搜索请求"""
    keyword: Optional[str] = Field(None, description="关键词")
    target_name: Optional[str] = Field(None, description="靶点名称")
    company_name: Optional[str] = Field(None, description="公司名称")
    phase: Optional[str] = Field(None, description="阶段")
    moa_type: Optional[str] = Field(None, description="药物类型（Small Molecule/ADC/CAR-T等）")
    limit: int = Field(50, ge=1, le=500, description="返回数量限制")


class PhaseJumpResponse(BaseModel):
    """Phase Jump 响应"""
    pipeline_id: int
    drug_code: str
    company_name: str
    indication: str
    old_phase: str
    new_phase: str
    jump_days: int
    confidence: float
    detected_at: str


class ChangeReportResponse(BaseModel):
    """变化报告响应"""
    total_changes: int
    new_pipelines: List[dict]
    phase_jumps: List[PhaseJumpResponse]
    disappeared_pipelines: List[dict]
    reappeared_pipelines: List[dict]
    info_updates: int
    scan_date: str


class UpdateDetectRequest(BaseModel):
    """更新并检测请求"""
    company_name: str = Field(..., description="公司名称")
    new_pipelines: List[dict] = Field(..., description="新管线数据")
    disappeared_threshold_days: int = Field(180, ge=0, description="消失判定阈值（天）")


class PipelineStatsResponse(BaseModel):
    """管线统计响应"""
    total_pipelines: int
    by_company: dict
    by_phase: dict
    by_target: dict
    phase_jump_count_30d: int


# =====================================================
# 依赖项
# =====================================================


def get_pipeline_service_dep() -> PipelineService:
    """
    获取 PipelineService 实例（依赖注入）

    Returns:
        PipelineService 实例
    """
    return get_pipeline_service()


# =====================================================
# API 路由
# =====================================================


@router.post("/", response_model=PipelineResponse)
async def create_pipeline(
    request: PipelineCreateRequestValidator,
    service: PipelineService = Depends(get_pipeline_service_dep),
):
    """
    创建管线

    示例：
    ```json
    {
      "drug_code": "SHR-1210",
      "company_name": "恒瑞医药",
      "indication": "NSCLC",
      "phase": "Phase 3",
      "modality": "单抗",
      "source_url": "https://...",
      "targets": ["PD-1"]
    }
    ```
    """
    try:
        # 使用 validator 的 to_dict() 方法，包含所有验证后的数据
        pipeline_data = request.to_dict()

        # 处理 targets 字段（如果提供）
        targets = pipeline_data.pop('targets', None)

        # 创建管线
        pipeline = await service.create_pipeline(pipeline_data)

        # 如果有靶点，创建关联
        if targets:
            # TODO: 实现 Pipeline-Target 关联逻辑
            logger.info(f"Would link pipeline to targets: {targets}")

        return PipelineResponse(**pipeline)
    except ValueError as e:
        # Pydantic 验证错误
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Create pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[PipelineResponse])
async def search_pipelines(
    keyword: Optional[str] = None,
    target_name: Optional[str] = None,
    company_name: Optional[str] = None,
    phase: Optional[str] = None,
    moa_type: Optional[str] = Query(None, description="药物类型筛选（Small Molecule/ADC/CAR-T等）"),
    limit: int = Query(50, ge=1, le=500),
    service: PipelineService = Depends(get_pipeline_service_dep),
):
    """
    搜索管线（集成MoA类型筛选）

    参数：
    - keyword: 关键词（搜索 drug_code 和 indication）
    - target_name: 靶点名称
    - company_name: 公司名称
    - phase: 阶段
    - moa_type: 药物类型（新增）
    - limit: 返回数量限制
    """
    try:
        pipelines = await service.search_pipelines(
            keyword=keyword,
            target_name=target_name,
            company_name=company_name,
            phase=phase,
            moa_type=moa_type,  # 新增MoA类型筛选
            limit=limit,
        )

        return [PipelineResponse(**p) for p in pipelines]
    except Exception as e:
        logger.error(f"Search pipelines failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_name}", response_model=List[PipelineResponse])
async def get_company_pipelines(
    company_name: str,
    target_filter: Optional[str] = None,
    phase_filter: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    service: PipelineService = Depends(get_pipeline_service_dep),
):
    """
    获取公司管线

    参数：
    - company_name: 公司名称
    - target_filter: 靶点过滤
    - phase_filter: 阶段过滤
    - limit: 返回数量限制
    """
    try:
        pipelines = await service.get_pipelines_by_company(
            company_name=company_name,
            target_filter=target_filter,
            phase_filter=phase_filter,
            limit=limit,
        )

        return [PipelineResponse(**p) for p in pipelines]
    except Exception as e:
        logger.error(f"Get company pipelines failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[PipelineResponse])
async def list_pipelines(
    keyword: Optional[str] = Query(None, description="关键词（药物代码/适应症）"),
    company_name: Optional[str] = Query(None, description="公司名称过滤"),
    phase: Optional[str] = Query(None, description="阶段过滤"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: PipelineService = Depends(get_pipeline_service_dep),
):
    """
    获取管线列表

    参数：
    - keyword: 关键词搜索（药物代码/适应症）
    - company_name: 公司名称过滤
    - phase: 阶段过滤
    - limit: 返回数量限制
    - offset: 偏移量（分页）
    """
    try:
        pipelines = await service.search_pipelines(
            keyword=keyword or "",
            company_name=company_name,
            phase=phase,
            limit=limit,
        )

        # 应用 offset
        if offset > 0:
            pipelines = pipelines[offset:]

        return [PipelineResponse(**p) for p in pipelines]
    except Exception as e:
        logger.error(f"List pipelines failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/target/{target_id}", response_model=List[PipelineResponse])
async def get_target_pipelines(
    target_id: int,
    phase_filter: Optional[str] = None,
    company_filter: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    service: PipelineService = Depends(get_pipeline_service_dep),
):
    """
    获取靶点管线

    参数：
    - target_id: 靶点 ID
    - phase_filter: 阶段过滤
    - company_filter: 公司过滤
    - limit: 返回数量限制
    """
    try:
        pipelines = await service.get_pipelines_by_target(
            target_id=target_id,
            phase_filter=phase_filter,
            company_filter=company_filter,
            limit=limit,
        )

        return [PipelineResponse(**p) for p in pipelines]
    except Exception as e:
        logger.error(f"Get target pipelines failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-and-detect", response_model=ChangeReportResponse)
async def update_and_detect(
    request: UpdateDetectRequest,
    service: PipelineService = Depends(get_pipeline_service_dep),
):
    """
    批量更新公司管线并检测变化

    功能：
    - 更新管线数据
    - 检测 Phase Jump
    - 检测消失管线
    - 生成变化报告

    示例：
    ```json
    {
      "company_name": "恒瑞医药",
      "new_pipelines": [
        {
          "drug_code": "SHR-1210",
          "indication": "NSCLC",
          "phase": "Phase 3",
          "source_url": "https://..."
        }
      ],
      "disappeared_threshold_days": 180
    }
    ```
    """
    try:
        report = await service.update_and_detect(
            company_name=request.company_name,
            new_pipelines=request.new_pipelines,
            disappeared_threshold_days=request.disappeared_threshold_days,
        )

        return ChangeReportResponse(**report.to_dict())
    except Exception as e:
        logger.error(f"Update and detect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=PipelineStatsResponse)
async def get_statistics(
    company_name: Optional[str] = None,
    target_id: Optional[int] = None,
    service: PipelineService = Depends(get_pipeline_service_dep),
):
    """
    获取管线统计信息

    参数：
    - company_name: 公司过滤
    - target_id: 靶点过滤
    """
    try:
        stats = await service.get_statistics(
            company_name=company_name,
            target_id=target_id,
        )

        return PipelineStatsResponse(**stats.__dict__)
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phases", response_model=List[str])
async def list_standard_phases():
    """
    获取所有标准阶段列表

    返回支持的标准阶段名称
    """
    phases = [phase.value for phase in StandardPhase]
    return phases


@router.get("/health")
async def health_check():
    """
    健康检查

    Returns:
        服务状态
    """
    return {
        "status": "healthy",
        "service": "Pipeline API",
    }


# =====================================================
# 导出
# =====================================================

__all__ = ["router"]
