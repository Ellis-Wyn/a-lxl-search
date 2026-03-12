"""
简单的数据库统计查询脚本（使用GBK编码）
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'drug_intelligence_db',
    'user': 'postgres',
    'password': 'yang051028',
    'client_encoding': 'GBK'  # 使用GBK编码
}

def main():
    conn = None
    try:
        # 连接数据库
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print("=" * 60)
        print("数据库统计信息")
        print("=" * 60)

        # 统计管线数量
        cursor.execute("SELECT COUNT(*) as count FROM pipeline")
        pipeline_count = cursor.fetchone()['count']
        print(f"管线数量: {pipeline_count}")

        # 统计靶点数量
        cursor.execute("SELECT COUNT(*) as count FROM target")
        target_count = cursor.fetchone()['count']
        print(f"靶点数量: {target_count}")

        # 统计关联数量
        cursor.execute("SELECT COUNT(*) as count FROM target_pipeline")
        link_count = cursor.fetchone()['count']
        print(f"靶点-管线关联数量: {link_count}")

        # 统计文献数量
        cursor.execute("SELECT COUNT(*) as count FROM publication")
        pub_count = cursor.fetchone()['count']
        print(f"文献数量: {pub_count}")

        # 统计公司数量
        cursor.execute("SELECT COUNT(DISTINCT company_name) as count FROM pipeline")
        company_count = cursor.fetchone()['count']
        print(f"公司数量: {company_count}")

        print("=" * 60)

        # 列出所有靶点
        print("\n所有靶点:")
        cursor.execute("SELECT standard_name, category FROM target ORDER BY standard_name")
        targets = cursor.fetchall()
        for t in targets:
            print(f"  - {t['standard_name']} ({t['category']})")

        cursor.close()

    except Exception as e:
        print(f"查询失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
