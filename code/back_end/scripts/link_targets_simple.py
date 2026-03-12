"""
为已有管线创建靶点关联（简化版 - 使用原始SQL查询）
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor
from core.logger import setup_logger, get_logger
import re
import uuid

# 初始化日志
setup_logger(app_name="link_targets_simple", log_level="INFO", json_logs=False)
logger = get_logger(__name__)

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'drug_intelligence_db',
    'user': 'postgres',
    'password': 'yang051028',
    'client_encoding': 'GBK'  # 使用GBK编码
}


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


def main():
    """主函数"""
    logger.info("开始为管线创建靶点关联...")

    conn = None
    try:
        # 连接数据库
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 获取所有管线
        cursor.execute("SELECT pipeline_id, drug_code, indication FROM pipeline")
        pipelines = cursor.fetchall()
        logger.info(f"找到 {len(pipelines)} 条管线")

        targets_created = 0
        links_created = 0
        pipelines_skipped = 0

        # 存储要创建的靶点和关联
        targets_to_create = {}  # target_name -> (drug_code, list of pipeline_ids)
        links_to_create = []  # (target_name, pipeline_id, drug_code)

        for pipeline in pipelines:
            pipeline_id = pipeline['pipeline_id']
            drug_code = pipeline['drug_code']
            indication = pipeline['indication']

            if not indication:
                continue

            # 提取靶点
            targets_extracted = extract_targets_from_text(indication)

            if targets_extracted:
                logger.info(f"管线 {drug_code}: 提取到 {len(targets_extracted)} 个靶点 - {targets_extracted}")

                for target_name in targets_extracted:
                    # 检查靶点是否存在
                    cursor.execute(
                        "SELECT target_id FROM target WHERE standard_name = %s",
                        (target_name,)
                    )
                    result = cursor.fetchone()

                    if result:
                        target_id = result['target_id']

                        # 检查关联是否存在
                        cursor.execute(
                            """SELECT 1 FROM target_pipeline
                               WHERE target_id = %s AND pipeline_id = %s""",
                            (target_id, pipeline_id)
                        )
                        if not cursor.fetchone():
                            # 记录需要创建的关联
                            links_to_create.append((target_name, pipeline_id, drug_code))
                    else:
                        # 记录需要创建的靶点及对应的管线
                        if target_name not in targets_to_create:
                            targets_to_create[target_name] = {'drug_code': drug_code, 'pipeline_ids': []}
                        targets_to_create[target_name]['pipeline_ids'].append((pipeline_id, drug_code))

        # 创建新靶点
        logger.info(f"\n准备创建 {len(targets_to_create)} 个新靶点...")
        for target_name, info in targets_to_create.items():
            try:
                # 生成UUID
                target_id = str(uuid.uuid4())
                cursor.execute(
                    """INSERT INTO target (target_id, standard_name, aliases, category, description)
                       VALUES (%s, %s, %s, %s, %s)
                       RETURNING target_id""",
                    (target_id, target_name, '[]', '未知', f'自动创建于管线关联脚本: {info["drug_code"]}')
                )
                conn.commit()
                targets_created += 1
                logger.info(f"  ✓ 创建新靶点: {target_name}")

                # 为新创建的靶点创建管线关联
                for pipeline_id, drug_code in info['pipeline_ids']:
                    try:
                        cursor.execute(
                            """INSERT INTO target_pipeline (target_id, pipeline_id, relation_type, evidence_snippet)
                               VALUES (%s, %s, %s, %s)""",
                            (target_id, pipeline_id, 'targets', f'从适应症提取: {drug_code}')
                        )
                        conn.commit()
                        links_created += 1
                        logger.info(f"  ✓ 关联 {drug_code} -> {target_name}")
                    except Exception as e:
                        logger.error(f"  ✗ 关联失败 {drug_code} -> {target_name}: {e}")
                        conn.rollback()
            except Exception as e:
                logger.error(f"  ✗ 创建靶点失败 {target_name}: {e}")
                conn.rollback()

        # 创建关联
        logger.info(f"\n准备创建 {len(links_to_create)} 个关联...")
        for target_name, pipeline_id, drug_code in links_to_create:
            try:
                # 获取target_id
                cursor.execute(
                    "SELECT target_id FROM target WHERE standard_name = %s",
                    (target_name,)
                )
                result = cursor.fetchone()
                if result:
                    target_id = result['target_id']

                    # 创建关联
                    cursor.execute(
                        """INSERT INTO target_pipeline (target_id, pipeline_id, relation_type, evidence_snippet)
                           VALUES (%s, %s, %s, %s)""",
                        (target_id, pipeline_id, 'targets', f'从适应症提取: {drug_code}')
                    )
                    conn.commit()
                    links_created += 1
                    logger.info(f"  ✓ 关联 {drug_code} -> {target_name}")
            except Exception as e:
                logger.error(f"  ✗ 关联失败 {drug_code} -> {target_name}: {e}")
                conn.rollback()

        logger.info("=" * 60)
        logger.info("完成统计:")
        logger.info(f"  创建靶点: {targets_created}")
        logger.info(f"  创建关联: {links_created}")
        logger.info("=" * 60)

        cursor.close()

    except Exception as e:
        logger.error(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
