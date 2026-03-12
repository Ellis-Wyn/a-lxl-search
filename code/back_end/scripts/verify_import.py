"""
验证靶点导入结果
"""
import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'drug_intelligence_db',
    'user': 'postgres',
    'password': 'yang051028',
    'client_encoding': 'GBK'
}

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# 检查关键靶点
key_targets = ['EGFR', 'HER2', 'PI3Kα', 'PD-1', 'ALK', 'KRAS', 'CD19', 'PARP1']

print("=" * 60)
print("验证关键靶点是否已导入：")
print("=" * 60)

for target in key_targets:
    cursor.execute("SELECT standard_name, category FROM target WHERE standard_name = %s", (target,))
    result = cursor.fetchone()
    if result:
        print(f"[+] {result[0]:15s} - {result[1]}")
    else:
        print(f"[x] {target:15s} - 未找到")

# 统计总数
cursor.execute("SELECT COUNT(*) FROM target")
total = cursor.fetchone()[0]

print("\n" + "=" * 60)
print(f"数据库靶点总数：{total}")
print("=" * 60)

cursor.close()
conn.close()
