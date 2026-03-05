"""
=====================================================
Pipeline ORM 模型（管线表）
=====================================================

产业界研发活动的快照层+时序监控层
- 支持增量监控（first_seen_at, last_seen_at）
- 检测Phase Jump（阶段跳变）
- 竞品退场预警
=====================================================
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from utils.database import Base


class Pipeline(Base):
    """
    管线表

    核心设计：
    - 最小粒度：(drug_code, company_name, indication) 唯一
    - 双时间戳：first_seen_at（首次发现）+ last_seen_at（最近更新）
    - 支持检测Phase Jump和竞品退场
    """

    __tablename__ = "pipeline"

    # =====================================================
    # 主键
    # =====================================================
    pipeline_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # =====================================================
    # 药物信息
    # =====================================================
    drug_code = Column(String(255), nullable=False, index=True, comment="药物代号/名称")
    company_name = Column(String(255), nullable=False, index=True, comment="公司名")
    indication = Column(Text, nullable=False, comment="适应症")

    # =====================================================
    # 研发阶段
    # =====================================================
    phase = Column(String(50), nullable=False, index=True, comment="研发阶段：preclinical/I/II/III/filing/approved")
    phase_raw = Column(String(255), comment="官网原始阶段名称（便于调试）")

    # =====================================================
    # 药物类型（V1补充）
    # =====================================================
    modality = Column(String(100), index=True, comment="药物类型：Small Molecule/Antibody/ADC/PROTAC/CAR-T")

    # =====================================================
    # 来源（必填）
    # =====================================================
    source_url = Column(Text, nullable=False, comment="原始来源URL")

    # =====================================================
    # 增量监控（双时间戳）
    # =====================================================
    first_seen_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="首次发现时间（永不变化）"
    )
    last_seen_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        onupdate=datetime.utcnow,
        comment="最近更新时间（每次爬取更新）"
    )

    # =====================================================
    # 状态
    # =====================================================
    status = Column(
        String(50),
        default="active",
        index=True,
        comment="状态：active/discontinued"
    )
    discontinued_at = Column(
        DateTime,
        nullable=True,
        comment="终止时间（当status=discontinued时记录）"
    )

    # =====================================================
    # 联合用药
    # =====================================================
    is_combination = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="是否为联合用药"
    )
    combination_drugs = Column(
        Text,
        nullable=True,
        comment="联合用药列表(JSON格式): [\"HRS-1234\", \"HRS-5678\"]"
    )

    # =====================================================
    # 时间戳
    # =====================================================
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # =====================================================
    # 关系（ORM 关联）
    # =====================================================
    # 反向关系：一个管线可以针对多个靶点（双抗、多靶点药物）
    targets = relationship(
        "TargetPipeline",
        back_populates="pipeline",
        cascade="all, delete-orphan"
    )

    # =====================================================
    # 实用方法
    # =====================================================

    def has_phase_changed(self) -> bool:
        """
        是否发生过Phase变化

        通过对比 first_seen_at 和 last_seen_at 是否不同
        （实际需要历史记录，这里简化处理）

        返回：
            bool: True=有变化，False=无变化
        """
        # 简化版本：如果两个时间戳相差超过1天，认为可能有变化
        # 实际应该通过 Pipeline_Event_Log 表判断
        delta = self.last_seen_at - self.first_seen_at
        return delta.days >= 1

    def get_days_since_first_seen(self) -> int:
        """
        获取距离首次发现的天数

        返回：
            int: 天数
        """
        delta = datetime.utcnow() - self.first_seen_at
        return delta.days

    def get_days_since_last_seen(self) -> int:
        """
        获取距离最近更新的天数

        返回：
            int: 天数（用于判断是否"消失"）
        """
        delta = datetime.utcnow() - self.last_seen_at
        return delta.days

    def is_disappeared(self, threshold_days: int = 21) -> bool:
        """
        判断是否已消失（竞品退场）

        默认：连续21天（3周）未抓取到

        参数：
            threshold_days: 阈值天数

        返回：
            bool: True=已消失，False=正常
        """
        days = self.get_days_since_last_seen()
        return days >= threshold_days

    def get_phase_order(self) -> int:
        """
        获取阶段的排序值（用于排序和比较）

        返回：
            int: 阶段排序（数字越大越后期）
        """
        phase_mapping = {
            "preclinical": 1,
            "I": 2,
            "II": 3,
            "III": 4,
            "filing": 5,
            "approved": 6
        }

        # 标准化phase名称
        phase_normalized = self.phase.lower().replace("phase ", "").strip()

        return phase_mapping.get(phase_normalized, 0)

    def is_later_phase_than(self, other_pipeline) -> bool:
        """
        判断是否比另一个管线阶段更靠后

        参数：
            other_pipeline: 另一个Pipeline对象

        返回：
            bool: True=当前阶段更靠后
        """
        return self.get_phase_order() > other_pipeline.get_phase_order()

    # =====================================================
    # 序列化方法
    # =====================================================

    def to_dict(self, include_relations: bool = False) -> dict:
        """
        转换为字典（用于API返回）

        参数：
            include_relations: 是否包含关联数据

        返回：
            dict: 管线信息字典
        """
        data = {
            "pipeline_id": str(self.pipeline_id),
            "drug_code": self.drug_code,
            "company_name": self.company_name,
            "indication": self.indication,
            "phase": self.phase,
            "phase_raw": self.phase_raw,
            "modality": self.modality,
            "source_url": self.source_url,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "status": self.status,
            "discontinued_at": self.discontinued_at.isoformat() if self.discontinued_at else None,
            "is_combination": self.is_combination,
            "combination_drugs": self.combination_drugs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # 计算附加字段
        data["days_since_first_seen"] = self.get_days_since_first_seen()
        data["days_since_last_seen"] = self.get_days_since_last_seen()
        data["is_disappeared"] = self.is_disappeared()
        data["phase_order"] = self.get_phase_order()

        if include_relations:
            data["targets_count"] = len(self.targets)
            data["targets"] = [
                {
                    "standard_name": tp.target.standard_name,
                    "relation_type": tp.relation_type,
                    "is_primary": tp.is_primary
                }
                for tp in self.targets
            ]

        return data

    def __repr__(self) -> str:
        return f"<Pipeline({self.drug_code} by {self.company_name}, Phase {self.phase})>"

    def __str__(self) -> str:
        return f"{self.company_name} - {self.drug_code} - Phase {self.phase}"
