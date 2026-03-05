from utils.database import SessionLocal
from models.pipeline import Pipeline

db = SessionLocal()
companies = db.query(Pipeline.company_name).distinct().all()

print('数据库中的所有公司:')
for i, (c,) in enumerate(companies, 1):
    print(f'{i}. {c}')
    # 显示每个公司的管线数量
    count = db.query(Pipeline).filter(Pipeline.company_name == c).count()
    print(f'   管线数: {count}')

db.close()
