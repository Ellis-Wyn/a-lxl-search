# 快速参考卡 - Quick Reference Card

> **版本**：1.0.0 | **更新时间**：2026-03-07

---

## 🚀 快速启动

### 启动系统
```bash
# 后端
cd D:\26初寒假实习\A_lxl_search\code\back_end
python main.py

# 前端（新终端）
cd D:\26初寒假实习\A_lxl_search\code\front_end
npm run dev
```

### 访问地址
- **后端API**：http://localhost:8000
- **前端界面**：http://localhost:5173
- **API文档**：http://localhost:8000/docs

---

## 🎯 关键文件位置

| 用途 | 文件位置 |
|------|----------|
| **靶点数据** | `back_end/scripts/data/common_drug_targets.yaml` ⭐ |
| **主配置** | `back_end/.env` ⭐⭐⭐ |
| **日志文件** | `back_end/logs/app.log` ⭐ |
| **爬虫调度器** | `back_end/crawlers/scheduler.py` |
| **数据库查看** | `back_end/db_viewer.py` |

---

## 🕷️ 爬虫快速操作

### 启用/禁用爬虫
```bash
# 编辑 .env 文件
COMPANY_CRAWLER_ENABLED=true   # 启用
COMPANY_CRAWLER_ENABLED=false  # 禁用

# 重启后端生效
```

### 运行爬虫
```bash
# 运行所有爬虫
python scripts/run_crawler.py --all

# 运行单个爬虫
python scripts/run_crawler.py --company hengrui

# 可用药企: hengrui, beigene, xindaa, junshi, akeso...
```

### 爬虫配置参数
| 参数 | 默认值 | 推荐值 | 说明 |
|------|--------|--------|------|
| `CRAWLER_DELAY` | 0.3秒 | 0.5-1.0 | 请求间隔 |
| `CRAWLER_SCHEDULER_TIME` | 02:00 | 02:00 | 执行时间 |
| `CRAWLER_MAX_CONCURRENT` | 3 | 2-5 | 并发数 |

---

## 💾 数据库操作

### 查看统计
```bash
python scripts/check_stats.py
```

### 导入靶点
```bash
python scripts/import_common_targets.py
```

### 备份数据库
```bash
pg_dump -U postgres -d drug_intelligence_db > backup.sql
```

---

## ⚙️ 常用配置修改

### 修改数据库密码
```bash
# 编辑 .env
DB_PASSWORD=你的新密码
```

### 修改爬虫执行时间
```bash
# 编辑 .env
CRAWLER_SCHEDULER_TIME="14:30"  # 改为下午2:30
```

### 修改日志级别
```bash
# 编辑 .env
LOG_LEVEL=DEBUG   # 开发环境
LOG_LEVEL=INFO    # 生产环境
```

---

## 🐛 常见问题

### 后端无法启动
```bash
# 1. 检查PostgreSQL
Get-Service postgresql*

# 2. 检查端口占用
netstat -ano | findstr :8000

# 3. 查看日志
Get-Content logs\app.log -Tail 50
```

### 爬虫失败
```bash
# 1. 检查爬虫是否启用
cat .env | findstr "CRAWLER_ENABLED"

# 2. 查看错误日志
Get-Content logs\app.log | findstr "ERROR"

# 3. 测试单个爬虫
python scripts/run_crawler.py --company hengrui --analyze-only
```

### 数据库连接失败
```bash
# 1. 测试连接
psql -U postgres -d drug_intelligence_db -c "SELECT 1;"

# 2. 检查配置
cat .env | findstr "DB_"

# 3. 重启PostgreSQL
Restart-Service postgresql-x64-15
```

---

## 📊 数据控制快速指南

### 添加新靶点
1. 编辑 `scripts/data/common_drug_targets.yaml`
2. 运行 `python scripts/import_common_targets.py`

### 修改爬虫配置
1. 编辑 `.env` 文件
2. 重启后端服务器

### 查看系统状态
1. 查看日志：`Get-Content logs\app.log -Tail 50`
2. 查看统计：`python scripts/check_stats.py`

---

**提示**：完整文档请参阅 `OPERATIONS_MANUAL.md`
