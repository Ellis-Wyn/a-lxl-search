"""
为已有管线创建靶点关联（修复版 - 处理编码问题）
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import SessionLocal
from models.pipeline import Pipeline
from models.target import Target
from models.relationships import TargetPipeline
from sqlalchemy import or_
from core.logger import setup_logger, get_logger
import re

# 初始化日志
setup_logger(app_name="link_targets_fixed", log_level="INFO", json_logs=False)
logger = get_logger(__name__)


def extract_targets_from_text(text: str) -> list:
    """
    从文本中提取靶点信息
    """
    if not text:
        return []

    targets = []

    # 常见靶点模式
    target_patterns = [
        r'EGFR', r'HER2', r'HER3', r'HER4', r'VEGF', r'VEGFR1', r'VEGFR2', r'VEGFR3',
        r'FGFR', r'PDGFR', r'C-MET', r'MET', r'RON', r'IGF1R',
        r'PD-?1', r'PD-?L1', r'PD-?L2', r'CTLA-?4', r'LAG-?3', r'TIM-?3',
        r'TIGIT', r'CD47', r'SIRPα',
        r'CD19', r'CD20', r'CD22', r'CD33', r'CD38', r'CD79[bB]', r'CD123',
        r'CD3', r'CD4', r'CD8', r'CD28', r'CD137', r'CD127', r'CD70',
        r'ALK', r'ROS1', r'NTRK', r'BTK', r'JAK', r'SYK', r'BCL-?2',
        r'PI3K', r'AKT', r'mTOR', r'MAPK', r'ERK',
        r'PARP', r'KRAS', r'NRAS', r'HRAS', r'BRAF', r'BRCA',
        r'IDH1', r'IDH2', r'FLT3', r'c-?KIT',
    ]

    # 提取靶点
    for pattern in target_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # 标准化靶点名称
            target = match.upper().replace('-', '').replace(' ', '')

            # 特殊处理
            if target == 'PDL1':
                target = 'PD-L1'
            elif target == 'PDL2':
                target = 'PD-L2'
            elif target == 'PDCD1':
                target = 'PD-1'
            elif target == 'CD79B':
                target = 'CD79b'
            elif target == 'SIRPA':
                target = 'SIRPα'

            # 去重
            if target and target not in targets:
                targets.append(target)

    return targets


def safe_get_indication(pipeline) -> str:
    """
    安全地获取适应症文本，处理编码错误
    """
    try:
        # 尝试直接访问
        indication = pipeline.indication
        if indication:
            # 尝试编码转换
            if isinstance(indication, bytes):
                try:
                    indication = indication.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        indication = indication.decode('gbk')
                    except:
                        indication = indication.decode('utf-8', errors='ignore')
            return indication
        return ""
    except Exception as e:
        logger.warning(f"获取适应症失败 (pipeline_id={pipeline.pipeline_id}): {e}")
        return ""


def main():
    """主函数"""
    logger.info("开始为管线创建靶点关联...")

    db = SessionLocal()
    try:
        # 获取所有管线ID（避免一次性加载所有数据）
        pipeline_ids = db.query(Pipeline.pipeline_id).all()
        logger.info(f"找到 {len(pipeline_ids)} 条管线")

        targets_created = 0
        links_created = 0
        links_skipped = 0
        pipelines_processed = 0
        pipelines_failed = 0

        for pipeline_id_tuple in pipeline_ids:
            pipeline_id = pipeline_id_tuple[0]
            pipelines_processed += 1

            try:
                # 单独查询每个管线（避免编码错误影响其他记录）
                pipeline = db.query(Pipeline).filter(
                    Pipeline.pipeline_id == pipeline_id
                ).first()

                if not pipeline:
                    continue

                # 安全获取适应症
                indication = safe_get_indication(pipeline)

                # 提取靶点
                targets_extracted = extract_targets_from_text(indication)

                if targets_extracted:
                    logger.info(f"管线 {pipeline.drug_code}: 提取到 {len(targets_extracted)} 个靶点 - {targets_extracted}")

                    for target_name in targets_extracted:
                        try:
                            # 查找或创建靶点
                            target = db.query(Target).filter(
                                or_(
                                    Target.standard_name == target_name,
                                    Target.aliases.contains([target_name])
                                )
                            ).first()

                            if not target:
                                # 创建新靶点
                                target = Target(
                                    standard_name=target_name,
                                    aliases=[],
                                    category="未知",
                                    description=f"自动创建于管线关联脚本: {pipeline.drug_code}"
                                )
                                db.add(target)
                                db.commit()
                                db.refresh(target)
                                targets_created += 1
                                logger.info(f"  ✓ 创建新靶点: {target_name}")

                            # 检查是否已存在关联
                            existing_link = db.query(TargetPipeline).filter(
                                TargetPipeline.target_id == target.target_id,
                                TargetPipeline.pipeline_id == pipeline.pipeline_id
                            ).first()

                            if not existing_link:
                                # 创建管线-靶点关联
                                link = TargetPipeline(
                                    target_id=target.target_id,
                                    pipeline_id=pipeline.pipeline_id,
                                    relation_type="targets",
                                    evidence_snippet=f"从适应症提取: {pipeline.drug_code}"
                                )
                                db.add(link)
                                db.commit()
                                links_created += 1
                                logger.info(f"  ✓ 关联 {pipeline.drug_code} -> {target_name}")
                            else:
                                links_skipped += 1

                        except Exception as e:
                            logger.error(f"  ✗ 关联失败 {target_name}: {e}")
                            db.rollback()

                # 每处理10个管线输出一次进度
                if pipelines_processed % 10 == 0:
                    logger.info(f"进度: {pipelines_processed}/{len(pipeline_ids)} 条管线已处理")

            except Exception as e:
                logger.error(f"处理管线 {pipeline_id} 失败: {e}")
                pipelines_failed += 1
                db.rollback()
                continue

        logger.info("=" * 60)
        logger.info("完成统计:")
        logger.info(f"  处理管线: {pipelines_processed}/{len(pipeline_ids)}")
        logger.info(f"  失败管线: {pipelines_failed}")
        logger.info(f"  创建靶点: {targets_created}")
        logger.info(f"  创建关联: {links_created}")
        logger.info(f"  跳过已存在: {links_skipped}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"执行失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
