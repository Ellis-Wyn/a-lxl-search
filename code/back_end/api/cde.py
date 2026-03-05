"""
=====================================================
CDE 事件 API 路由（CDE Events API）
=====================================================

提供 CDE（药审中心）事件查询接口：
- GET /api/cde/events: 查询 CDE 事件
- GET /api/cde/events/stats: 获取 CDE 事件统计
- GET /api/cde/events/{acceptance_no}: 获取单个事件详情

使用示例：
    # 查询所有 IND 事件
    curl "http://localhost:8000/api/cde/events?event_type=IND&limit=10"

    # 查询特定申请人的事件
    curl "http://localhost:8000/api/cde/events?applicant=恒瑞医药"

    # 获取事件统计
    curl "http://localhost:8000/api/cde/events/stats"
=====================================================
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from utils.database import SessionLocal
from models.cde_event import CDEEvent
from core.logger import get_logger

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/api/cde", tags=["CDE"])


# =====================================================
# 请求/响应模型
# =====================================================


class CDEEventResponse(BaseModel):
    """CDE事件响应"""
    acceptance_no: str = Field(..., description="受理号")
    event_type: str = Field(..., description="事件类型 IND/CTA/NDA/BLA")
    drug_name: str = Field(..., description="药品名称")
    applicant: str = Field(..., description="申请人")
    indication: Optional[str] = Field(None, description="适应症")
    drug_type: Optional[str] = Field(None, description="药物类型")
    registration_class: Optional[str] = Field(None, description="注册分类")
    undertake_date: Optional[str] = Field(None, description="承办日期")
    acceptance_date: Optional[str] = Field(None, description="受理日期")
    public_date: Optional[str] = Field(None, description="公示日期")
    review_status: Optional[str] = Field(None, description="审评状态")
    public_page_url: str = Field(..., description="公示页面URL")
    source_urls: List[str] = Field(default_factory=list, description="所有相关URL")
    first_seen_at: str = Field(..., description="首次发现时间")
    last_seen_at: str = Field(..., description="最后更新时间")

    class Config:
        from_attributes = True


class CDEEventStatsResponse(BaseModel):
    """CDE事件统计响应"""
    total_count: int = Field(..., description="总事件数")
    by_event_type: Dict[str, int] = Field(..., description="按事件类型分组")
    by_applicant: Dict[str, int] = Field(..., description="按申请人分组（Top 10）")
    by_drug_type: Dict[str, int] = Field(..., description="按药物类型分组")
    recent_7_days: int = Field(..., description="近7天新增")
    recent_30_days: int = Field(..., description="近30天新增")
    latest_events: List[CDEEventResponse] = Field(..., description="最新事件（Top 5）")


# =====================================================
# API 路由
# =====================================================


@router.get("/events", response_model=List[CDEEventResponse])
async def get_cde_events(
    event_type: Optional[str] = Query(None, description="事件类型筛选 IND/CTA/NDA/BLA/补充资料"),
    applicant: Optional[str] = Query(None, description="申请人筛选"),
    drug_name: Optional[str] = Query(None, description="药品名称筛选"),
    indication: Optional[str] = Query(None, description="适应症筛选（模糊匹配）"),
    drug_type: Optional[str] = Query(None, description="药物类型筛选（化药/生物制品/中药）"),
    registration_class: Optional[str] = Query(None, description="注册分类筛选（1类/2类等）"),
    review_status: Optional[str] = Query(None, description="审评状态筛选"),
    date_from: Optional[str] = Query(None, description="起始日期（承办日期）YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期（承办日期）YYYY-MM-DD"),
    sort_by: str = Query("undertake_date", description="排序字段：undertake_date/acceptance_date/first_seen_at"),
    sort_order: str = Query("desc", description="排序方向：asc/desc"),
    limit: int = Query(100, ge=1, le=500, description="结果数量限制"),
    offset: int = Query(0, ge=0, description="偏移量（分页）")
):
    """
    查询 CDE 事件

    功能：
    - 多条件筛选查询
    - 支持分页
    - 支持排序
    - 数据可追溯性（返回所有source_urls）

    参数：
    - event_type: 事件类型（IND/CTA/NDA/BLA/补充资料）
    - applicant: 申请人（企业名称）
    - drug_name: 药品名称
    - indication: 适应症（模糊匹配）
    - drug_type: 药物类型（化药/生物制品/中药）
    - registration_class: 注册分类（1类/2类等）
    - review_status: 审评状态
    - date_from/date_to: 承办日期范围
    - sort_by: 排序字段
    - sort_order: 排序方向（asc/desc）
    - limit: 结果数量限制（最大500）
    - offset: 偏移量（用于分页）

    返回：
    ```json
    [
      {
        "acceptance_no": "CXSL2400001",
        "event_type": "IND",
        "drug_name": "EGFR抑制剂",
        "applicant": "江苏恒瑞医药股份有限公司",
        "indication": "非小细胞肺癌",
        "undertake_date": "2024-01-15",
        "public_page_url": "https://www.cde.org.cn/...",
        "source_urls": ["https://www.cde.org.cn/...", "..."],
        ...
      }
    ]
    ```

    示例：
    ```bash
    # 查询所有 IND 事件
    curl "http://localhost:8000/api/cde/events?event_type=IND&limit=10"

    # 查询恒瑞医药的 NDA 事件
    curl "http://localhost:8000/api/cde/events?applicant=恒瑞&event_type=NDA"

    # 查询近30天的事件
    curl "http://localhost:8000/api/cde/events?date_from=2024-01-01&sort_by=undertake_date&sort_order=desc"

    # 分页查询
    curl "http://localhost:8000/api/cde/events?limit=20&offset=20"
    ```
    """
    try:
        db = SessionLocal()
        query = db.query(CDEEvent).filter(CDEEvent.is_active == True)

        # 应用筛选条件
        if event_type:
            query = query.filter(CDEEvent.event_type == event_type)

        if applicant:
            query = query.filter(CDEEvent.applicant.ilike(f"%{applicant}%"))

        if drug_name:
            query = query.filter(CDEEvent.drug_name.ilike(f"%{drug_name}%"))

        if indication:
            query = query.filter(CDEEvent.indication.ilike(f"%{indication}%"))

        if drug_type:
            query = query.filter(CDEEvent.drug_type == drug_type)

        if registration_class:
            query = query.filter(CDEEvent.registration_class == registration_class)

        if review_status:
            query = query.filter(CDEEvent.review_status == review_status)

        if date_from:
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(CDEEvent.undertake_date >= start_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date_from format: {date_from}. Expected YYYY-MM-DD"
                )

        if date_to:
            try:
                end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(CDEEvent.undertake_date <= end_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date_to format: {date_to}. Expected YYYY-MM-DD"
                )

        # 排序
        sort_column = None
        if sort_by == "undertake_date":
            sort_column = CDEEvent.undertake_date
        elif sort_by == "acceptance_date":
            sort_column = CDEEvent.acceptance_date
        elif sort_by == "first_seen_at":
            sort_column = CDEEvent.first_seen_at
        else:
            sort_column = CDEEvent.undertake_date  # 默认按承办日期排序

        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # 分页
        total_count = query.count()
        events = query.offset(offset).limit(limit).all()

        # 转换为响应格式
        results = []
        for event in events:
            results.append(CDEEventResponse(
                acceptance_no=event.acceptance_no,
                event_type=event.event_type,
                drug_name=event.drug_name,
                applicant=event.applicant,
                indication=event.indication,
                drug_type=event.drug_type,
                registration_class=event.registration_class,
                undertake_date=event.undertake_date.isoformat() if event.undertake_date else None,
                acceptance_date=event.acceptance_date.isoformat() if event.acceptance_date else None,
                public_date=event.public_date.isoformat() if event.public_date else None,
                review_status=event.review_status,
                public_page_url=event.public_page_url,
                source_urls=event.get_source_urls(),
                first_seen_at=event.first_seen_at.isoformat() if event.first_seen_at else None,
                last_seen_at=event.last_seen_at.isoformat() if event.last_seen_at else None
            ))

        logger.info(
            f"CDE events query completed",
            extra={
                "total_count": total_count,
                "returned": len(results),
                "filters": {
                    "event_type": event_type,
                    "applicant": applicant,
                    "date_from": date_from,
                    "date_to": date_to
                }
            }
        )

        db.close()
        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get CDE events failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/stats", response_model=CDEEventStatsResponse)
async def get_cde_event_stats():
    """
    获取 CDE 事件统计

    功能：
    - 总事件数统计
    - 按事件类型分组
    - 按申请人分组（Top 10）
    - 按药物类型分组
    - 近期新增趋势（7天/30天）
    - 最新事件列表

    返回：
    ```json
    {
      "total_count": 1500,
      "by_event_type": {"IND": 800, "NDA": 400, "BLA": 200, "补充资料": 100},
      "by_applicant": {"江苏恒瑞医药": 150, "百济神州": 120, ...},
      "by_drug_type": {"化药": 1000, "生物制品": 450, "中药": 50},
      "recent_7_days": 25,
      "recent_30_days": 120,
      "latest_events": [...]
    }
    ```

    示例：
    ```bash
    curl "http://localhost:8000/api/cde/events/stats"
    ```
    """
    try:
        db = SessionLocal()

        # 总事件数
        total_count = db.query(CDEEvent).filter(CDEEvent.is_active == True).count()

        # 按事件类型分组
        event_type_counts = {}
        for event_type in ["IND", "CTA", "NDA", "BLA", "补充资料"]:
            count = db.query(CDEEvent).filter(
                CDEEvent.is_active == True,
                CDEEvent.event_type == event_type
            ).count()
            if count > 0:
                event_type_counts[event_type] = count

        # 按申请人分组（Top 10）
        applicant_counts = {}
        from sqlalchemy import func
        applicant_results = db.query(
            CDEEvent.applicant,
            func.count(CDEEvent.acceptance_no)
        ).filter(
            CDEEvent.is_active == True
        ).group_by(
            CDEEvent.applicant
        ).order_by(
            func.count(CDEEvent.acceptance_no).desc()
        ).limit(10).all()

        for applicant, count in applicant_results:
            applicant_counts[applicant] = count

        # 按药物类型分组
        drug_type_counts = {}
        drug_type_results = db.query(
            CDEEvent.drug_type,
            func.count(CDEEvent.acceptance_no)
        ).filter(
            CDEEvent.is_active == True,
            CDEEvent.drug_type.isnot(None)
        ).group_by(
            CDEEvent.drug_type
        ).all()

        for drug_type, count in drug_type_results:
            if drug_type:
                drug_type_counts[drug_type] = count

        # 近7天新增
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_7_days = db.query(CDEEvent).filter(
            CDEEvent.is_active == True,
            CDEEvent.first_seen_at >= seven_days_ago
        ).count()

        # 近30天新增
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_30_days = db.query(CDEEvent).filter(
            CDEEvent.is_active == True,
            CDEEvent.first_seen_at >= thirty_days_ago
        ).count()

        # 最新事件（Top 5）
        latest_events = db.query(CDEEvent).filter(
            CDEEvent.is_active == True
        ).order_by(
            CDEEvent.first_seen_at.desc()
        ).limit(5).all()

        latest_events_response = []
        for event in latest_events:
            latest_events_response.append(CDEEventResponse(
                acceptance_no=event.acceptance_no,
                event_type=event.event_type,
                drug_name=event.drug_name,
                applicant=event.applicant,
                indication=event.indication,
                drug_type=event.drug_type,
                registration_class=event.registration_class,
                undertake_date=event.undertake_date.isoformat() if event.undertake_date else None,
                acceptance_date=event.acceptance_date.isoformat() if event.acceptance_date else None,
                public_date=event.public_date.isoformat() if event.public_date else None,
                review_status=event.review_status,
                public_page_url=event.public_page_url,
                source_urls=event.get_source_urls(),
                first_seen_at=event.first_seen_at.isoformat() if event.first_seen_at else None,
                last_seen_at=event.last_seen_at.isoformat() if event.last_seen_at else None
            ))

        db.close()

        logger.info("CDE events stats retrieved")

        return CDEEventStatsResponse(
            total_count=total_count,
            by_event_type=event_type_counts,
            by_applicant=applicant_counts,
            by_drug_type=drug_type_counts,
            recent_7_days=recent_7_days,
            recent_30_days=recent_30_days,
            latest_events=latest_events_response
        )

    except Exception as e:
        logger.error(f"Get CDE event stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{acceptance_no}", response_model=CDEEventResponse)
async def get_cde_event_detail(acceptance_no: str):
    """
    获取单个 CDE 事件详情

    参数：
    - acceptance_no: 受理号（唯一标识）

    返回：
    ```json
    {
      "acceptance_no": "CXSL2400001",
      "event_type": "IND",
      "drug_name": "EGFR抑制剂",
      "applicant": "江苏恒瑞医药股份有限公司",
      "indication": "非小细胞肺癌",
      ...
    }
    ```

    示例：
    ```bash
    curl "http://localhost:8000/api/cde/events/CXSL2400001"
    ```
    """
    try:
        db = SessionLocal()
        event = db.query(CDEEvent).filter(
            CDEEvent.acceptance_no == acceptance_no,
            CDEEvent.is_active == True
        ).first()

        if not event:
            db.close()
            raise HTTPException(
                status_code=404,
                detail=f"CDE event not found: {acceptance_no}"
            )

        result = CDEEventResponse(
            acceptance_no=event.acceptance_no,
            event_type=event.event_type,
            drug_name=event.drug_name,
            applicant=event.applicant,
            indication=event.indication,
            drug_type=event.drug_type,
            registration_class=event.registration_class,
            undertake_date=event.undertake_date.isoformat() if event.undertake_date else None,
            acceptance_date=event.acceptance_date.isoformat() if event.acceptance_date else None,
            public_date=event.public_date.isoformat() if event.public_date else None,
            review_status=event.review_status,
            public_page_url=event.public_page_url,
            source_urls=event.get_source_urls(),
            first_seen_at=event.first_seen_at.isoformat() if event.first_seen_at else None,
            last_seen_at=event.last_seen_at.isoformat() if event.last_seen_at else None
        )

        db.close()
        logger.info(f"CDE event detail retrieved: {acceptance_no}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get CDE event detail failed: {e}")
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
        "service": "CDE Events API",
    }


# =====================================================
# 导出
# =====================================================

__all__ = ["router"]
