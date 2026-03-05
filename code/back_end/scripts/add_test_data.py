"""
添加测试数据脚本
用于快速填充数据库，测试统一搜索功能
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, date
from utils.database import SessionLocal
from models.pipeline import Pipeline
from models.publication import Publication
from models.target import Target
import uuid

def add_test_targets():
    """添加测试靶点"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing = db.query(Target).count()
        if existing > 0:
            print(f"[OK] Target table has {existing} records, skipping")
            return

        targets = [
            Target(
                target_id=uuid.uuid4(),
                standard_name="EGFR",
                aliases=["ERBB1", "HER1"],
                gene_id="1956",
                uniprot_id="P00533",
                category="激酶",
                description="表皮生长因子受体"
            ),
            Target(
                target_id=uuid.uuid4(),
                standard_name="PD-1",
                aliases=["PDCD1", "CD279"],
                gene_id="5133",
                uniprot_id="Q15260",
                category="免疫检查点",
                description="程序性死亡受体1"
            ),
            Target(
                target_id=uuid.uuid4(),
                standard_name="HER2",
                aliases=["ERBB2"],
                gene_id="2064",
                uniprot_id="P04626",
                category="激酶",
                description="人表皮生长因子受体2"
            ),
            Target(
                target_id=uuid.uuid4(),
                standard_name="VEGF",
                aliases=["VEGFA"],
                gene_id="7422",
                uniprot_id="P15692",
                category="生长因子",
                description="血管内皮生长因子"
            ),
        ]

        db.add_all(targets)
        db.commit()
        print(f"[OK] Added {len(targets)} targets")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to add targets: {e}")
    finally:
        db.close()

def add_test_pipelines():
    """添加测试管线"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing = db.query(Pipeline).count()
        if existing > 0:
            print(f"✓ 管线表已有 {existing} 条数据，跳过添加")
            return

        pipelines = [
            Pipeline(
                pipeline_id=uuid.uuid4(),
                drug_code="SHR-1210",
                company_name="恒瑞医药",
                indication="EGFR抑制剂用于NSCLC治疗",
                phase="Phase 3",
                phase_raw="III期临床",
                modality="Small Molecule",
                source_url="https://www.hengrui.com",
                status="active"
            ),
            Pipeline(
                pipeline_id=uuid.uuid4(),
                drug_code="信迪利单抗",
                company_name="信达生物",
                indication="PD-1抗体用于NSCLC",
                phase="Phase 3",
                phase_raw="III期临床",
                modality="Monoclonal Antibody",
                source_url="https://www.innoventbio.com",
                status="active"
            ),
            Pipeline(
                pipeline_id=uuid.uuid4(),
                drug_code="吡咯替尼",
                company_name="恒瑞医药",
                indication="HER2阳性乳腺癌",
                phase="Approved",
                phase_raw="已批准",
                modality="Small Molecule",
                source_url="https://www.hengrui.com",
                status="active"
            ),
            Pipeline(
                pipeline_id=uuid.uuid4(),
                drug_code="替雷利珠单抗",
                company_name="百济神州",
                indication="PD-1抗体用于多种实体瘤",
                phase="Phase 3",
                phase_raw="III期临床",
                modality="Monoclonal Antibody",
                source_url="https://www.beigene.com",
                status="active"
            ),
            Pipeline(
                pipeline_id=uuid.uuid4(),
                drug_code="安罗替尼",
                company_name="正大天晴",
                indication="VEGFR抑制剂用于NSCLC",
                phase="Approved",
                phase_raw="已批准",
                modality="Small Molecule",
                source_url="https://www.cttq.com",
                status="active"
            ),
            Pipeline(
                pipeline_id=uuid.uuid4(),
                drug_code="HLX22",
                company_name="复宏汉霖",
                indication="HER2靶向治疗胃癌",
                phase="Phase 2",
                phase_raw="II期临床",
                modality="Monoclonal Antibody",
                source_url="https://www.henlius.com",
                status="active"
            ),
        ]

        db.add_all(pipelines)
        db.commit()
        print(f"✓ 成功添加 {len(pipelines)} 条管线")

    except Exception as e:
        db.rollback()
        print(f"✗ 添加管线失败: {e}")
    finally:
        db.close()

def add_test_publications():
    """添加测试文献"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing = db.query(Publication).count()
        if existing > 0:
            print(f"✓ 文献表已有 {existing} 条数据，跳过添加")
            return

        publications = [
            Publication(
                pmid=12345678,
                title="EGFR抑制剂在NSCLC中的III期临床试验",
                abstract="本研究评估了EGFR抑制剂治疗非小细胞肺癌的疗效和安全性",
                pub_date=date(2024, 1, 15),
                journal="J Clin Oncol",
                publication_type="Clinical Trial",
                clinical_data_tags=["ORR: 62%", "mPFS: 11.2月"]
            ),
            Publication(
                pmid=23456789,
                title="PD-1抗体联合化疗治疗晚期NSCLC",
                abstract="PD-1抗体联合化疗显著改善患者生存期",
                pub_date=date(2023, 12, 20),
                journal="Lancet Oncol",
                publication_type="Clinical Trial",
                clinical_data_tags=["ORR: 58%", "OS: 20.5月"]
            ),
            Publication(
                pmid=34567890,
                title="HER2靶向治疗乳腺癌的新进展",
                abstract="综述HER2靶向治疗的最新研究进展",
                pub_date=date(2024, 2, 1),
                journal="Nature Reviews Clinical Oncology",
                publication_type="Review",
                clinical_data_tags=[]
            ),
            Publication(
                pmid=45678901,
                title="VEGF抑制剂在肿瘤治疗中的应用",
                abstract="血管生成抑制剂的机制和临床应用",
                pub_date=date(2023, 11, 10),
                journal="Cancer Cell",
                publication_type="Research Article",
                clinical_data_tags=["mPFS: 9.8月"]
            ),
        ]

        db.add_all(publications)
        db.commit()
        print(f"✓ 成功添加 {len(publications)} 条文献")

    except Exception as e:
        db.rollback()
        print(f"✗ 添加文献失败: {e}")
    finally:
        db.close()

def main():
    """主函数"""
    print("=" * 60)
    print("开始添加测试数据...")
    print("=" * 60)

    add_test_targets()
    add_test_pipelines()
    add_test_publications()

    print("=" * 60)
    print("测试数据添加完成！")
    print("=" * 60)

    # 显示统计
    db = SessionLocal()
    target_count = db.query(Target).count()
    pipeline_count = db.query(Pipeline).count()
    publication_count = db.query(Publication).count()
    db.close()

    print(f"\n数据库统计：")
    print(f"  - 靶点: {target_count} 条")
    print(f"  - 管线: {pipeline_count} 条")
    print(f"  - 文献: {publication_count} 条")
    print(f"\n现在可以测试搜索功能了！")
    print(f"访问: http://localhost:8000/api/search/unified?q=EGFR")

if __name__ == "__main__":
    main()
