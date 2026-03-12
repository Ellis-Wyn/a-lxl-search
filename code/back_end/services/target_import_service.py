"""
============================================================
靶点导入服务 (Target Import Service)
============================================================

提供健壮、可维护的靶点导入功能：
- 支持从YAML配置文件导入靶点
- 幂等性保证：重复运行不会出错
- 事务管理：确保数据一致性
- 完善的日志记录
- 错误处理和恢复机制

使用方式：
    from services.target_import_service import TargetImportService

    service = TargetImportService()
    result = service.import_from_yaml('scripts/data/common_drug_targets.yaml')
    print(f"导入完成：{result.created}个新靶点，{result.skipped}个已存在")

作者：Claude AI
创建时间：2026-03-07
版本：1.0.0
============================================================
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import uuid
from sqlalchemy.orm import Session

from utils.database import SessionLocal
from models.target import Target
from core.logger import setup_logger, get_logger

# 初始化日志
setup_logger(app_name="target_import", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


@dataclass
class TargetData:
    """
    靶点数据类

    用于存储从YAML文件读取的靶点信息
    """
    standard_name: str
    aliases: List[str] = field(default_factory=list)
    category: str = ""
    description: str = ""
    gene_id: Optional[str] = None

    def __post_init__(self):
        """数据验证和清洗"""
        # 标准化名称
        self.standard_name = self.standard_name.strip()
        # 确保别名不重复且不包含标准名
        self.aliases = list(set([a.strip() for a in self.aliases if a.strip() and a.strip() != self.standard_name]))
        # 标准化类别
        if not self.category:
            self.category = "未知"
        # 标准化描述
        if not self.description:
            self.description = f"{self.standard_name} - {self.category}"


@dataclass
class ImportResult:
    """
    导入结果数据类

    用于记录导入操作的统计信息
    """
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        """格式化输出结果"""
        return (
            f"导入完成：\n"
            f"  总数: {self.total}\n"
            f"  新创建: {self.created}\n"
            f"  已更新: {self.updated}\n"
            f"  已跳过: {self.skipped}\n"
            f"  失败: {self.failed}"
        )


class TargetImportService:
    """
    靶点导入服务类

    负责从各种数据源导入靶点信息到数据库

    核心功能：
    - 从YAML文件导入
    - 幂等性检查
    - 事务管理
    - 批量操作优化
    """

    def __init__(self, db: Optional[Session] = None):
        """
        初始化服务

        Args:
            db: 数据库会话，如果为None则创建新会话
        """
        self.db = db or SessionLocal()
        self._external_db = db is not None  # 标记是否外部传入的会话

        # 统计信息
        self._existing_targets: Set[str] = set()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if not self._external_db:
            self.db.close()

    def _load_existing_targets(self) -> None:
        """
        加载已存在的靶点列表

        用于幂等性检查，避免重复创建
        """
        try:
            targets = self.db.query(Target.standard_name).all()
            self._existing_targets = set([t[0] for t in targets])
            logger.info(f"加载已存在靶点列表：{len(self._existing_targets)}个")
        except Exception as e:
            logger.error(f"加载已存在靶点列表失败：{e}")
            self._existing_targets = set()

    def _target_exists(self, standard_name: str) -> bool:
        """
        检查靶点是否已存在

        Args:
            standard_name: 标准名称

        Returns:
            True如果已存在，否则False
        """
        # 首先检查缓存
        if standard_name in self._existing_targets:
            return True

        # 检查别名匹配
        try:
            target = self.db.query(Target).filter(
                Target.aliases.contains([standard_name])
            ).first()
            if target:
                # 更新缓存
                self._existing_targets.add(target.standard_name)
                return True
        except Exception as e:
            logger.warning(f"检查别名失败：{e}")

        return False

    def _create_target(self, data: TargetData) -> Optional[Target]:
        """
        创建单个靶点

        Args:
            data: 靶点数据

        Returns:
            创建的Target对象，失败返回None
        """
        try:
            target = Target(
                target_id=uuid.uuid4(),
                standard_name=data.standard_name,
                aliases=data.aliases,
                gene_id=data.gene_id,
                uniprot_id=None,
                category=data.category,
                description=data.description
            )

            self.db.add(target)
            self.db.flush()  # 获取ID但不提交

            logger.info(f"✓ 创建靶点：{data.standard_name}")
            return target

        except Exception as e:
            logger.error(f"✗ 创建靶点失败 {data.standard_name}：{e}")
            self.db.rollback()
            return None

    def import_from_dict(self, targets_dict: Dict, category: str) -> ImportResult:
        """
        从字典导入靶点

        Args:
            targets_dict: 靶点字典（从YAML解析）
            category: 类别名

        Returns:
            ImportResult对象
        """
        result = ImportResult()
        self._load_existing_targets()

        if not targets_dict or not isinstance(targets_dict, list):
            logger.warning(f"跳过空类别：{category}")
            return result

        logger.info(f"开始处理类别：{category}（{len(targets_dict)}个靶点）")

        for item in targets_dict:
            result.total += 1

            try:
                # 解析数据
                data = TargetData(**item)

                # 幂等性检查
                if self._target_exists(data.standard_name):
                    logger.info(f"⊝ 跳过已存在：{data.standard_name}")
                    result.skipped += 1
                    continue

                # 创建靶点
                target = self._create_target(data)
                if target:
                    result.created += 1
                    # 更新缓存
                    self._existing_targets.add(data.standard_name)
                else:
                    result.failed += 1
                    result.errors.append(f"创建失败：{data.standard_name}")

            except Exception as e:
                logger.error(f"✗ 处理失败：{e}")
                result.failed += 1
                result.errors.append(str(e))
                continue

        return result

    def import_from_yaml(self, yaml_path: str) -> ImportResult:
        """
        从YAML文件导入靶点

        Args:
            yaml_path: YAML文件路径

        Returns:
            ImportResult对象
        """
        logger.info("=" * 60)
        logger.info(f"开始导入靶点：{yaml_path}")
        logger.info("=" * 60)

        # 读取YAML文件
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"文件不存在：{yaml_path}")
            return ImportResult()
        except yaml.YAMLError as e:
            logger.error(f"YAML解析失败：{e}")
            return ImportResult()

        # 汇总结果
        total_result = ImportResult()

        # 遍历所有类别
        for category_name, targets_list in yaml_data.items():
            if category_name.startswith('#'):
                continue  # 跳过注释

            category_result = self.import_from_dict(targets_list, category_name)
            total_result.total += category_result.total
            total_result.created += category_result.created
            total_result.updated += category_result.updated
            total_result.skipped += category_result.skipped
            total_result.failed += category_result.failed
            total_result.errors.extend(category_result.errors)

        # 提交事务
        try:
            if not self._external_db:
                self.db.commit()
            logger.info("=" * 60)
            logger.info("✓ 所有更改已提交到数据库")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"✗ 提交失败：{e}")
            if not self._external_db:
                self.db.rollback()
            total_result.failed = total_result.total  # 标记全部失败

        return total_result

    def get_import_summary(self) -> Dict:
        """
        获取导入摘要信息

        Returns:
            包含靶点统计的字典
        """
        try:
            total_targets = self.db.query(Target).count()

            # 按类别统计
            category_counts = {}
            targets = self.db.query(Target.category, Target.standard_name).all()
            for category, name in targets:
                if category not in category_counts:
                    category_counts[category] = []
                category_counts[category].append(name)

            return {
                "total_targets": total_targets,
                "by_category": {k: len(v) for k, v in category_counts.items()},
                "categories": category_counts
            }
        except Exception as e:
            logger.error(f"获取摘要失败：{e}")
            return {}


# ============================================================
# 便捷函数
# ============================================================

def import_targets_from_yaml(yaml_path: str) -> ImportResult:
    """
    从YAML文件导入靶点的便捷函数

    Args:
        yaml_path: YAML文件路径

    Returns:
        ImportResult对象

    Example:
        >>> result = import_targets_from_yaml('scripts/data/common_drug_targets.yaml')
        >>> print(result)
    """
    with TargetImportService() as service:
        return service.import_from_yaml(yaml_path)


if __name__ == "__main__":
    """
    测试代码
    """
    import sys

    if len(sys.argv) > 1:
        yaml_file = sys.argv[1]
    else:
        yaml_file = "scripts/data/common_drug_targets.yaml"

    result = import_targets_from_yaml(yaml_file)
    print("\n" + "=" * 60)
    print(result)
    print("=" * 60)
