"""
=====================================================
Target ORM 模型（靶点表）
=====================================================

核心主表：以靶点为信息枢纽
- 存储靶点标准名称和别名
- 支持反向查询（别名 → 标准名）
- 关联文献和管线
=====================================================
"""

from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from utils.database import Base


class Target(Base):
    """
    靶点表

    核心设计：
    - standard_name：唯一的标准名称（如 EGFR）
    - aliases：JSON数组存储别名（如 ["ERBB1", "HER1"]）
    - 支持通过别名反向查找（GIN索引）
    """

    __tablename__ = "target"

    # =====================================================
    # 主键
    # =====================================================
    target_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # =====================================================
    # 基本信息
    # =====================================================
    standard_name = Column(String(100), unique=True, nullable=False, index=True, comment="标准名称，如 EGFR")
    aliases = Column(JSONB, default=list, comment="别名数组，如 ['ERBB1', 'HER1']")

    # =====================================================
    # 外部标识
    # =====================================================
    gene_id = Column(String(50), index=True, comment="NCBI Gene ID")
    uniprot_id = Column(String(50), index=True, comment="UniProt ID")

    # =====================================================
    # 元数据（V1扩展）
    # =====================================================
    category = Column(String(100), comment="靶点分类：激酶/GPCR/离子通道等")
    description = Column(Text, comment="靶点描述")

    # =====================================================
    # 并发控制（乐观锁）
    # =====================================================
    version = Column(
        Integer,
        nullable=False,
        default=1,
        comment="乐观锁版本号，每次更新自动递增"
    )

    # =====================================================
    # 时间戳
    # =====================================================
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # =====================================================
    # 软删除（P2优化）
    # =====================================================
    deleted_at = Column(
        DateTime,
        nullable=True,
        index=True,
        comment="软删除时间（NULL=未删除，非NULL=已删除）"
    )

    # =====================================================
    # 关系（ORM 关联）
    # =====================================================
    # 反向关系：一个靶点可以关联多篇文献
    publications = relationship(
        "TargetPublication",
        back_populates="target",
        cascade="all, delete-orphan"
    )

    # 反向关系：一个靶点可以关联多个管线
    pipelines = relationship(
        "TargetPipeline",
        back_populates="target",
        cascade="all, delete-orphan"
    )

    # =====================================================
    # 实用方法
    # =====================================================

    def has_alias(self, name: str) -> bool:
        """
        检查是否包含某个别名

        参数：
            name: 别名（如 "ERBB1"）

        返回：
            bool: True=包含，False=不包含
        """
        if not self.aliases:
            return False
        return name in self.aliases

    def add_alias(self, name: str) -> None:
        """
        添加别名（去重）

        参数：
            name: 别名
        """
        if not self.aliases:
            self.aliases = []

        if name not in self.aliases:
            self.aliases.append(name)
            self.aliases = list(set(self.aliases))  # 去重

    def get_all_names(self) -> list:
        """
        获取所有名称（标准名 + 别名）

        返回：
            list: [标准名, 别名1, 别名2, ...]
        """
        names = [self.standard_name]
        if self.aliases:
            names.extend(self.aliases)
        return list(set(names))  # 去重

    # =====================================================
    # 软删除方法（P2优化）
    # =====================================================

    def soft_delete(self) -> None:
        """
        软删除：标记为已删除，不真正删除数据

        设置 deleted_at 为当前时间戳
        """
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """
        恢复：清除删除标记

        将 deleted_at 设置为 NULL
        """
        self.deleted_at = None

    def is_deleted(self) -> bool:
        """
        判断是否已删除

        返回：
            bool: True=已删除，False=未删除
        """
        return self.deleted_at is not None

    @classmethod
    def active_only(cls, query):
        """
        筛选仅活跃的（未删除）记录

        参数：
            query: SQLAlchemy Query 对象

        返回：
            Query: 过滤后的查询对象
        """
        return query.filter(cls.deleted_at.is_(None))

    @classmethod
    def deleted_only(cls, query):
        """
        筛选仅已删除的记录

        参数：
            query: SQLAlchemy Query 对象

        返回：
            Query: 过滤后的查询对象
        """
        return query.filter(cls.deleted_at.isnot(None))

    # =====================================================
    # 序列化方法
    # =====================================================

    def to_dict(self, include_relations: bool = False) -> dict:
        """
        转换为字典（用于API返回）

        参数：
            include_relations: 是否包含关联数据

        返回：
            dict: 靶点信息字典
        """
        data = {
            "target_id": str(self.target_id),
            "standard_name": self.standard_name,
            "aliases": self.aliases or [],
            "gene_id": self.gene_id,
            "uniprot_id": self.uniprot_id,
            "category": self.category,
            "description": self.description,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "is_deleted": self.is_deleted(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_relations:
            data["publications_count"] = len(self.publications)
            data["pipelines_count"] = len(self.pipelines)

        return data

    def __repr__(self) -> str:
        return f"<Target({self.standard_name})>"

    def __str__(self) -> str:
        return self.standard_name
