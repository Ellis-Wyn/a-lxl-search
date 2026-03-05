"""
=====================================================
Publication ORM 模型（PubMed文献表）
=====================================================

存储PubMed文献的科学证据与热点
- 支持全文搜索
- 临床数据标签（ORR、PFS等）
- MeSH主题词
=====================================================
"""

from sqlalchemy import Column, String, Text, DateTime, Date, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, date

from utils.database import Base


class Publication(Base):
    """
    PubMed文献表

    核心设计：
    - pmid：PubMed唯一标识（主键）
    - clinical_data_tags：存储临床数据指标（ORR、PFS等）
    - 支持全文搜索（GIN索引）
    """

    __tablename__ = "publication"

    # =====================================================
    # 主键
    # =====================================================
    pmid = Column(String(20), primary_key=True, comment="PubMed唯一标识")

    # =====================================================
    # 基本信息
    # =====================================================
    title = Column(Text, nullable=False, comment="文献标题")
    abstract = Column(Text, comment="摘要全文")
    pub_date = Column(Date, index=True, comment="发布日期")

    # =====================================================
    # MeSH 主题词
    # =====================================================
    mesh_terms = Column(JSONB, default=list, comment="MeSH主题词数组")

    # =====================================================
    # 期刊信息（V1补充）
    # =====================================================
    journal = Column(String(255), index=True, comment="期刊名")
    source_type = Column(String(100), index=True, comment="来源类型：ASCO/AACR/NEJM等")

    # =====================================================
    # 临床数据标签（V1补充）
    # =====================================================
    clinical_data_tags = Column(JSONB, default=list, comment="临床数据指标")
    # 示例: [
    #   {"metric": "ORR", "value": "45.2%"},
    #   {"metric": "PFS", "value": "11.2m"},
    #   {"metric": "n", "value": "120"}
    # ]

    # =====================================================
    # 文献类型
    # =====================================================
    publication_type = Column(String(50), index=True, comment="文献类型：Clinical Trial/Review/Case Report")

    # =====================================================
    # 时间戳
    # =====================================================
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # =====================================================
    # 关系（ORM 关联）
    # =====================================================
    # 反向关系：一篇文献可以关联多个靶点
    targets = relationship(
        "TargetPublication",
        back_populates="publication",
        cascade="all, delete-orphan"
    )

    # =====================================================
    # 实用方法
    # =====================================================

    def has_clinical_data(self) -> bool:
        """
        是否包含临床数据

        返回：
            bool: True=包含临床数据（ORR/PFS等）
        """
        if not self.clinical_data_tags:
            return False
        return len(self.clinical_data_tags) > 0

    def get_clinical_metrics(self) -> dict:
        """
        获取所有临床指标

        返回：
            dict: {指标名: 值}，如 {"ORR": "45.2%", "PFS": "11.2m"}
        """
        if not self.clinical_data_tags:
            return {}

        return {tag["metric"]: tag["value"] for tag in self.clinical_data_tags}

    def get_days_since_publication(self) -> int:
        """
        获取距离发布的天数

        返回：
            int: 天数（如果pub_date为空，返回999999）
        """
        if not self.pub_date:
            return 999999

        delta = date.today() - self.pub_date
        return delta.days

    def calculate_recency_score(self, max_days: int = 730) -> int:
        """
        计算时效性得分

        得分规则：
        - 0-30天：100分
        - 31-90天：80分
        - 91-365天：60分
        - 366-730天（24个月）：40分
        - 超过730天：20分

        参数：
            max_days: 最大天数阈值（默认24个月）

        返回：
            int: 得分（0-100）
        """
        days = self.get_days_since_publication()

        if days <= 30:
            return 100
        elif days <= 90:
            return 80
        elif days <= 365:
            return 60
        elif days <= max_days:
            return 40
        else:
            return 20

    def extract_keywords_from_abstract(self, keywords: list) -> list:
        """
        从摘要中提取关键词

        参数：
            keywords: 关键词列表，如 ["ORR", "PFS", "n=", "p-value"]

        返回：
            list: 找到的关键词
        """
        found = []
        if not self.abstract:
            return found

        abstract_lower = self.abstract.lower()
        for keyword in keywords:
            if keyword.lower() in abstract_lower:
                found.append(keyword)

        return found

    # =====================================================
    # 序列化方法
    # =====================================================

    def to_dict(self, include_relations: bool = False) -> dict:
        """
        转换为字典（用于API返回）

        参数：
            include_relations: 是否包含关联数据

        返回：
            dict: 文献信息字典
        """
        data = {
            "pmid": self.pmid,
            "title": self.title,
            "abstract": self.abstract,
            "pub_date": self.pub_date.isoformat() if self.pub_date else None,
            "journal": self.journal,
            "source_type": self.source_type,
            "mesh_terms": self.mesh_terms or [],
            "clinical_data_tags": self.clinical_data_tags or [],
            "publication_type": self.publication_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # 计算附加字段
        data["days_since_publication"] = self.get_days_since_publication()
        data["recency_score"] = self.calculate_recency_score()
        data["has_clinical_data"] = self.has_clinical_data()

        if include_relations:
            data["targets_count"] = len(self.targets)
            data["targets"] = [
                {
                    "standard_name": tp.target.standard_name,
                    "relation_type": tp.relation_type
                }
                for tp in self.targets
            ]

        return data

    def __repr__(self) -> str:
        return f"<Publication(pmid={self.pmid}, title={self.title[:50]}...)>"

    def __str__(self) -> str:
        return f"PMID: {self.pmid} - {self.title[:80]}"
