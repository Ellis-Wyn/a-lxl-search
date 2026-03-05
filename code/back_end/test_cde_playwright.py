#!/usr/bin/env python
"""
CDE Spider Playwright 版本测试脚本
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from crawlers.cde_spider_playwright import CDESpiderPlaywright
from utils.database import SessionLocal
from models.cde_event import CDEEvent

print("=" * 70)
print("CDE Spider (Playwright) Manual Test")
print("=" * 70)
print()

# 统计初始数据库中的事件数
db = SessionLocal()
initial_count = db.query(CDEEvent).count()
db.close()
print(f"Initial CDE events in database: {initial_count}")
print()

# 创建爬虫实例
spider = CDESpiderPlaywright()

print("Spider Configuration:")
print(f"  Base URL: {spider.base_url}")
print(f"  List Page URLs: {len(spider.list_page_urls)}")
for i, url in enumerate(spider.list_page_urls, 1):
    print(f"    {i}. {url}")
print()

print("Starting CDE spider (Playwright)...")
print("This may take a few minutes (browser automation)...")
print("-" * 70)

try:
    # 运行爬虫
    stats = spider.run()

    print("-" * 70)
    print()
    print("=" * 70)
    print("CDE Spider Execution Summary")
    print("=" * 70)

    # 统计结果
    db = SessionLocal()
    final_count = db.query(CDEEvent).count()
    new_events = final_count - initial_count

    print(f"Initial events: {initial_count}")
    print(f"Final events: {final_count}")
    print(f"New events added: {new_events}")
    print()
    print("Statistics:")
    if hasattr(stats, 'to_dict'):
        stats_dict = stats.to_dict()
        for key, value in stats_dict.items():
            print(f"  {key}: {value}")
    else:
        print(f"  {stats}")

    print()

    # 显示最新的几条记录
    if new_events > 0:
        latest_events = db.query(CDEEvent).order_by(
            CDEEvent.first_seen_at.desc()
        ).limit(5).all()

        print("Latest 5 events:")
        for event in latest_events:
            print(f"  - {event.acceptance_no}: {event.drug_name} ({event.applicant})")
            print(f"    Event Type: {event.event_type}")
            print(f"    Drug Type: {event.drug_type}")
            print(f"    Undertake Date: {event.undertake_date}")
            print(f"    URL: {event.public_page_url}")
            print()

        db.close()

    print("=" * 70)
    print("Test completed successfully!")

except Exception as e:
    print()
    print("=" * 70)
    print(f"ERROR: {e}")
    print("=" * 70)
    import traceback
    traceback.print_exc()
    sys.exit(1)
