"""
管线数据查询工具

使用方式：
    python query_pipeline.py              # 查看所有数据
    python query_pipeline.py --company 恒瑞医药  # 按公司查询
    python query_pipeline.py --phase 3    # 按阶段查询
"""

import sys
from utils.database import SessionLocal
from models.pipeline import Pipeline

def query_all():
    """查询所有管线数据"""
    db = SessionLocal()

    try:
        pipelines = db.query(Pipeline).order_by(
            Pipeline.company_name,
            Pipeline.drug_code
        ).all()

        print(f'\n总计：{len(pipelines)} 条管线记录\n')
        print('=' * 100)

        # 按公司分组
        companies = {}
        for p in pipelines:
            if p.company_name not in companies:
                companies[p.company_name] = []
            companies[p.company_name].append(p)

        for company, items in companies.items():
            print(f'\n【{company}】共 {len(items)} 条')
            print('-' * 100)

            for p in items:
                combo = f' [联合用药]' if p.is_combination else ''
                print(f'  • {p.drug_code}{combo}')
                print(f'    适应症：{p.indication}')
                print(f'    阶段：{p.phase}')
                print(f'    状态：{p.status}')
                if p.combination_drugs:
                    print(f'    联合药物：{p.combination_drugs}')
                print()

        print('=' * 100)

    finally:
        db.close()

def query_by_company(company_name):
    """按公司查询"""
    db = SessionLocal()

    try:
        pipelines = db.query(Pipeline).filter(
            Pipeline.company_name == company_name
        ).order_by(Pipeline.drug_code).all()

        print(f'\n【{company_name}】共 {len(pipelines)} 条管线\n')

        for p in pipelines:
            combo = f' [联合用药]' if p.is_combination else ''
            print(f'{p.drug_code}{combo}')
            print(f'  适应症：{p.indication}')
            print(f'  阶段：{p.phase}')
            print(f'  首次发现：{p.first_seen_at.strftime("%Y-%m-%d")}')
            print(f'  最近更新：{p.last_seen_at.strftime("%Y-%m-%d %H:%M")}')
            print()

    finally:
        db.close()

def show_statistics():
    """显示统计信息"""
    db = SessionLocal()

    try:
        from sqlalchemy import func

        # 总体统计
        total = db.query(func.count(Pipeline.pipeline_id)).scalar()

        # 按公司统计
        by_company = db.query(
            Pipeline.company_name,
            func.count(Pipeline.pipeline_id)
        ).group_by(Pipeline.company_name).all()

        # 按阶段统计
        by_phase = db.query(
            Pipeline.phase,
            func.count(Pipeline.pipeline_id)
        ).group_by(Pipeline.phase).all()

        # 联合用药统计
        combo_count = db.query(func.count(Pipeline.pipeline_id)).filter(
            Pipeline.is_combination == True
        ).scalar()

        print('\n' + '=' * 60)
        print('管线数据统计')
        print('=' * 60)
        print(f'\n总计：{total} 条')

        print('\n【按公司】')
        for company, count in sorted(by_company, key=lambda x: x[1], reverse=True):
            print(f'  {company}：{count}条')

        print('\n【按阶段】')
        for phase, count in sorted(by_phase):
            print(f'  {phase}：{count}条')

        print(f'\n【联合用药】：{combo_count}条')

        print('\n' + '=' * 60)

    finally:
        db.close()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        # 默认显示统计
        show_statistics()
        print('\n详细数据：\n')
        query_all()
    elif sys.argv[1] == '--company':
        query_by_company(sys.argv[2])
    elif sys.argv[1] == '--stats':
        show_statistics()
    else:
        print('使用方式：')
        print('  python query_pipeline.py              # 查看所有')
        print('  python query_pipeline.py --company 恒瑞医药')
        print('  python query_pipeline.py --stats     # 统计信息')
