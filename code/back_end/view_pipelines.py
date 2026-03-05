"""
管线数据查看器（简化版）
"""

from utils.database import SessionLocal
from models.pipeline import Pipeline
from sqlalchemy import func

db = SessionLocal()

print('\n' + '='*80)
print('爬虫管线数据总览')
print('='*80)

# 总体统计
total = db.query(func.count(Pipeline.pipeline_id)).scalar()

# 按公司统计
company_stats = db.query(
    Pipeline.company_name,
    func.count(Pipeline.pipeline_id)
).group_by(Pipeline.company_name).all()

print(f'\n【总计】：{total} 条管线\n')

print('【各公司数据量】')
for company, count in company_stats:
    print(f'  • {company}: {count}条')

print('\n【最新数据预览】（最近10条）')
print('-'*80)

recent = db.query(Pipeline).order_by(
    Pipeline.updated_at.desc()
).limit(10).all()

for p in recent:
    combo = ' [联合用药]' if p.is_combination else ''
    print(f'\n{p.company_name} - {p.drug_code}{combo}')
    print(f'  适应症：{p.indication}')
    print(f'  阶段：{p.phase}')
    print(f'  状态：{p.status} | 更新时间：{p.updated_at.strftime("%m-%d %H:%M")}')

print('\n' + '='*80)

db.close()

print('\n提示：使用API查看更多数据')
print('  API文档：http://localhost:8000/docs')
print('  查询接口：GET /api/pipeline/search')
