"""
数据库信息查看脚本
"""
import sys
import io

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from utils.database import SessionLocal
from sqlalchemy import func
from models.pipeline import Pipeline
from models.target import Target
from models.publication import Publication

def show_database_info():
    """显示数据库基本信息"""
    print("=" * 80)
    print("📊 数据库信息概览")
    print("=" * 80)

    db = SessionLocal()
    try:
        # 统计各表的记录数
        pipeline_count = db.query(Pipeline).count()
        target_count = db.query(Target).count()
        publication_count = db.query(Publication).count()

        print(f"\n📈 数据统计:")
        print(f"  - 管线表 (pipeline): {pipeline_count} 条记录")
        print(f"  - 靶点表 (target): {target_count} 条记录")
        print(f"  - 文献表 (publication): {publication_count} 条记录")

        # 显示公司列表
        print(f"\n🏢 所有公司（按管线数量排序）:")
        companies = db.query(
            Pipeline.company_name,
            func.count(Pipeline.pipeline_id).label('count')
        ).group_by(
            Pipeline.company_name
        ).order_by(
            func.desc('count')
        ).all()

        for i, (company, count) in enumerate(companies, 1):
            print(f"  {i}. {company}: {count} 条管线")

        # 显示前5条管线
        print(f"\n💊 前5条管线数据:")
        pipelines = db.query(Pipeline).limit(5).all()
        for i, p in enumerate(pipelines, 1):
            print(f"  {i}. {p.drug_code} | {p.company_name} | {p.indication} | {p.phase}")

    finally:
        db.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    show_database_info()
