# 病理AI药研情报库 - 项目操作维护手册

> **版本**：1.0.0
> **更新时间**：2026-03-07
> **适用范围**：开发环境、生产环境

---

## 📋 目录

- [一、项目概览](#一项目概览)
- [二、数据控制位置映射](#二数据控制位置映射)
- [三、配置文件详解](#三配置文件详解)
- [四、爬虫系统完整指南](#四爬虫系统完整指南)
- [五、常用操作命令](#五常用操作命令)
- [六、故障排查指南](#六故障排查指南)
- [七、快速参考卡](#七快速参考卡)

---

## 一、项目概览

### 1.1 系统简介

**病理AI药研情报库** 是一个基于 FastAPI + React 的药物研发情报系统，主要功能包括：

- 🎯 **靶点数据管理**：基因、蛋白靶点信息
- 💊 **药物管线监控**：药企研发进展追踪
- 📚 **PubMed文献爬取**：自动抓取和分析学术文献
- 🏛️ **CDE平台监管信息**：药品监管动态抓取
- ⚠️ **智能预警系统**：Phase Jump、竞品退场预警

### 1.2 技术栈

#### 后端
```
Python 3.14+
FastAPI          # Web框架
PostgreSQL 15    # 数据库
SQLAlchemy       # ORM
Redis            # 缓存
Uvicorn          # ASGI服务器
APScheduler      # 任务调度
```

#### 前端
```
React 19.2.0
Vite             # 构建工具
React Router     # 路由管理
Axios            # HTTP客户端
```

### 1.3 项目目录结构

```
D:\26初寒假实习\A_lxl_search\code\
├── back_end/                    # 后端项目根目录
│   ├── main.py                  # FastAPI应用入口
│   ├── config.py                # 配置类定义
│   ├── .env                     # 环境变量配置
│   ├── requirements.txt         # Python依赖
│   ├── models/                  # 数据模型
│   │   ├── target.py           # 靶点表
│   │   ├── pipeline.py          # 管线表
│   │   ├── publication.py       # 文献表
│   │   └── relationships.py     # 关联表
│   ├── crawlers/                # 爬虫系统
│   │   ├── base_spider.py      # 爬虫基类
│   │   ├── scheduler.py        # 调度器
│   │   └── companies/          # 药企爬虫
│   ├── scripts/                 # 工具脚本
│   │   ├── data/               # 数据文件
│   │   │   └── common_drug_targets.yaml  # 靶点数据
│   │   ├── import_common_targets.py     # 靶点导入
│   │   ├── check_stats.py              # 统计检查
│   │   └── db_viewer.py                # 数据库查看
│   ├── services/                # 业务服务层
│   ├── api/                     # API路由
│   ├── core/                    # 核心模块
│   ├── utils/                   # 工具函数
│   ├── logs/                    # 日志目录
│   └── static/                  # 静态文件
├── front_end/                   # 前端项目根目录
│   ├── src/                     # 源代码
│   │   ├── pages/              # 页面组件
│   │   ├── api/                # API封装
│   │   └── context/            # 状态管理
│   ├── package.json            # 依赖配置
│   ├── vite.config.js          # 构建配置
│   └── dist/                   # 构建输出
└── docs/                       # 文档目录
    └── OPERATIONS_MANUAL.md    # 本手册
```

---

## 二、数据控制位置映射

### 2.1 配置文件控制

#### 🔧 后端主配置文件

**文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\.env`

| 参数 | 说明 | 示例值 |
|------|------|--------|
| **数据库配置** |
| `DB_HOST` | 数据库主机 | localhost |
| `DB_PORT` | 数据库端口 | 5432 |
| `DB_NAME` | 数据库名称 | drug_intelligence_db |
| `DB_USER` | 数据库用户名 | postgres |
| `DB_PASSWORD` | 数据库密码 | yang051028 |
| **应用配置** |
| `APP_NAME` | 应用名称 | 病理AI药研情报库 |
| `APP_VERSION` | 应用版本 | 1.0.0 |
| `DEBUG` | 调试模式 | true |
| **PubMed配置** |
| `PUBMED_EMAIL` | NCBI邮箱（必填） | test@example.com |
| `PUBMED_API_KEY` | API密钥（可选） | 从NCBI获取 |
| **爬虫配置** |
| `COMPANY_CRAWLER_ENABLED` | 药企爬虫开关 | true/false |
| `CDE_CRAWLER_ENABLED` | CDE爬虫开关 | true/false |
| `PATENT_CRAWLER_ENABLED` | 专利爬虫开关 | true/false |
| `CRAWLER_DELAY` | 请求间隔（秒） | 0.3 |
| **预警配置** |
| `ALERT_PHASE_JUMP_ENABLED` | Phase Jump预警 | true/false |
| `ALERT_DISAPPEARED_THRESHOLD` | 竞品退场阈值（天） | 21 |
| **日志配置** |
| `LOG_LEVEL` | 日志级别 | INFO/DEBUG/ERROR |
| `LOG_FILE` | 日志文件路径 | logs/app.log |

#### 🔧 Python配置类

**文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\config.py`

提供所有配置的Python类定义，支持环境变量覆盖。

### 2.2 数据源控制

#### 🎯 靶点数据控制

**数据文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\scripts\data\common_drug_targets.yaml`

```yaml
# 靶点数据示例
growth_factor_receptors:
  - standard_name: EGFR
    aliases: [ERBB1, HER1]
    category: 生长因子受体
    description: Epidermal Growth Factor Receptor
    gene_id: HGNC:3233
```

**操作方式**：
1. **查看现有靶点**：直接编辑YAML文件
2. **添加新靶点**：在对应类别下添加条目
3. **导入靶点**：运行 `python scripts/import_common_targets.py`

**模型文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\models\target.py`

定义靶点数据结构：
- `standard_name`：标准名称（唯一）
- `aliases`：别名数组（JSONB）
- `gene_id`：HGNC基因ID
- `uniprot_id`：UniProt ID
- `category`：分类
- `description`：描述

#### 💊 管线数据控制

**数据来源**：爬虫自动抓取

**模型文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\models\pipeline.py`

**爬虫控制**：
- 药企爬虫目录：`D:\26初寒假实习\A_lxl_search\code\back_end\crawlers\companies\`
- 调度器配置：`D:\26初寒假实习\A_lxl_search\code\back_end\crawlers\scheduler.py`

**手动添加管线**：通过API接口

#### 📚 文献数据控制

**数据来源**：PubMed API自动抓取

**模型文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\models\publication.py`

**API配置**：在 `.env` 中配置 `PUBMED_EMAIL` 和可选的 `PUBMED_API_KEY`

### 2.3 日志文件位置

**日志目录**：`D:\26初寒假实习\A_lxl_search\code\back_end\logs\`

**日志文件**：
- `app.log` - 主应用日志
- 爬虫执行日志会记录到 `app.log`

**查看日志**：
```bash
# 实时查看日志
tail -f back_end/logs/app.log

# Windows PowerShell
Get-Content back_end\logs\app.log -Wait
```

### 2.4 静态资源位置

| 资源类型 | 位置 |
|----------|------|
| 后端日志 | `back_end/logs/` |
| 前端构建输出 | `front_end/dist/` |
| 上传文件 | `back_end/static/uploads/` |
| 数据库备份 | 用户自定义目录 |

---

## 三、配置文件详解

### 3.1 后端配置文件（.env）完整说明

```bash
# =====================================================
# 应用基础配置
# =====================================================
APP_NAME="病理AI药研情报库"      # 应用名称
APP_VERSION="1.0.0"               # 版本号
DEBUG=true                        # 调试模式（生产环境设为false）

# =====================================================
# 数据库配置（PostgreSQL）
# =====================================================
DB_HOST=localhost                 # 数据库主机
DB_PORT=5432                      # 数据库端口
DB_NAME=drug_intelligence_db      # 数据库名称
DB_USER=postgres                  # 数据库用户名
DB_PASSWORD=yang051028            # 数据库密码

# 数据库连接池配置
DB_POOL_SIZE=5                    # 连接池大小
DB_MAX_OVERFLOW=10                # 最大溢出连接数
DB_POOL_TIMEOUT=30                # 连接超时（秒）
DB_POOL_RECYCLE=3600              # 连接回收时间（秒）

# =====================================================
# PubMed API 配置
# =====================================================
PUBMED_EMAIL=test@example.com     # 必填：NCBI要求提供邮箱
PUBMED_API_KEY=                   # 可选：从https://www.ncbi.nlm.nih.gov/account/获取
PUBMED_RATE_LIMIT=3               # 无API密钥时的每秒请求数限制

# =====================================================
# 爬虫配置
# =====================================================
CRAWLER_USER_AGENT="Mozilla/5.0"  # User-Agent
CRAWLER_TIMEOUT=30                 # 请求超时（秒）
CRAWLER_DELAY=0.3                  # 请求间隔（秒），建议0.5-1.0

# 药企官网爬虫
COMPANY_CRAWLER_ENABLED=true       # 启用/禁用
COMPANY_CRAWLER_INTERVAL=24        # 执行间隔（小时）

# CDE平台爬虫
CDE_CRAWLER_ENABLED=true
CDE_CRAWLER_INTERVAL=12            # 执行间隔（小时）

# 专利爬虫
PATENT_CRAWLER_ENABLED=true
PATENT_CRAWLER_INTERVAL=168         # 执行间隔（小时，168=每周）

# =====================================================
# 爬虫调度器配置
# =====================================================
CRAWLER_SCHEDULER_ENABLED=true     # 启用调度器
CRAWLER_SCHEDULER_TIME="02:00"     # 执行时间（24小时制HH:MM）
CRAWLER_SCHEDULER_MAX_CONCURRENT=3 # 最大并发爬虫数
CRAWLER_SCHEDULER_TIMEZONE="Asia/Shanghai"  # 时区

# =====================================================
# 爬虫重试配置
# =====================================================
CRAWLER_RETRY_ENABLED=true                    # 启用重试
CRAWLER_RETRY_MAX_ATTEMPTS=3                 # 最大重试次数
CRAWLER_RETRY_BASE_DELAY=60.0                # 基础延迟（秒）
CRAWLER_RETRY_BACKOFF_FACTOR=5.0             # 退避因子
CRAWLER_RETRY_MAX_DELAY=900.0                # 最大延迟（15分钟）

# =====================================================
# 预警配置
# =====================================================
# Phase Jump预警
ALERT_PHASE_JUMP_ENABLED=true               # 启用Phase Jump预警
ALERT_PHASE_JUMP_PHASES=["II", "III"]       # 监控的阶段跳转

# 竞品退场预警
ALERT_DISAPPEARED_THRESHOLD=21              # 连续21天未抓取到即预警
ALERT_DISAPPEARED_CHECK_ENABLED=true        # 启用检查

# 新入局者预警
ALERT_NEW_ENTRY_ENABLED=true                # 启用新入局者预警

# =====================================================
# 数据处理配置
# =====================================================
# 文献排序权重
WEIGHT_RECENCY_DAYS=730                     # 考虑最近730天（24个月）
WEIGHT_RECENCY_RATIO=0.7                    # 时间权重占比

# 临床数据加分
SCORE_CLINICAL_DATA=50                     # 有临床数据加分
SCORE_PHASE_III=40                         # Phase III加分
SCORE_FIRST_IN_CLASS=30                    # 首创药加分

# 综述减分
SCORE_REVIEW=-10                           # 综述减分
SCORE_CASE_REPORT=-20                      # 病例报告减分

# =====================================================
# Redis 缓存配置
# =====================================================
REDIS_ENABLED=true                         # 启用Redis缓存
REDIS_HOST=localhost                       # Redis主机
REDIS_PORT=6379                            # Redis端口
REDIS_DB=0                                 # Redis数据库编号
REDIS_PASSWORD=                            # Redis密码（如需要）

# 缓存TTL配置（秒）
REDIS_TTL_PUBMED=7200                      # PubMed缓存：2小时
REDIS_TTL_SEARCH=1800                      # 搜索缓存：30分钟
REDIS_TTL_PIPELINE=3600                    # 管线缓存：1小时
REDIS_TTL_CDE=86400                        # CDE缓存：24小时
REDIS_TTL_DEFAULT=3600                    # 默认缓存：1小时

# =====================================================
# 日志配置
# =====================================================
LOG_LEVEL=INFO                             # 日志级别：DEBUG/INFO/WARNING/ERROR
LOG_FILE=logs/app.log                      # 日志文件路径
```

### 3.2 前端配置文件

**文件位置**：`D:\26初寒假实习\A_lxl_search\code\front_end\package.json`

```json
{
  "name": "front_end",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",              # 开发服务器：npm run dev
    "build": "vite build",      # 生产构建：npm run build
    "preview": "vite preview"   # 预览构建结果
  },
  "dependencies": {
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "react-router-dom": "^7.13.0",
    "axios": "^1.13.4"
  }
}
```

**API地址配置**：`D:\26初寒假实习\A_lxl_search\code\front_end\src\api\index.js`

```javascript
// 默认配置
const BASE_URL = 'http://localhost:8000/api/v1';
```

---

## 四、爬虫系统完整指南

### 4.1 爬虫架构

```
爬虫系统架构
│
├── 调度器 (Scheduler)
│   ├── 定时触发
│   ├── 并发控制
│   └── 错误重试
│
├── 爬虫基类 (BaseSpider)
│   ├── HTTP请求
│   ├── HTML解析
│   ├── 数据标准化
│   └── 数据库入库
│
└── 药企爬虫 (Company Spiders)
    ├── 恒瑞医药 (hengrui)
    ├── 百济神州 (beigene)
    ├── 信达生物 (xindaa)
    ├── 军事医学科学院 (junshi)
    ├── 康方生物 (akeso)
    └── ... (更多药企)
```

### 4.2 爬虫启用/禁用方法

#### 🎯 方法1：通过 .env 文件（推荐）

```bash
# 编辑文件
D:\26初寒假实习\A_lxl_search\code\back_end\.env

# 启用所有爬虫
COMPANY_CRAWLER_ENABLED=true
CDE_CRAWLER_ENABLED=true
PATENT_CRAWLER_ENABLED=true

# 禁用所有爬虫
COMPANY_CRAWLER_ENABLED=false
CDE_CRAWLER_ENABLED=false
PATENT_CRAWLER_ENABLED=false

# 只启用特定爬虫
COMPANY_CRAWLER_ENABLED=true
CDE_CRAWLER_ENABLED=false
PATENT_CRAWLER_ENABLED=false
```

**修改后需要重启后端服务器**

#### 🎯 方法2：通过环境变量

```bash
# Windows PowerShell
$env:COMPANY_CRAWLER_ENABLED="true"
python main.py

# Windows CMD
set COMPANY_CRAWLER_ENABLED=true
python main.py
```

#### 🎯 方法3：通过代码修改（不推荐）

**文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\config.py`

```python
class Settings(BaseSettings):
    COMPANY_CRAWLER_ENABLED: bool = False  # 修改默认值
```

### 4.3 选择性爬取配置

#### 📌 按药企筛选

**当前已实现的药企爬虫**：

| 药企名称 | 爬虫标识 | 公司名称映射 |
|----------|----------|--------------|
| 恒瑞医药 | hengrui | 江苏恒瑞医药 |
| 百济神州 | beigene | 百济神州（苏州） |
| 信达生物 | xindaa | 信达生物制药 |
| 军事医学科学院 | junshi | 军事医学科学院 |
| 康方生物 | akeso | 康方生物药业 |
| 再鼎医药 | zailab | 再鼎医药 |
| 和黄医药 | hutchmed | 和黄中国医药 |
| 无锡生物技术 | wuxibiologics | 药明康德 |
| 亚盛医药 | ascentage | 广东亚盛药业 |
| 先声药业 | simcere | 先声药业 |
| 石药集团 | cspc | 石药集团 |
| 复星医药 | fosun | 上海复星医药 |

**单个爬虫启用/禁用**：

方法1：修改爬虫类文件
```python
# 文件位置：back_end/crawlers/companies/hengrui.py

@spider_register("hengrui")
class HengruiSpider(CompanySpiderBase):
    enabled = False  # 添加这一行禁用该爬虫
```

方法2：修改 .env 配置（推荐）
```bash
# 在 .env 中添加特定药企的开关
HENG_RUI_ENABLED=false
BEI_GENE_ENABLED=true
```

#### 📌 按时间段爬取

**修改调度器执行时间**：

```bash
# 编辑 .env 文件
CRAWLER_SCHEDULER_TIME="02:00"    # 凌晨2点执行
CRAWLER_SCHEDULER_TIME="14:30"    # 下午2:30执行
```

**时间格式**：24小时制 `HH:MM`

#### 📌 按频率控制

```bash
# 编辑 .env 文件
COMPANY_CRAWLER_INTERVAL=24   # 每24小时爬取一次药企
CDE_CRAWLER_INTERVAL=12       # 每12小时爬取一次CDE
PATENT_CRAWLER_INTERVAL=168   # 每7天爬取一次专利
```

**单位**：小时

#### 📌 并发控制

```bash
# 编辑 .env 文件
CRAWLER_SCHEDULER_MAX_CONCURRENT=3  # 同时运行3个爬虫
```

**推荐值**：
- 开发环境：1-2个
- 生产环境：3-5个
- 网络较差：1个

### 4.4 爬虫手动触发

#### 立即运行所有爬虫

```bash
cd D:\26初寒假实习\A_lxl_search\code\back_end
python scripts/run_crawler.py --all
```

#### 运行单个爬虫

```bash
# 运行恒瑞医药爬虫
python scripts/run_crawler.py --company hengrui

# 运行百济神州爬虫
python scripts/run_crawler.py --company beigene
```

#### 仅分析网站结构（不抓取数据）

```bash
python scripts/run_crawler.py --company hengrui --analyze-only
```

### 4.5 爬虫监控与日志

#### 查看爬虫执行日志

```bash
# 实时查看日志
Get-Content back_end\logs\app.log -Wait | Select-String -Pattern "crawler"

# 查看最近的爬虫日志
Get-Content back_end\logs\app.log -Tail 50 | Select-String -Pattern "crawler"
```

#### 爬虫执行记录

**查询表位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\models\crawler_execution_log.py`

查询最近执行记录：
```python
from utils.database import SessionLocal
from models.crawler_execution_log import CrawlerExecutionLog

db = SessionLocal()
logs = db.query(CrawlerExecutionLog).order_by(
    CrawlerExecutionLog.start_time.desc()
).limit(10).all()

for log in logs:
    print(f"{log.spider_name}: {log.status} - {log.duration_ms}ms")
```

### 4.6 爬虫参数调优

#### 请求延迟（避免被封IP）

```bash
# .env 配置
CRAWLER_DELAY=0.3    # 默认0.3秒
```

**推荐值**：
- 正常使用：0.3-0.5秒
- 网站敏感：1.0-2.0秒
- 大规模抓取：2.0-5.0秒

#### 超时时间

```bash
CRAWLER_TIMEOUT=30    # 默认30秒
```

**推荐值**：
- 正常网站：30秒
- 慢速网站：60秒
- 可能超时：90秒

#### 重试配置

```bash
CRAWLER_RETRY_MAX_ATTEMPTS=3       # 最多重试3次
CRAWLER_RETRY_BASE_DELAY=60.0      # 基础延迟60秒
CRAWLER_RETRY_BACKOFF_FACTOR=5.0   # 退避因子5倍
```

**重试延迟计算**：
- 第1次重试：60秒
- 第2次重试：60 × 5 = 300秒（5分钟）
- 第3次重试：300 × 5 = 1500秒（25分钟）

---

## 五、常用操作命令

### 5.1 系统启动/停止

#### 后端服务

```bash
# 进入后端目录
cd D:\26初寒假实习\A_lxl_search\code\back_end

# 启动开发服务器（自动重载）
python main.py

# 或使用uvicorn直接启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 停止服务器
Ctrl + C
```

#### 前端服务

```bash
# 进入前端目录
cd D:\26初寒假实习\A_lxl_search\code\front_end

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

#### Docker方式（推荐生产环境）

```bash
# 启动所有服务
cd back_end
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止所有服务
docker-compose down
```

### 5.2 数据导入/导出

#### 靶点数据导入

```bash
# 导入常见药物靶点
python scripts/import_common_targets.py

# 导入自定义靶点文件
python scripts/import_common_targets.py scripts/data/custom_targets.yaml
```

#### 数据库备份

```bash
# 备份数据库
pg_dump -U postgres -d drug_intelligence_db > backup_$(date +%Y%m%d).sql

# Windows PowerShell
$timestamp = Get-Date -Format "yyyyMMdd"
pg_dump -U postgres -d drug_intelligence_db > "backup_$timestamp.sql"
```

#### 数据库恢复

```bash
# 恢复数据库
psql -U postgres -d drug_intelligence_db < backup_20260307.sql
```

### 5.3 数据库操作

#### 查看数据库统计

```bash
# 查看完整统计
python scripts/check_stats.py

# 使用db_viewer
python db_viewer.py stats
python db_viewer.py targets
python db_viewer.py companies
```

#### 直接查询数据库

```bash
# 进入PostgreSQL
psql -U postgres -d drug_intelligence_db

# 查询示例
SELECT COUNT(*) FROM pipeline;
SELECT COUNT(*) FROM target;
SELECT COUNT(*) FROM publication;

# 退出
\q
```

### 5.4 爬虫管理

#### 查看爬虫状态

```bash
# 查看调度器状态
python -c "from crawlers.scheduler import get_scheduler; s=get_scheduler(); print(s.get_status())"
```

#### 手动触发爬虫

```bash
# 运行所有爬虫
python scripts/run_crawler.py --all

# 运行单个爬虫
python scripts/run_crawler.py --company hengrui
```

#### 查看爬虫日志

```bash
# 实时查看
Get-Content back_end\logs\app.log -Wait

# 查看最近100行
Get-Content back_end\logs\app.log -Tail 100
```

### 5.5 日志查看

#### 应用主日志

```bash
# 实时监控
Get-Content back_end\logs\app.log -Wait

# 搜索错误日志
Get-Content back_end\logs\app.log | Select-String -Pattern "ERROR"

# 搜索爬虫日志
Get-Content back_end\logs\app.log | Select-String -Pattern "crawler"
```

#### 日志级别说明

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 调试信息 | 函数调用、变量值 |
| INFO | 一般信息 | 操作成功、进度更新 |
| WARNING | 警告信息 | 重试、配置问题 |
| ERROR | 错误信息 | 异常、失败 |

---

## 六、故障排查指南

### 6.1 数据库连接问题

#### 问题：无法连接到数据库

**症状**：
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方案**：

1. 检查PostgreSQL是否运行
```bash
pg_isready -h localhost -p 5432
```

2. 检查数据库服务（Windows）
```bash
# 查看PostgreSQL服务状态
Get-Service -Name "postgresql*"

# 启动服务
Start-Service postgresql-x64-15
```

3. 验证 .env 配置
```bash
# 检查配置
cat back_end\.env | Select-String -Pattern "DB_"

# 确认以下参数正确
DB_HOST=localhost
DB_PORT=5432
DB_NAME=drug_intelligence_db
DB_USER=postgres
DB_PASSWORD=你的密码
```

4. 测试数据库连接
```bash
psql -U postgres -d drug_intelligence_db -c "SELECT 1;"
```

### 6.2 爬虫失败问题

#### 问题：爬虫运行失败

**症状**：
```
ERROR: Spider execution failed
```

**解决方案**：

1. 检查爬虫是否启用
```bash
# 查看 .env 配置
cat back_end\.env | Select-String -Pattern "CRAWLER_ENABLED"
```

2. 查看详细错误日志
```bash
Get-Content back_end\logs\app.log -Tail 100 | Select-String -Pattern "ERROR" -Context 5
```

3. 手动测试单个爬虫
```bash
python scripts/run_crawler.py --company hengrui --analyze-only
```

4. 检查网络连接
```bash
# 测试网站是否可访问
curl https://www.hengrui.com

# 检查DNS解析
nslookup hengrui.com
```

5. 增加超时时间
```bash
# 修改 .env
CRAWLER_TIMEOUT=60
```

#### 问题：爬虫被反爬虫阻止

**症状**：
```
HTTP 403 Forbidden
HTTP 429 Too Many Requests
```

**解决方案**：

1. 增加请求延迟
```bash
CRAWLER_DELAY=1.0
```

2. 更换User-Agent
```python
# 在爬虫类中修改
self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...'
```

3. 启用代理（如需要）
```python
# 在爬虫类中添加
self.proxies = {'http': 'http://proxy.example.com:8080'}
```

### 6.3 前端显示问题

#### 问题：前端无法访问后端API

**症状**：
- 浏览器控制台出现CORS错误
- API请求失败

**解决方案**：

1. 确认后端服务运行
```bash
curl http://localhost:8000/api/v1/targets
```

2. 检查前端API配置
```javascript
// 文件：front_end/src/api/index.js
const BASE_URL = 'http://localhost:8000/api/v1';
```

3. 检查CORS配置（后端已配置允许所有来源）
```python
# config.py
CORS_ORIGINS = ["*"]  # 允许所有来源
```

#### 问题：前端页面显示旧数据

**解决方案**：

1. 清除浏览器缓存
```
Ctrl + Shift + Delete
```

2. 清除前端构建缓存
```bash
cd front_end
rm -rf dist
npm run build
```

3. 硬刷新页面
```
Ctrl + F5
```

### 6.4 性能问题

#### 问题：响应速度慢

**解决方案**：

1. 启用Redis缓存
```bash
# .env 配置
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

2. 增加数据库连接池
```bash
# .env 配置
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

3. 优化查询（添加索引）
```sql
-- 示例：为常用查询字段添加索引
CREATE INDEX idx_pipeline_phase ON pipeline(phase);
CREATE INDEX idx_pipeline_company ON pipeline(company_name);
```

#### 问题：爬虫速度慢

**解决方案**：

1. 调整并发数
```bash
CRAWLER_SCHEDULER_MAX_CONCURRENT=5
```

2. 减少请求延迟（谨慎使用）
```bash
CRAWLER_DELAY=0.2
```

3. 启用响应缓存
```python
# 在爬虫基类中已默认启用
ENABLE_CACHE=True
CACHE_TTL=3600
```

---

## 七、快速参考卡

### 7.1 常用文件路径速查

| 用途 | 文件路径 |
|------|----------|
| **配置文件** |
| 主配置 | `back_end/.env` |
| Python配置类 | `back_end/config.py` |
| **数据文件** |
| 靶点数据 | `back_end/scripts/data/common_drug_targets.yaml` |
| **爬虫相关** |
| 爬虫基类 | `back_end/crawlers/base_spider.py` |
| 调度器 | `back_end/crawlers/scheduler.py` |
| 药企爬虫 | `back_end/crawlers/companies/*.py` |
| **工具脚本** |
| 数据库查看 | `back_end/db_viewer.py` |
| 统计检查 | `back_end/scripts/check_stats.py` |
| 靶点导入 | `back_end/scripts/import_common_targets.py` |
| **日志文件** |
| 应用日志 | `back_end/logs/app.log` |

### 7.2 常用命令速查

#### 系统操作
```bash
# 启动后端
cd back_end && python main.py

# 启动前端
cd front_end && npm run dev

# 查看数据库统计
python scripts/check_stats.py
```

#### 爬虫操作
```bash
# 运行所有爬虫
python scripts/run_crawler.py --all

# 运行单个爬虫
python scripts/run_crawler.py --company hengrui

# 仅分析网站
python scripts/run_crawler.py --company hengrui --analyze-only
```

#### 数据库操作
```bash
# 数据库备份
pg_dump -U postgres -d drug_intelligence_db > backup.sql

# 数据库恢复
psql -U postgres -d drug_intelligence_db < backup.sql

# 连接数据库
psql -U postgres -d drug_intelligence_db
```

### 7.3 配置参数速查

#### 爬虫控制参数
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `COMPANY_CRAWLER_ENABLED` | 药企爬虫开关 | true |
| `CDE_CRAWLER_ENABLED` | CDE爬虫开关 | true |
| `CRAWLER_DELAY` | 请求间隔（秒） | 0.3 |
| `CRAWLER_SCHEDULER_TIME` | 执行时间 | "02:00" |
| `CRAWLER_SCHEDULER_MAX_CONCURRENT` | 并发数 | 3 |

#### 数据库连接参数
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `DB_HOST` | 数据库主机 | localhost |
| `DB_PORT` | 数据库端口 | 5432 |
| `DB_NAME` | 数据库名称 | drug_intelligence_db |
| `DB_POOL_SIZE` | 连接池大小 | 5 |

### 7.4 端口和服务

| 服务 | 端口 | 访问地址 |
|------|------|----------|
| 后端API | 8000 | http://localhost:8000 |
| 前端开发服务器 | 5173 | http://localhost:5173 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |

### 7.5 紧急故障处理

#### 后端无法启动
```bash
# 1. 检查端口占用
netstat -ano | findstr :8000

# 2. 检查数据库连接
pg_isready -h localhost -p 5432

# 3. 查看启动日志
python main.py 2>&1 | head -50
```

#### 爬虫全部失败
```bash
# 1. 检查网络连接
ping google.com

# 2. 检查爬虫配置
cat .env | findstr "CRAWLER"

# 3. 查看详细错误
Get-Content logs\app.log -Tail 50 | findstr "ERROR"
```

#### 数据库无响应
```bash
# 1. 检查PostgreSQL服务
Get-Service postgresql*

# 2. 重启服务（如需要）
Restart-Service postgresql-x64-15

# 3. 检查数据库连接
psql -U postgres -d drug_intelligence_db -c "SELECT version();"
```

---

## 附录A：完整文件清单

### 后端核心文件

```
back_end/
├── main.py                          # FastAPI应用入口
├── config.py                        # 配置类定义
├── .env                             # 环境变量配置 ⭐
├── requirements.txt                 # Python依赖
│
├── models/                          # 数据模型
│   ├── target.py                    # 靶点表定义 ⭐
│   ├── pipeline.py                   # 管线表定义 ⭐
│   ├── publication.py                # 文献表定义
│   ├── relationships.py              # 关联表定义
│   ├── cde_event.py                 # CDE事件表
│   └── crawler_execution_log.py     # 爬虫执行日志
│
├── crawlers/                        # 爬虫系统
│   ├── base_spider.py              # 爬虫基类 ⭐
│   ├── scheduler.py                # 调度器 ⭐
│   └── companies/                  # 药企爬虫
│       ├── hengrui.py              # 恒瑞医药 ⭐
│       ├── beigene.py              # 百济神州 ⭐
│       ├── xindaa.py               # 信达生物 ⭐
│       ├── junshi.py               # 军事医学科学院 ⭐
│       ├── akeso.py                # 康方生物 ⭐
│       ├── zailab.py               # 再鼎医药
│       ├── hutchmed.py             # 和黄医药
│       ├── wuxibiologics.py        # 无锡生物技术
│       ├── ascentage.py            # 亚盛医药
│       ├── simcere.py              # 先声药业
│       ├── cspc.py                 # 石药集团
│       └── fosun.py                # 复星医药
│
├── scripts/                        # 工具脚本
│   ├── data/                       # 数据文件
│   │   └── common_drug_targets.yaml  # 靶点数据 ⭐⭐⭐
│   ├── import_common_targets.py    # 靶点导入 ⭐⭐⭐
│   ├── check_stats.py              # 统计检查 ⭐
│   ├── run_crawler.py              # 爬虫运行 ⭐
│   ├── link_targets_simple.py     # 靶点关联
│   └── db_viewer.py                # 数据库查看 ⭐
│
├── services/                       # 业务服务
│   ├── pipeline_service.py         # 管线服务
│   ├── target_service.py           # 靶点服务
│   ├── publication_service.py      # 文献服务
│   └── crawler_scheduler_service.py # 爬虫调度服务
│
├── api/                            # API路由
│   ├── v1/
│   │   ├── targets.py              # 靶点API
│   │   ├── pipelines.py           # 管线API
│   │   ├── publications.py        # 文献API
│   │   └── search.py              # 搜索API
│
├── utils/                          # 工具函数
│   ├── database.py                 # 数据库连接 ⭐
│   └── company_name_mapper.py     # 公司名称映射
│
└── logs/                           # 日志目录 ⭐
    └── app.log                     # 主日志文件 ⭐
```

### 前端核心文件

```
front_end/
├── package.json                    # 依赖配置 ⭐
├── vite.config.js                  # 构建配置 ⭐
├── index.html                      # HTML入口
│
├── src/
│   ├── main.jsx                    # React入口
│   ├── App.jsx                     # 根组件
│   │
│   ├── pages/                      # 页面组件
│   │   ├── Home/                   # 首页 ⭐
│   │   ├── Targets/                # 靶点页面
│   │   ├── Pipelines/             # 管线页面
│   │   └── Publications/           # 文献页面
│   │
│   ├── api/                        # API封装 ⭐
│   │   └── index.js                # 统一API接口
│   │
│   └── context/                    # 状态管理
│       └── DataContext.js         # 数据上下文
│
└── dist/                           # 构建输出
```

---

## 附录B：联系方式与技术支持

### 问题反馈

如遇到本手册未涵盖的问题，请通过以下方式反馈：

1. **查看日志**：`back_end/logs/app.log`
2. **检查配置**：`back_end/.env`
3. **参考源码**：查看相关文件的注释和文档

### 文档更新

本手册最后更新时间：**2026-03-07**

---

**文档结束**

> 💡 **提示**：建议将此手册加入书签，方便日常维护时快速查阅。
