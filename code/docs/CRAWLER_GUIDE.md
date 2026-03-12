# 爬虫系统使用指南

> **版本**：1.0.0 | **更新时间**：2026-03-07

---

## 目录
- [一、爬虫系统架构](#一爬虫系统架构)
- [二、启用和禁用爬虫](#二启用和禁用爬虫)
- [三、手动运行爬虫](#三手动运行爬虫)
- [四、调度器配置](#四调度器配置)
- [五、选择性爬取](#五选择性爬取)
- [六、爬虫监控和日志](#六爬虫监控和日志)
- [七、常见问题解决](#七常见问题解决)

---

## 一、爬虫系统架构

### 1.1 系统组成

```
爬虫系统
│
├── 【调度器】Scheduler
│   ├── 定时触发（每天凌晨2点）
│   ├── 并发控制（最多3个爬虫同时运行）
│   ├── 错误重试（最多3次）
│   └── 执行日志记录
│
├── 【爬虫基类】BaseSpider
│   ├── HTTP请求管理
│   ├── HTML解析
│   ├── 数据标准化
│   ├── 数据库入库
│   └── 缓存管理
│
└── 【药企爬虫】Company Spiders
    ├── hengrui（恒瑞医药）
    ├── beigene（百济神州）
    ├── xindaa（信达生物）
    ├── junshi（军事医学科学院）
    ├── akeso（康方生物）
    ├── zailab（再鼎医药）
    ├── hutchmed（和黄医药）
    ├── wuxibiologics（无锡生物技术）
    ├── ascentage（亚盛医药）
    ├── simcere（先声药业）
    ├── cspc（石药集团）
    └── fosun（复星医药）
```

### 1.2 数据流程

```
1. 调度器触发 → 2. 爬虫运行 → 3. 数据解析 → 4. 数据入库 → 5. 日志记录
   ↓             ↓            ↓            ↓            ↓
定时任务      访问网站      提取管线      存入pipeline   记录执行状态
```

---

## 二、启用和禁用爬虫

### 2.1 全局启用/禁用

#### 方法1：修改 .env 文件（推荐）

**文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\.env`

```bash
# 启用所有爬虫
COMPANY_CRAWLER_ENABLED=true
CDE_CRAWLER_ENABLED=true
PATENT_CRAWLER_ENABLED=true

# 禁用所有爬虫
COMPANY_CRAWLER_ENABLED=false
CDE_CRAWLER_ENABLED=false
PATENT_CRAWLER_ENABLED=false
```

**重启后端生效**：
```bash
# 停止当前运行的后端（Ctrl+C）
# 重新启动
python main.py
```

#### 方法2：单独控制

```bash
# 只启用药企爬虫，禁用CDE和专利爬虫
COMPANY_CRAWLER_ENABLED=true
CDE_CRAWLER_ENABLED=false
PATENT_CRAWLER_ENABLED=false
```

### 2.2 单个爬虫启用/禁用

#### 修改爬虫类文件

**文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\crawlers\companies\[药企名].py`

```python
@spider_register("hengrui")
class HengruiSpider(CompanySpiderBase):
    # 添加这一行来禁用爬虫
    enabled = False  # 改为 True 启用
```

**可用的爬虫标识**：
- `hengrui` - 恒瑞医药
- `beigene` - 百济神州
- `xindaa` - 信达生物
- `junshi` - 军事医学科学院
- `akeso` - 康方生物
- `zailab` - 再鼎医药
- `hutchmed` - 和黄医药
- `wuxibiologics` - 无锡生物技术
- `ascentage` - 亚盛医药
- `simcere` - 先声药业
- `cspc` - 石药集团
- `fosun` - 复星医药

---

## 三、手动运行爬虫

### 3.1 运行所有爬虫

```bash
cd D:\26初寒假实习\A_lxl_search\code\back_end
python scripts/run_crawler.py --all
```

### 3.2 运行单个爬虫

```bash
# 运行恒瑞医药爬虫
python scripts/run_crawler.py --company hengrui

# 运行百济神州爬虫
python scripts/run_crawler.py --company beigene

# 运行信达生物爬虫
python scripts/run_crawler.py --company xindaa
```

### 3.3 仅分析网站结构

```bash
# 分析恒瑞医药网站，不抓取数据
python scripts/run_crawler.py --company hengrui --analyze-only
```

**输出示例**：
```
[*] 网站分析：恒瑞医药
[*] 主页：https://www.hengrui.com
[*] 管线页面：https://www.hengrui.com/pipeline
[*] 发现：15条管线记录
```

### 3.4 运行多个指定爬虫

```bash
# 同时运行多个爬虫
python scripts/run_crawler.py --company hengrui --company beigene --company xindaa
```

---

## 四、调度器配置

### 4.1 修改执行时间

**文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\.env`

```bash
# 默认：凌晨2点执行
CRAWLER_SCHEDULER_TIME="02:00"

# 改为下午2点执行
CRAWLER_SCHEDULER_TIME="14:00"

# 改为上午10点执行
CRAWLER_SCHEDULER_TIME="10:00"
```

**时间格式**：24小时制 `HH:MM`（小时:分钟）

**常见设置**：
| 时间 | 说明 |
|------|------|
| `02:00` | 凌晨2点（默认） |
| `06:00` | 早上6点 |
| `12:00` | 中午12点 |
| `18:00` | 晚上6点 |
| `23:00` | 晚上11点 |

### 4.2 修改执行频率

```bash
# .env 配置
COMPANY_CRAWLER_INTERVAL=24   # 每24小时（每天）
CDE_CRAWLER_INTERVAL=12       # 每12小时（每12小时）
PATENT_CRAWLER_INTERVAL=168   # 每168小时（每周）
```

**频率建议**：
| 爬虫类型 | 推荐频率 | 说明 |
|----------|----------|------|
| 药企官网 | 24-48小时 | 更新不频繁 |
| CDE平台 | 12小时 | 更新较频繁 |
| 专利数据 | 168小时 | 更新较慢 |

### 4.3 修改并发数

```bash
# .env 配置
CRAWLER_SCHEDULER_MAX_CONCURRENT=3  # 默认3个
```

**并发数建议**：
| 环境 | 推荐并发数 | 说明 |
|------|-----------|------|
| 开发 | 1-2个 | 避免影响开发 |
| 生产（网络好） | 3-5个 | 效率最高 |
| 生产（网络差） | 1个 | 避免失败 |

---

## 五、选择性爬取

### 5.1 按药企筛选

#### 一次性配置（长期生效）

创建自定义配置文件：

**文件位置**：`D:\26初寒假实习\A_lxl_search\code\back_end\.env.crawler`

```bash
# .env.crawler
# 只启用指定的爬虫
ENABLED_SPIDERS=hengrui,beigene,xindaa
DISABLED_SPIDERS=junshi,akeso,zailab
```

然后修改爬虫调度器代码以读取此配置。

#### 临时性配置（单次执行）

```bash
# 只运行指定的爬虫
python scripts/run_crawler.py --company hengrui --company beigene
```

### 5.2 按时间段爬取

#### 工作日爬取

```bash
# .env 配置
CRAWLER_SCHEDULER_TIME="02:00"  # 工作日凌晨2点
```

#### 周末爬取

```bash
# .env 配置
CRAWLER_SCHEDULER_TIME="10:00"  # 周末上午10点
```

### 5.3 按频率差异化配置

#### 快速爬取（测试用）

```bash
CRAWLER_DELAY=0.2              # 快速请求（可能被封IP）
COMPANY_CRAWLER_INTERVAL=1     # 每1小时执行
```

#### 稳定爬取（生产用）

```bash
CRAWLER_DELAY=0.5              # 正常速度
COMPANY_CRAWLER_INTERVAL=24    # 每24小时执行
```

#### 谨慎爬取（网站敏感）

```bash
CRAWLER_DELAY=2.0              # 慢速请求
COMPANY_CRAWLER_INTERVAL=48    # 每48小时执行
```

---

## 六、爬虫监控和日志

### 6.1 实时监控

#### 查看当前运行的爬虫

```python
from crawlers.scheduler import get_scheduler

scheduler = get_scheduler()
status = scheduler.get_status()
print(status)
```

**输出示例**：
```
{
  "running": false,
  "last_execution": "2026-03-07 02:00:00",
  "next_execution": "2026-03-08 02:00:00",
  "spider_status": {
    "hengrui": "success",
    "beigene": "success",
    "xindaa": "failed"
  }
}
```

### 6.2 查看执行日志

#### 实时查看

```bash
# Windows PowerShell
Get-Content back_end\logs\app.log -Wait | Select-String -Pattern "crawler"
```

#### 查看最近的日志

```bash
# 最近50行
Get-Content back_end\logs\app.log -Tail 50

# 最近100行，只看爬虫相关
Get-Content back_end\logs\app.log -Tail 100 | Select-String -Pattern "crawler"
```

#### 查看错误日志

```bash
Get-Content back_end\logs\app.log | Select-String -Pattern "ERROR" -Context 3
```

### 6.3 查看执行历史

#### 通过数据库查询

```python
from utils.database import SessionLocal
from models.crawler_execution_log import CrawlerExecutionLog

db = SessionLocal()

# 最近的执行记录
logs = db.query(CrawlerExecutionLog).order_by(
    CrawlerExecutionLog.start_time.desc()
).limit(10).all()

for log in logs:
    print(f"爬虫: {log.spider_name}")
    print(f"状态: {log.status}")
    print(f"开始时间: {log.start_time}")
    print(f"耗时: {log.duration_ms}ms")
    print(f"获取管线数: {log.pipeline_count}")
    print("-" * 40)

db.close()
```

### 6.4 性能监控

#### 查看爬虫性能指标

```python
# 统计成功率
import requests

# 查询爬虫统计API
response = requests.get("http://localhost:8000/api/v1/crawler/statistics")
stats = response.json()

print(f"总执行次数: {stats['total_executions']}")
print(f"成功率: {stats['success_rate']}%")
print(f"平均耗时: {stats['avg_duration_ms']}ms")
```

---

## 七、常见问题解决

### 7.1 爬虫运行失败

#### 问题：HTTP 403 Forbidden

**原因**：网站禁止爬虫访问

**解决方案**：

1. 增加请求延迟
```bash
# .env
CRAWLER_DELAY=1.0
```

2. 更换User-Agent
```python
# 在爬虫类中修改
self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
```

3. 使用代理（高级）
```python
self.session.proxies = {'http': 'http://proxy.example.com:8080'}
```

#### 问题：HTTP 429 Too Many Requests

**原因**：请求频率过高

**解决方案**：

1. 立即停止爬虫，避免被封IP
2. 增加请求延迟
```bash
CRAWLER_DELAY=2.0
```

3. 减少并发数
```bash
CRAWLER_SCHEDULER_MAX_CONCURRENT=1
```

4. 延长执行间隔
```bash
COMPANY_CRAWLER_INTERVAL=48
```

#### 问题：连接超时

**原因**：网络慢或网站响应慢

**解决方案**：

1. 增加超时时间
```bash
CRAWLER_TIMEOUT=60
```

2. 使用重试机制（已默认启用）
```bash
CRAWLER_RETRY_ENABLED=true
CRAWLER_RETRY_MAX_ATTEMPTS=3
```

### 7.2 数据问题

#### 问题：获取的管线数量为0

**排查步骤**：

1. 检查网站是否可访问
```bash
curl https://www.hengrui.com
```

2. 运行分析模式
```bash
python scripts/run_crawler.py --company hengrui --analyze-only
```

3. 检查日志中的错误信息
```bash
Get-Content logs\app.log -Tail 50 | Select-String -Pattern "hengrui"
```

4. 查看网站结构是否变化
   - 网站可能改版
   - URL可能变化
   - 需要更新爬虫代码

#### 问题：重复数据

**原因**：爬虫去重逻辑问题

**解决方案**：

1. 检查唯一约束
```sql
-- 查看 pipeline 表的唯一约束
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pipeline';
```

2. 手动去重
```sql
-- 删除重复数据
DELETE FROM pipeline
WHERE ctid NOT IN (
    SELECT min(ctid)
    FROM pipeline
    GROUP BY drug_code, company_name, indication
);
```

### 7.3 调度器问题

#### 问题：调度器不执行

**排查步骤**：

1. 检查调度器是否启用
```bash
# .env 配置
CRAWLER_SCHEDULER_ENABLED=true
```

2. 检查后端日志
```bash
Get-Content logs\app.log | Select-String -Pattern "scheduler"
```

3. 手动触发测试
```python
from crawlers.scheduler import get_scheduler

scheduler = get_scheduler()
await scheduler.trigger_now()
```

#### 问题：调度器执行时间不准确

**原因**：时区配置错误

**解决方案**：

```bash
# .env 配置
CRAWLER_SCHEDULER_TIMEZONE="Asia/Shanghai"  # 使用上海时区
```

**可用时区**：
- `Asia/Shanghai` - 上海（UTC+8）
- `Asia/Hong_Kong` - 香港（UTC+8）
- `Asia/Tokyo` - 东京（UTC+9）

---

## 附录A：爬虫参数完整列表

### 请求控制参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CRAWLER_USER_AGENT` | Mozilla/5.0 | 浏览器标识 |
| `CRAWLER_TIMEOUT` | 30秒 | 请求超时时间 |
| `CRAWLER_DELAY` | 0.3秒 | 请求间隔 |
| `CRAWLER_MAX_RETRIES` | 3 | 最大重试次数 |

### 调度器参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CRAWLER_SCHEDULER_ENABLED` | true | 启用调度器 |
| `CRAWLER_SCHEDULER_TIME` | "02:00" | 执行时间 |
| `CRAWLER_SCHEDULER_MAX_CONCURRENT` | 3 | 并发数 |
| `CRAWLER_SCHEDULER_TIMEZONE` | Asia/Shanghai | 时区 |

### 爬虫开关参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `COMPANY_CRAWLER_ENABLED` | true | 药企爬虫开关 |
| `CDE_CRAWLER_ENABLED` | true | CDE爬虫开关 |
| `PATENT_CRAWLER_ENABLED` | true | 专利爬虫开关 |

---

## 附录B：药企爬虫列表

### 已实现的爬虫

| 序号 | 爬虫标识 | 中文名称 | 官网 |
|------|----------|----------|------|
| 1 | hengrui | 恒瑞医药 | https://www.hengrui.com |
| 2 | beigene | 百济神州 | https://www.beigene.com |
| 3 | xindaa | 信达生物 | https://www.innoventbio.com |
| 4 | junshi | 军事医学科学院 | https://www.bmi.ac.cn |
| 5 | akeso | 康方生物 | https://www.akeso.com |
| 6 | zailab | 再鼎医药 | https://www.zailaboratory.com |
| 7 | hutchmed | 和黄医药 | https://www.hutchmed.com |
| 8 | wuxibiologics | 无锡生物技术 | https://www.wuxibiologics.com |
| 9 | ascentage | 亚盛医药 | https://www.ascentagepharm.com |
| 10 | simcere | 先声药业 | https://www.simcere.com |
| 11 | cspc | 石药集团 | https://www.cspc.com.hk |
| 12 | fosun | 复星医药 | https://www.fosunpharma.com |

---

**文档结束**

> 💡 **提示**：遇到问题时，首先查看日志文件 `back_end/logs/app.log`，通常能找到错误原因。
