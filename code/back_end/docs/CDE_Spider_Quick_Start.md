# CDE Spider 快速启动指南

## 前置条件
- PostgreSQL 数据库已启动
- `.env` 文件已配置
- 数据库表已创建

---

## 启动步骤

### 步骤 1: 初始化数据库
```bash
cd D:\26初寒假实习\A_lxl_search\code\back_end
python scripts/init_db.py
```

预期输出：
```
====================================================================
数据库初始化
====================================================================
步骤 1: 检查数据库连接...
✅ 数据库连接正常
步骤 2: 创建数据表...
✅ 所有表创建成功
步骤 3: 插入种子数据...
✅ 成功插入 6 条靶点数据
步骤 4: 验证数据完整性...
数据统计：
  Target（靶点）:        6 条
  Publication（文献）:   0 条
  Pipeline（管线）:      0 条
  CDEEvent（CDE事件）:   0 条
✅ 数据验证通过
```

### 步骤 2: 运行 CDE 爬虫（手动测试）

#### 方法 A: Python 命令行
```bash
python -c "from crawlers.cde_spider import CDESpider; spider = CDESpider(); stats = spider.run(); print(stats.to_dict())"
```

#### 方法 B: 交互式 Python
```bash
python
>>> from crawlers.cde_spider import CDESpider
>>> spider = CDESpider()
>>> stats = spider.run()
>>> print(stats.to_dict())
```

#### 方法 C: 创建测试脚本
创建 `test_cde_run.py`：
```python
#!/usr/bin/env python
"""手动测试 CDE 爬虫"""
from crawlers.cde_spider import CDESpider

spider = CDESpider()
print("Starting CDE spider...")

stats = spider.run()

print("\n" + "=" * 60)
print("CDE Spider Execution Summary")
print("=" * 60)
print(f"Total processed: {stats.get('total', 0)}")
print(f"Success: {stats.get('success', 0)}")
print(f"Failed: {stats.get('failed', 0)}")
print("=" * 60)
```

运行：
```bash
python test_cde_run.py
```

### 步骤 3: 验证数据库

#### 方法 A: 使用 psql
```bash
psql -U postgres -d pathology_ai -c "SELECT COUNT(*) FROM cde_events;"
psql -U postgres -d pathology_ai -c "SELECT * FROM cde_events ORDER BY undertake_date DESC LIMIT 10;"
```

#### 方法 B: 使用 Python
```python
from utils.database import SessionLocal
from models.cde_event import CDEEvent

db = SessionLocal()
count = db.query(CDEEvent).count()
print(f"Total CDE events: {count}")

events = db.query(CDEEvent).order_by(CDEEvent.undertake_date.desc()).limit(10).all()
for event in events:
    print(f"{event.acceptance_no} - {event.drug_name} - {event.applicant}")
db.close()
```

### 步骤 4: 启动 API 服务
```bash
python main.py
```

预期输出：
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 步骤 5: 测试 API

#### 5.1 查询 CDE 事件
```bash
curl "http://localhost:8000/api/cde/events?limit=10"
```

#### 5.2 按申请人筛选
```bash
curl "http://localhost:8000/api/cde/events?applicant=恒瑞&limit=10"
```

#### 5.3 按事件类型筛选
```bash
curl "http://localhost:8000/api/cde/events?event_type=IND&limit=10"
```

#### 5.4 获取统计信息
```bash
curl "http://localhost:8000/api/cde/events/stats"
```

#### 5.5 查询单个事件
```bash
curl "http://localhost:8000/api/cde/events/CXHS2600023"
```

### 步骤 6: 访问 API 文档
在浏览器中打开：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 常见问题

### Q1: 数据库连接失败
**错误**: `connection to server at "localhost", port 5432 failed`

**解决方案**:
1. 检查 PostgreSQL 是否启动
2. 检查 `.env` 文件中的数据库配置
3. 确认数据库已创建

### Q2: 爬虫返回 0 条数据
**可能原因**:
1. 网络连接问题
2. CDE 网站结构变化
3. 请求被拦截

**解决方案**:
1. 检查网络连接
2. 查看日志中的错误信息
3. 手动访问 CDE 网站验证 URL

### Q3: 端口 8000 已被占用
**错误**: `Address already in use`

**解决方案**:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# 或使用其他端口
uvicorn main:app --port 8001
```

---

## 监控和日志

### 查看爬虫日志
日志位置：`logs/cde_spider_*.log`

```bash
# 查看最新日志
tail -f logs/cde_spider_$(date +%Y%m%d).log
```

### 查看数据库统计
```sql
-- 总事件数
SELECT COUNT(*) FROM cde_events;

-- 按类型统计
SELECT event_type, COUNT(*) FROM cde_events GROUP BY event_type;

-- 按申请人统计（Top 10）
SELECT applicant, COUNT(*) as count
FROM cde_events
GROUP BY applicant
ORDER BY count DESC
LIMIT 10;

-- 近7天新增
SELECT COUNT(*) FROM cde_events
WHERE first_seen_at >= NOW() - INTERVAL '7 days';
```

---

## 性能指标

### 预期性能
- 单页爬取时间: ~1-2 秒
- 总数据量: ~1851 条（当前 CDE 网站）
- 预计总时间: ~30-60 分钟（取决于网络和 CDE 服务器响应）
- 速率限制: 0.3 QPS（每 3.3 秒 1 个请求）

### 优化建议
1. 使用数据库索引加速查询
2. 定期清理旧数据（`is_active=False`）
3. 使用缓存减少重复请求
4. 并发处理多个列表页（需谨慎，避免触发反爬虫）

---

## 下一步

1. **生产部署**
   - 配置定时任务（APScheduler）
   - 设置监控告警
   - 配置日志轮转

2. **功能增强**
   - 添加更多列表页 URL
   - 支持生物制品和中药
   - 实现增量更新优化

3. **数据分析**
   - CDE 事件趋势分析
   - 申请人竞争分析
   - 药品类型分布统计

---

## 参考文档
- [CDE Spider 实现总结](./CDE_Spider_Implementation_Summary.md)
- [API 文档](http://localhost:8000/docs)
- [数据库模型](../models/cde_event.py)
- [爬虫代码](../crawlers/cde_spider.py)
