"""
=====================================================
Pipeline 业务服务层
=====================================================

功能：
- 管线数据 CRUD 操作
- 批量更新管线信息
- Phase Jump 预警处理
- Target-Pipeline 关联管理

使用示例：
    service = PipelineService()

    # 创建管线
    pipeline = await service.create_pipeline({
        "drug_code": "SHR-1210",
        "company_name": "恒瑞医药",
        "indication": "NSCLC",
        "phase": "Phase 3",
        "source_url": "..."
    })

    # 更新并检测变化
    report = await service.update_and_detect(
        company_name="恒瑞医药",
        new_pipelines=[...]
    )
=====================================================
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from services.phase_mapper import PhaseMapper, get_phase_mapper
from services.pipeline_monitor import PipelineMonitor, get_pipeline_monitor, ChangeReport
from core.logger import get_logger
from utils.database import SessionLocal
from models.pipeline import Pipeline

# 集成新工具模块
from utils.moa_recognizer import detect_moa
from utils.clinical_metrics_extractor import extract_clinical_metrics
from utils.pipeline_monitor import PipelineMonitor as NewPipelineMonitor

logger = get_logger(__name__)


@dataclass
class PipelineStats:
    """管线统计"""
    total_pipelines: int
    by_company: Dict[str, int]
    by_phase: Dict[str, int]
    by_target: Dict[str, int]
    phase_jump_count_30d: int  # 30天内 Phase Jump 数量


class PipelineService:
    """
    Pipeline 业务服务

    核心功能：
    1. create_pipeline(): 创建管线
    2. update_pipeline(): 更新管线
    3. get_pipelines_by_target(): 获取靶点相关管线
    4. update_and_detect(): 批量更新并检测变化
    5. get_statistics(): 获取统计信息
    """

    def __init__(
        self,
        phase_mapper: Optional[PhaseMapper] = None,
        monitor: Optional[PipelineMonitor] = None,
    ):
        """
        初始化服务

        Args:
            phase_mapper: Phase 映射器
            monitor: 变化检测器
        """
        self.phase_mapper = phase_mapper or get_phase_mapper()
        self.monitor = monitor or get_pipeline_monitor()

        logger.info("PipelineService initialized")

    async def create_pipeline(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        创建管线（集成MoA识别和临床数据提取）

        Args:
            data: 管线数据
                - drug_code: 药物代码
                - company_name: 公司名称
                - indication: 适应症
                - phase: 阶段
                - modality: 药物类型（小分子/ADC 等）- 可选，系统会自动识别
                - source_url: 来源 URL
                - targets: 关联靶点列表（可选）
                - description: 描述信息（可选）

        Returns:
            创建的管线数据（包含 moa_info 和 clinical_data）

        注意：当前版本仅处理数据，数据库操作待实现
        """
        # 标准化 Phase
        raw_phase = data.get("phase", "")
        normalized_phase = self.phase_mapper.normalize(raw_phase)

        # 1. 识别作用机制（MoA）
        moa_info = None
        try:
            # 组合文本以提高识别准确率
            text_for_moa = (
                data.get("indication", "") + " " +
                data.get("description", "")
            ).strip()

            moa_result = detect_moa(
                text=text_for_moa,
                title=data.get("drug_code", "")
            )

            moa_info = {
                "modality": moa_result.modality,
                "category": moa_result.category,
                "confidence": moa_result.confidence,
                "keywords_matched": moa_result.keywords_matched,
                "aliases": moa_result.aliases,
            }

            logger.info(
                f"MoA detected for {data.get('drug_code')}: {moa_result.modality} "
                f"(confidence: {moa_result.confidence})"
            )

        except Exception as e:
            logger.warning(f"MoA detection failed for {data.get('drug_code')}: {e}")
            moa_info = None

        # 2. 提取临床数据
        clinical_data = None
        try:
            text_for_clinical = (
                data.get("indication", "") + " " +
                data.get("description", "")
            ).strip()

            clinical_metrics = extract_clinical_metrics(text_for_clinical)
            clinical_data = clinical_metrics.to_dict()

            # 如果有临床指标，记录日志
            if clinical_metrics.has_any_metric():
                logger.info(
                    f"Clinical metrics extracted for {data.get('drug_code')}: "
                    f"ORR={clinical_metrics.orr}, PFS={clinical_metrics.pfs}, "
                    f"OS={clinical_metrics.os_val}"
                )

        except Exception as e:
            logger.warning(f"Clinical data extraction failed for {data.get('drug_code')}: {e}")
            clinical_data = None

        # 添加时间戳
        now = datetime.utcnow()

        pipeline = {
            **data,
            "phase_normalized": normalized_phase,
            "phase_raw": raw_phase,
            "first_seen_at": now,
            "last_seen_at": now,
            # 添加MoA信息（如果没有提供modality，使用识别的）
            "modality": data.get("modality") or (moa_info["modality"] if moa_info else None),
            "modality_confidence": moa_info["confidence"] if moa_info else None,
            "moa_info": moa_info,
            # 添加临床数据
            "clinical_data": clinical_data,
        }

        # TODO: 数据库插入操作
        logger.info(
            "Pipeline created (pending database)",
            extra={
                "drug_code": data.get("drug_code"),
                "company": data.get("company_name"),
                "phase": normalized_phase,
                "modality": pipeline.get("modality"),
            }
        )

        return pipeline

    async def update_pipeline(
        self,
        pipeline_id: int,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        更新管线

        Args:
            pipeline_id: 管线 ID
            data: 更新数据

        Returns:
            更新后的管线数据

        注意：当前版本仅处理数据，数据库操作待实现
        """
        # 标准化 Phase
        if "phase" in data:
            raw_phase = data["phase"]
            normalized_phase = self.phase_mapper.normalize(raw_phase)
            data["phase_normalized"] = normalized_phase
            data["phase_raw"] = raw_phase

        # 更新时间戳
        data["last_seen_at"] = datetime.utcnow()

        # TODO: 数据库更新操作
        logger.info(
            "Pipeline updated (pending database)",
            extra={
                "pipeline_id": pipeline_id,
                "phase": data.get("phase_normalized"),
            }
        )

        return data

    async def get_pipelines_by_target(
        self,
        target_id: int,
        phase_filter: Optional[str] = None,
        company_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取靶点相关管线（已实现数据库查询）

        Args:
            target_id: 靶点 ID
            phase_filter: 阶段过滤（如 "Phase 3"）
            company_filter: 公司过滤
            limit: 返回数量限制

        Returns:
            管线列表
        """
        db: Session = SessionLocal()
        try:
            # TODO: 需要实现Target-Pipeline关联表后才能真正按target_id查询
            # 当前先返回所有管线，后续添加关联逻辑
            query = db.query(Pipeline)

            # 公司筛选
            if company_filter:
                query = query.filter(Pipeline.company_name == company_filter)

            # 阶段筛选
            if phase_filter:
                query = query.filter(
                    or_(
                        Pipeline.phase == phase_filter,
                        Pipeline.phase_raw.contains(phase_filter)
                    )
                )

            # 执行查询
            pipelines = query.limit(limit).all()

            # 转换为字典
            results = []
            for p in pipelines:
                results.append({
                    "pipeline_id": str(p.pipeline_id),
                    "drug_code": p.drug_code,
                    "company_name": p.company_name,
                    "indication": p.indication,
                    "phase": p.phase,
                    "phase_raw": p.phase_raw,
                    "phase_normalized": p.phase,
                    "modality": p.modality,
                    "source_url": p.source_url,
                    "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
                    "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
                })

            logger.info(
                f"Query pipelines by target: {len(results)} results",
                extra={
                    "target_id": target_id,
                    "phase_filter": phase_filter,
                    "company_filter": company_filter,
                }
            )

            return results

        except Exception as e:
            logger.error(f"Query pipelines by target failed: {e}")
            return []
        finally:
            db.close()

    async def get_pipelines_by_company(
        self,
        company_name: str,
        target_filter: Optional[str] = None,
        phase_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取公司管线（已实现数据库查询，集成公司名称映射）

        Args:
            company_name: 公司名称（支持简称、英文、别名）
            target_filter: 靶点过滤
            phase_filter: 阶段过滤
            limit: 返回数量限制

        Returns:
            管线列表
        """
        from utils.company_name_mapper import get_company_mapper

        db: Session = SessionLocal()
        try:
            # 标准化公司名称
            mapper = get_company_mapper()
            standardized_name = mapper.normalize(company_name)

            if standardized_name:
                # 使用标准化后的公司名称
                query = db.query(Pipeline).filter(Pipeline.company_name == standardized_name)
                logger.info(f"Company name '{company_name}' normalized to: {standardized_name}")
            else:
                # 未找到映射，尝试模糊匹配
                fuzzy_match = mapper.find_match(company_name)
                if fuzzy_match:
                    query = db.query(Pipeline).filter(Pipeline.company_name == fuzzy_match)
                    logger.info(f"Company name '{company_name}' fuzzy matched to: {fuzzy_match}")
                else:
                    # 使用原始名称
                    query = db.query(Pipeline).filter(Pipeline.company_name == company_name)
                    logger.warning(f"Company name '{company_name}' not found in mapper, using original")

            # 阶段筛选
            if phase_filter:
                query = query.filter(
                    or_(
                        Pipeline.phase == phase_filter,
                        Pipeline.phase_raw.contains(phase_filter)
                    )
                )

            # 执行查询
            pipelines = query.limit(limit).all()

            # 转换为字典
            results = []
            for p in pipelines:
                results.append({
                    "pipeline_id": str(p.pipeline_id),
                    "drug_code": p.drug_code,
                    "company_name": p.company_name,
                    "indication": p.indication,
                    "phase": p.phase,
                    "phase_raw": p.phase_raw,
                    "phase_normalized": p.phase,
                    "modality": p.modality,
                    "source_url": p.source_url,
                    "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
                    "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
                })

            logger.info(
                f"Query pipelines by company: {len(results)} results",
                extra={
                    "company_name": company_name,
                    "phase_filter": phase_filter,
                }
            )

            return results

        except Exception as e:
            logger.error(f"Query pipelines by company failed: {e}")
            return []
        finally:
            db.close()

    async def update_and_detect(
        self,
        company_name: str,
        new_pipelines: List[Dict[str, Any]],
        disappeared_threshold_days: int = 180,
    ) -> ChangeReport:
        """
        批量更新公司管线并检测变化

        Args:
            company_name: 公司名称
            new_pipelines: 新管线数据（爬虫获取）
            disappeared_threshold_days: 消失判定阈值

        Returns:
            变化报告

        注意：当前版本仅做模拟检测，数据库操作待实现
        """
        logger.info(
            f"Updating pipelines for {company_name}",
            extra={
                "company_name": company_name,
                "new_pipelines_count": len(new_pipelines),
            }
        )

        # 获取旧管线数据
        old_pipelines = await self.get_pipelines_by_company(company_name)

        # 标准化新管线数据
        normalized_new = []
        for pipeline in new_pipelines:
            raw_phase = pipeline.get("phase", "")
            normalized_phase = self.phase_mapper.normalize(raw_phase)

            normalized_new.append({
                **pipeline,
                "phase_normalized": normalized_phase,
                "phase_raw": raw_phase,
            })

        # 检测变化
        report = self.monitor.detect_changes(
            old_pipelines=old_pipelines,
            new_pipelines=normalized_new,
            disappeared_threshold_days=disappeared_threshold_days,
        )

        # 处理变化
        await self._process_changes(company_name, report)

        return report

    async def _process_changes(
        self,
        company_name: str,
        report: ChangeReport,
    ) -> None:
        """
        处理变化报告

        Args:
            company_name: 公司名称
            report: 变化报告
        """
        # 处理新增管线
        for pipeline in report.new_pipelines:
            await self.create_pipeline(pipeline)

        # 处理 Phase Jump
        for jump in report.phase_jumps:
            logger.warning(
                "Phase Jump detected!",
                extra={
                    "company": company_name,
                    "drug": jump.drug_code,
                    "old_phase": jump.old_phase,
                    "new_phase": jump.new_phase,
                }
            )
            # TODO: 发送预警通知

        # 处理消失管线
        for pipeline in report.disappeared_pipelines:
            logger.warning(
                "Pipeline disappeared!",
                extra={
                    "company": company_name,
                    "drug": pipeline.get("drug_code"),
                }
            )
            # TODO: 标记为已终止

    async def link_target_pipeline(
        self,
        target_id: int,
        pipeline_id: int,
        relation_type: str = "targets",
        evidence_snippet: Optional[str] = None,
    ) -> None:
        """
        关联靶点和管线

        Args:
            target_id: 靶点 ID
            pipeline_id: 管线 ID
            relation_type: 关系类型（targets/inhibits/antibody_to）
            evidence_snippet: 证据片段

        注意：当前版本仅记录日志，数据库操作待实现
        """
        logger.info(
            "Link Target-Pipeline (pending database)",
            extra={
                "target_id": target_id,
                "pipeline_id": pipeline_id,
                "relation_type": relation_type,
            }
        )

    async def get_statistics(
        self,
        company_name: Optional[str] = None,
        target_id: Optional[int] = None,
    ) -> PipelineStats:
        """
        获取管线统计信息

        Args:
            company_name: 公司过滤
            target_id: 靶点过滤

        Returns:
            统计信息

        注意：当前版本返回模拟数据，数据库操作待实现
        """
        # TODO: 数据库统计查询
        logger.info(
            "Get pipeline statistics (pending database)",
            extra={
                "company_name": company_name,
                "target_id": target_id,
            }
        )

        return PipelineStats(
            total_pipelines=0,
            by_company={},
            by_phase={},
            by_target={},
            phase_jump_count_30d=0,
        )

    async def search_pipelines(
        self,
        keyword: Optional[str] = None,
        target_name: Optional[str] = None,
        company_name: Optional[str] = None,
        phase: Optional[str] = None,
        moa_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        搜索管线（已实现数据库查询，集成公司名称映射）

        Args:
            keyword: 关键词（搜索 drug_code、indication、company_name）
            target_name: 靶点名称
            company_name: 公司名称（支持简称、英文、别名）
            phase: 阶段
            moa_type: MoA类型
            limit: 返回数量限制

        Returns:
            管线列表
        """
        from utils.company_name_mapper import get_company_mapper

        db: Session = SessionLocal()
        try:
            # 构建查询
            query = db.query(Pipeline)

            # 关键词搜索
            if keyword:
                conditions = []
                conditions.append(Pipeline.drug_code.contains(keyword))
                conditions.append(Pipeline.indication.contains(keyword))
                # 添加 modality 搜索（药物类型）
                conditions.append(Pipeline.modality.contains(keyword))

                # 检查keyword是否匹配公司名称
                mapper = get_company_mapper()
                matched_company = mapper.normalize(keyword)
                if matched_company:
                    # 如果匹配到公司，添加公司名称条件
                    conditions.append(Pipeline.company_name == matched_company)
                    logger.info(f"Keyword '{keyword}' matched to company: {matched_company}")
                else:
                    # 尝试模糊匹配
                    fuzzy_match = mapper.find_match(keyword)
                    if fuzzy_match:
                        conditions.append(Pipeline.company_name == fuzzy_match)
                        logger.info(f"Keyword '{keyword}' fuzzy matched to company: {fuzzy_match}")

                query = query.filter(or_(*conditions))

            # 公司筛选（支持简称、英文、别名）
            if company_name:
                mapper = get_company_mapper()
                standardized_name = mapper.normalize(company_name)

                if standardized_name:
                    # 使用标准化后的公司名称
                    query = query.filter(Pipeline.company_name == standardized_name)
                    logger.info(f"Company name '{company_name}' normalized to: {standardized_name}")
                else:
                    # 未找到映射，尝试模糊匹配
                    fuzzy_match = mapper.find_match(company_name)
                    if fuzzy_match:
                        query = query.filter(Pipeline.company_name == fuzzy_match)
                        logger.info(f"Company name '{company_name}' fuzzy matched to: {fuzzy_match}")
                    else:
                        # 使用原始名称（可能是用户已经输入了全称）
                        query = query.filter(Pipeline.company_name == company_name)
                        logger.warning(f"Company name '{company_name}' not found in mapper, using original")

            # 阶段筛选
            if phase:
                # 支持标准化阶段或原始阶段
                query = query.filter(
                    or_(
                        Pipeline.phase == phase,
                        Pipeline.phase_raw.contains(phase)
                    )
                )

            # MoA类型筛选
            if moa_type:
                query = query.filter(Pipeline.modality == moa_type)

            # 执行查询
            pipelines = query.limit(limit).all()

            # 转换为字典
            results = []
            for p in pipelines:
                results.append({
                    "pipeline_id": str(p.pipeline_id),
                    "drug_code": p.drug_code,
                    "company_name": p.company_name,
                    "indication": p.indication,
                    "phase": p.phase,
                    "phase_raw": p.phase_raw,
                    "phase_normalized": p.phase,
                    "modality": p.modality,
                    "source_url": p.source_url,
                    "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
                    "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
                })

            logger.info(
                f"Pipeline search completed: {len(results)} results",
                extra={
                    "keyword": keyword,
                    "company_name": company_name,
                    "phase": phase,
                    "moa_type": moa_type,
                    "results_count": len(results)
                }
            )

            return results

        except Exception as e:
            logger.error(f"Pipeline search failed: {e}")
            return []
        finally:
            db.close()


# 单例实例
_default_service: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    """
    获取 PipelineService 单例

    Returns:
        PipelineService 实例
    """
    global _default_service
    if _default_service is None:
        _default_service = PipelineService()
    return _default_service


__all__ = [
    "PipelineService",
    "PipelineStats",
    "get_pipeline_service",
]
