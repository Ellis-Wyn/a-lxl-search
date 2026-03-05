"""
=====================================================
数据库操作服务层（CRUD）
=====================================================

提供统一的数据库访问接口，封装常用 CRUD 操作：
- Target 相关操作
- Publication 相关操作
- Pipeline 相关操作
- 关联表操作

使用示例：
    from services.database_service import get_db_service

    db = get_db_service()

    # 创建靶点
    target = db.create_target({
        "standard_name": "EGFR",
        "aliases": ["ERBB1"],
        "gene_id": "1956"
    })

    # 查询靶点
    target = db.get_target_by_name("EGFR")
=====================================================
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from utils.database import SessionLocal
from models.target import Target
from models.publication import Publication
from models.pipeline import Pipeline
from models.relationships import TargetPublication, TargetPipeline
from core.logger import get_logger
from core.retry import RetryPolicy

logger = get_logger(__name__)


class DatabaseService:
    """
    数据库操作服务

    提供统一的 CRUD 接口，封装数据库操作细节
    """

    def __init__(self):
        """初始化服务"""
        self._db: Optional[Session] = None

    @property
    def db(self) -> Session:
        """获取数据库会话（延迟创建）"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def close(self):
        """关闭数据库连接"""
        if self._db:
            self._db.close()
            self._db = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    # =====================================================
    # Target 操作
    # =====================================================

    @RetryPolicy.create_retry("DATABASE")
    def create_target(self, data: Dict[str, Any]) -> Target:
        """
        创建靶点（带事务保护和错误处理）

        Args:
            data: 靶点数据
                - standard_name: 标准名称（必填）
                - aliases: 别名列表
                - gene_id: Gene ID
                - uniprot_id: UniProt ID
                - category: 分类
                - description: 描述

        Returns:
            Target 对象

        Raises:
            SQLAlchemyError: 数据库操作失败
        """
        try:
            target = Target(**data)
            self.db.add(target)
            self.db.commit()
            self.db.refresh(target)

            logger.info(f"Created target: {target.standard_name}")
            return target

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create target: {e}")
            raise

    def get_target_by_name(self, standard_name: str) -> Optional[Target]:
        """
        根据标准名称查询靶点

        Args:
            standard_name: 标准名称

        Returns:
            Target 对象或 None
        """
        return self.db.query(Target).filter(
            Target.standard_name == standard_name
        ).first()

    def get_target_by_id(self, target_id: str) -> Optional[Target]:
        """
        根据 ID 查询靶点

        Args:
            target_id: 靶点 UUID

        Returns:
            Target 对象或 None
        """
        return self.db.query(Target).filter(
            Target.target_id == target_id
        ).first()

    def search_targets(self, keyword: str, limit: int = 50) -> List[Target]:
        """
        搜索靶点（支持标准名称和别名）

        Args:
            keyword: 关键词
            limit: 返回数量限制

        Returns:
            Target 列表
        """
        # 搜索标准名称
        from sqlalchemy import func

        query = self.db.query(Target).filter(
            Target.standard_name.ilike(f"%{keyword}%")
        )

        return query.limit(limit).all()

    def get_all_targets(self, limit: int = 100) -> List[Target]:
        """获取所有靶点"""
        return self.db.query(Target).limit(limit).all()

    # =====================================================
    # Publication 操作
    # =====================================================

    @RetryPolicy.create_retry("DATABASE")
    def create_publication(self, data: Dict[str, Any]) -> Publication:
        """
        创建文献（带事务保护和错误处理）

        Args:
            data: 文献数据
                - pmid: PubMed ID（必填）
                - title: 标题（必填）
                - abstract: 摘要
                - pub_date: 发布日期
                - journal: 期刊
                - mesh_terms: MeSH 主题词
                - clinical_data_tags: 临床数据标签

        Returns:
            Publication 对象

        Raises:
            SQLAlchemyError: 数据库操作失败
        """
        try:
            # 检查是否已存在
            existing = self.db.query(Publication).filter(
                Publication.pmid == data["pmid"]
            ).first()

            if existing:
                logger.info(f"Publication {data['pmid']} already exists, updating...")
                for key, value in data.items():
                    setattr(existing, key, value)
                self.db.commit()
                self.db.refresh(existing)
                return existing

            publication = Publication(**data)
            self.db.add(publication)
            self.db.commit()
            self.db.refresh(publication)

            logger.info(f"Created publication: {publication.pmid}")
            return publication

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create publication {data.get('pmid')}: {e}")
            raise

    def get_publication_by_pmid(self, pmid: str) -> Optional[Publication]:
        """根据 PMID 查询文献"""
        return self.db.query(Publication).filter(
            Publication.pmid == pmid
        ).first()

    def get_publications_by_target(
        self,
        target_id: str,
        limit: int = 100,
    ) -> List[Publication]:
        """获取靶点相关文献"""
        publications = self.db.query(Publication).join(
            TargetPublication,
            TargetPublication.pmid == Publication.pmid
        ).filter(
            TargetPublication.target_id == target_id
        ).order_by(
            Publication.pub_date.desc()
        ).limit(limit).all()

        return publications

    # =====================================================
    # Pipeline 操作
    # =====================================================

    @RetryPolicy.create_retry("DATABASE")
    def create_pipeline(self, data: Dict[str, Any]) -> Pipeline:
        """
        创建管线（带事务保护和错误处理）

        Args:
            data: 管线数据
                - drug_code: 药物代码（必填）
                - company_name: 公司名称（必填）
                - indication: 适应症（必填）
                - phase: 阶段（必填）
                - modality: 药物类型
                - source_url: 来源 URL

        Returns:
            Pipeline 对象

        Raises:
            SQLAlchemyError: 数据库操作失败
        """
        try:
            # 检查是否已存在（唯一约束）
            existing = self.db.query(Pipeline).filter(
                and_(
                    Pipeline.drug_code == data["drug_code"],
                    Pipeline.company_name == data["company_name"],
                    Pipeline.indication == data["indication"],
                )
            ).first()

            if existing:
                logger.info(f"Pipeline {data['drug_code']} already exists, updating last_seen_at...")
                existing.last_seen_at = datetime.utcnow()
                # 更新其他字段
                for key, value in data.items():
                    if key != "first_seen_at":  # 不更新首次发现时间
                        setattr(existing, key, value)
                self.db.commit()
                self.db.refresh(existing)
                return existing

            pipeline = Pipeline(**data)
            self.db.add(pipeline)
            self.db.commit()
            self.db.refresh(pipeline)

            logger.info(f"Created pipeline: {pipeline.drug_code}")
            return pipeline

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create pipeline {data.get('drug_code')}: {e}")
            raise

    def get_pipeline_by_id(self, pipeline_id: str) -> Optional[Pipeline]:
        """根据 ID 查询管线"""
        return self.db.query(Pipeline).filter(
            Pipeline.pipeline_id == pipeline_id
        ).first()

    def get_pipelines_by_company(
        self,
        company_name: str,
        limit: int = 100,
    ) -> List[Pipeline]:
        """获取公司管线"""
        return self.db.query(Pipeline).filter(
            Pipeline.company_name == company_name
        ).order_by(
            Pipeline.last_seen_at.desc()
        ).limit(limit).all()

    def get_pipelines_by_target(
        self,
        target_id: str,
        limit: int = 100,
    ) -> List[Pipeline]:
        """获取靶点相关管线"""
        pipelines = self.db.query(Pipeline).join(
            TargetPipeline,
            TargetPipeline.pipeline_id == Pipeline.pipeline_id
        ).filter(
            TargetPipeline.target_id == target_id
        ).order_by(
            Pipeline.last_seen_at.desc()
        ).limit(limit).all()

        return pipelines

    # =====================================================
    # 关联表操作
    # =====================================================

    def link_target_publication(
        self,
        target_id: str,
        pmid: str,
        relation_type: str = "mentions",
        evidence_snippet: Optional[str] = None,
    ) -> TargetPublication:
        """
        关联靶点和文献

        Args:
            target_id: 靶点 ID
            pmid: PubMed ID
            relation_type: 关系类型
            evidence_snippet: 证据片段

        Returns:
            TargetPublication 对象
        """
        # 检查是否已存在
        existing = self.db.query(TargetPublication).filter(
            and_(
                TargetPublication.target_id == target_id,
                TargetPublication.pmid == pmid,
            )
        ).first()

        if existing:
            logger.debug(f"Target-Publication association already exists")
            return existing

        association = TargetPublication(
            target_id=target_id,
            pmid=pmid,
            relation_type=relation_type,
            evidence_snippet=evidence_snippet,
        )

        self.db.add(association)
        self.db.commit()
        self.db.refresh(association)

        logger.info(f"Linked target {target_id} to publication {pmid}")
        return association

    def link_target_pipeline(
        self,
        target_id: str,
        pipeline_id: str,
        relation_type: str = "targets",
        evidence_snippet: Optional[str] = None,
        is_primary: bool = False,
    ) -> TargetPipeline:
        """
        关联靶点和管线

        Args:
            target_id: 靶点 ID
            pipeline_id: 管线 ID
            relation_type: 关系类型
            evidence_snippet: 证据片段
            is_primary: 是否主靶点

        Returns:
            TargetPipeline 对象
        """
        # 检查是否已存在
        existing = self.db.query(TargetPipeline).filter(
            and_(
                TargetPipeline.target_id == target_id,
                TargetPipeline.pipeline_id == pipeline_id,
            )
        ).first()

        if existing:
            logger.debug(f"Target-Pipeline association already exists")
            return existing

        association = TargetPipeline(
            target_id=target_id,
            pipeline_id=pipeline_id,
            relation_type=relation_type,
            evidence_snippet=evidence_snippet,
            is_primary=is_primary,
        )

        self.db.add(association)
        self.db.commit()
        self.db.refresh(association)

        logger.info(f"Linked target {target_id} to pipeline {pipeline_id}")
        return association


# =====================================================
# 单例和工厂函数
# =====================================================

_default_service: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    """
    获取 DatabaseService 单例

    Returns:
        DatabaseService 实例
    """
    global _default_service
    if _default_service is None:
        _default_service = DatabaseService()
    return _default_service


__all__ = [
    "DatabaseService",
    "get_db_service",
]
