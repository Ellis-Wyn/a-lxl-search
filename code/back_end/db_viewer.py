"""
数据库查看工具集

提供多种方式查看数据库内容：
1. 查看总体统计
2. 查看特定公司的管线
3. 搜索管线
4. 查看靶点信息
5. 查看文献信息

使用方式：
    python db_viewer.py stats          # 查看统计
    python db_viewer.py companies      # 查看所有公司
    python db_viewer.py company 百济神州  # 查看特定公司
    python db_viewer.py search BGB     # 搜索管线
    python db_viewer.py targets        # 查看靶点
    python db_viewer.py publications   # 查看文献
"""
import sys
import io

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from utils.database import SessionLocal
from models.pipeline import Pipeline
from models.target import Target
from models.publication import Publication


def show_stats():
    """显示数据库统计信息"""
    print("=" * 80)
    print("📊 数据库统计信息")
    print("=" * 80)

    db = SessionLocal()
    try:
        pipeline_count = db.query(Pipeline).count()
        target_count = db.query(Target).count()
        publication_count = db.query(Publication).count()

        print(f"\n总数据量:")
        print(f"  管线: {pipeline_count} 条")
        print(f"  靶点: {target_count} 条")
        print(f"  文献: {publication_count} 条")

        # 按阶段统计管线
        print(f"\n按阶段统计:")
        pipelines = db.query(Pipeline.phase).all()
        phase_counts = {}
        for (phase,) in pipelines:
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        for phase, count in sorted(phase_counts.items()):
            print(f"  {phase}: {count} 条")

    finally:
        db.close()

    print("\n" + "=" * 80)


def show_companies():
    """显示所有公司及其管线数量"""
    print("=" * 80)
    print("🏢 所有公司管线统计")
    print("=" * 80)

    db = SessionLocal()
    try:
        pipelines = db.query(Pipeline.company_name).all()
        company_counts = {}
        for (company_name,) in pipelines:
            company_counts[company_name] = company_counts.get(company_name, 0) + 1

        sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)

        print(f"\n共 {len(sorted_companies)} 家公司:\n")
        for i, (company, count) in enumerate(sorted_companies, 1):
            print(f"  {i:2d}. {company:30s} : {count:3d} 条管线")

    finally:
        db.close()

    print("\n" + "=" * 80)


def show_company_pipelines(company_keyword):
    """显示特定公司的管线"""
    print("=" * 80)
    print(f"🔍 查找公司: {company_keyword}")
    print("=" * 80)

    from utils.company_name_mapper import get_company_mapper
    mapper = get_company_mapper()

    # 标准化公司名称
    standard_name = mapper.normalize(company_keyword)

    if not standard_name:
        # 尝试模糊匹配
        standard_name = mapper.find_match(company_keyword)

    if not standard_name:
        print(f"\n❌ 未找到匹配的公司: {company_keyword}")
        print("\n💡 提示: 使用 'python db_viewer.py companies' 查看所有公司")
        return

    print(f"\n✅ 匹配到公司: {standard_name}")

    db = SessionLocal()
    try:
        pipelines = db.query(Pipeline).filter(
            Pipeline.company_name == standard_name
        ).all()

        if not pipelines:
            print(f"\n❌ 该公司没有管线数据")
            return

        print(f"\n共 {len(pipelines)} 条管线:\n")

        for i, p in enumerate(pipelines, 1):
            print(f"  {i}. {p.drug_code}")
            print(f"     适应症: {p.indication}")
            print(f"     阶段: {p.phase}")
            print(f"     药物类型: {p.modality or '未知'}")
            if p.source_url:
                print(f"     来源: {p.source_url}")
            print()

    finally:
        db.close()

    print("=" * 80)


def search_pipelines(keyword):
    """搜索管线"""
    print("=" * 80)
    print(f"🔍 搜索关键词: {keyword}")
    print("=" * 80)

    db = SessionLocal()
    try:
        # 使用公司名称映射
        from utils.company_name_mapper import get_company_mapper
        mapper = get_company_mapper()
        standard_name = mapper.normalize(keyword)

        # 构建查询
        from sqlalchemy import or_
        query = db.query(Pipeline)

        conditions = []
        conditions.append(Pipeline.drug_code.contains(keyword))
        conditions.append(Pipeline.indication.contains(keyword))

        # 如果关键词匹配到公司，添加公司条件
        if standard_name:
            conditions.append(Pipeline.company_name == standard_name)
            print(f"\n✅ 关键词匹配到公司: {standard_name}")

        query = query.filter(or_(*conditions))
        pipelines = query.limit(20).all()

        if not pipelines:
            print(f"\n❌ 未找到匹配的管线")
            return

        print(f"\n找到 {len(pipelines)} 条管线:\n")

        for i, p in enumerate(pipelines, 1):
            print(f"  {i}. {p.drug_code} | {p.company_name} | {p.indication} | {p.phase}")

    finally:
        db.close()

    print("\n" + "=" * 80)


def show_targets():
    """显示所有靶点"""
    print("=" * 80)
    print("🎯 所有靶点")
    print("=" * 80)

    db = SessionLocal()
    try:
        targets = db.query(Target).all()

        if not targets:
            print("\n❌ 暂无靶点数据")
            return

        print(f"\n共 {len(targets)} 个靶点:\n")

        for i, t in enumerate(targets, 1):
            print(f"  {i}. {t.standard_name}")
            if t.gene_id:
                print(f"     Gene ID: {t.gene_id}")
            if t.category:
                print(f"     分类: {t.category}")
            if t.aliases:
                print(f"     别名: {', '.join(t.aliases[:3])}")
            print()

    finally:
        db.close()

    print("=" * 80)


def show_publications():
    """显示所有文献"""
    print("=" * 80)
    print("📚 所有文献")
    print("=" * 80)

    db = SessionLocal()
    try:
        pubs = db.query(Publication).order_by(Publication.pub_date.desc()).all()

        if not pubs:
            print("\n❌ 暂无文献数据")
            return

        print(f"\n共 {len(pubs)} 篇文献:\n")

        for i, p in enumerate(pubs, 1):
            print(f"  {i}. {p.title}")
            print(f"     期刊: {p.journal or '未知'}")
            print(f"     发表日期: {p.pub_date or '未知'}")
            if p.pmid:
                print(f"     PMID: {p.pmid}")
            print()

    finally:
        db.close()

    print("=" * 80)


def print_help():
    """显示帮助信息"""
    print("=" * 80)
    print("数据库查看工具 - 使用说明")
    print("=" * 80)
    print("""
使用方式：
    python db_viewer.py <命令> [参数]

可用命令：
    stats                    查看数据库统计信息
    companies                查看所有公司及其管线数量
    company <公司名>         查看特定公司的所有管线
    search <关键词>          搜索管线（支持药物代码、适应症、公司名）
    targets                  查看所有靶点
    publications             查看所有文献
    help                     显示此帮助信息

示例：
    python db_viewer.py stats
    python db_viewer.py companies
    python db_viewer.py company 百济神州
    python db_viewer.py company 百济        # 支持简称
    python db_viewer.py search BGB
    python db_viewer.py search 肺癌
    python db_viewer.py targets
    python db_viewer.py publications
""")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
    else:
        command = sys.argv[1].lower()

        if command == "stats":
            show_stats()
        elif command == "companies":
            show_companies()
        elif command == "company":
            if len(sys.argv) < 3:
                print("❌ 请提供公司名称")
                print("   示例: python db_viewer.py company 百济神州")
            else:
                company_name = " ".join(sys.argv[2:])
                show_company_pipelines(company_name)
        elif command == "search":
            if len(sys.argv) < 3:
                print("❌ 请提供搜索关键词")
                print("   示例: python db_viewer.py search BGB")
            else:
                keyword = " ".join(sys.argv[2:])
                search_pipelines(keyword)
        elif command == "targets":
            show_targets()
        elif command == "publications":
            show_publications()
        elif command == "help":
            print_help()
        else:
            print(f"❌ 未知命令: {command}")
            print("\n使用 'python db_viewer.py help' 查看帮助")
