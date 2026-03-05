# 药企爬虫开发指南

## 目录

1. [概述](#概述)
2. [架构设计](#架构设计)
3. [快速开始](#快速开始)
4. [开发新爬虫](#开发新爬虫)
5. [网站分析](#网站分析)
6. [数据解析](#数据解析)
7. [测试](#测试)
8. [部署](#部署)
9. [最佳实践](#最佳实践)

## 概述

药企爬虫系统用于从药企官网自动抓取管线数据并入库。

### 核心功能

- ✅ 自动抓取药企官网管线数据
- ✅ 智能阶段标准化（PhaseMapper）
- ✅ 自动去重（基于 drug_code + company_name + indication）
- ✅ 数据来源追踪（source_url）
- ✅ 统计信息追踪

### 技术栈

- **HTTP 请求**: requests
- **HTML 解析**: BeautifulSoup4
- **ORM**: SQLAlchemy
- **数据标准化**: PhaseMapper
- **日志**: structlog

## 架构设计

### 组件关系

```
CompanySpiderFactory (工厂)
    ↓
CompanySpiderBase (基类)
    ↓
具体爬虫 (HengruiSpider, BeigeneSpider, ...)
    ↓
PipelineDataItem (数据模型)
    ↓
Pipeline (数据库表)
```

### 核心类说明

#### 1. CompanySpiderBase

基础爬虫类，提供通用功能：

```python
class CompanySpiderBase:
    def fetch_page(url: str) -> Response  # HTTP 请求
    def parse_html(html: str) -> BeautifulSoup  # HTML 解析
    def normalize_phase(raw_phase: str) -> str  # 阶段标准化
    def save_to_database(item: PipelineDataItem) -> bool  # 入库
    def run() -> CrawlerStats  # 运行爬虫（需子类实现）
```

#### 2. PipelineDataItem

管线数据模型：

```python
@dataclass
class PipelineDataItem:
    drug_code: str          # 药物代码（必填）
    company_name: str       # 公司名称（必填）
    indication: str         # 适应症（必填）
    phase: str             # 研发阶段（必填）
    modality: Optional[str] # 药物类型（可选）
    source_url: Optional[str] # 来源 URL（推荐）
    targets: List[str]      # 靶点列表（可选）
    description: Optional[str] # 描述（可选）
```

#### 3. CrawlerStats

爬虫统计信息：

```python
@dataclass
class CrawlerStats:
    total_fetched: int  # 总抓取数
    success: int        # 成功数
    failed: int         # 失败数
    skipped: int        # 跳过数
    errors: List[str]   # 错误列表
```

## 快速开始

### 1. 运行现有爬虫

```bash
# 运行恒瑞医药爬虫
python scripts/run_crawler.py --company hengrui

# 运行所有爬虫
python scripts/run_crawler.py --all

# 仅分析网站（不抓取）
python scripts/run_crawler.py --company hengrui --analyze-only
```

### 2. 查看爬虫列表

```bash
python -c "from crawlers.company_spider import CompanySpiderFactory; print(CompanySpiderFactory.list_spiders())"
```

### 3. 查看帮助

```bash
python scripts/run_crawler.py --help
```

## 开发新爬虫

### 步骤 1: 分析目标网站

使用网站分析工具：

```bash
python scripts/analyze_company_website.py --company beigene
```

分析工具会输出：
- ✅ 网站可访问性
- ✅ 找到的管线页面
- ✅ HTML 结构分析
- ✅ 开发建议

### 步骤 2: 创建爬虫文件

在 `crawlers/company_crawlers/` 下创建新文件：

```bash
touch crawlers/company_crawlers/beigene_spider.py
```

### 步骤 3: 实现爬虫类

```python
"""
百济神州官网爬虫
"""

from typing import List, Optional
from bs4 import BeautifulSoup, Tag

from crawlers.company_spider import (
    CompanySpiderBase,
    PipelineDataItem,
    CrawlerStats,
    spider_register,
)
from core.logger import get_logger

logger = get_logger(__name__)


@spider_register("beigene")
class BeigeneSpider(CompanySpiderBase):
    """
    百济神州爬虫

    官网：https://www.beigene.com
    """

    def __init__(self):
        super().__init__()
        self.name = "百济神州"
        self.company_name = "百济神州"
        self.base_url = "https://www.beigene.com"

        # 管线页面 URL
        self.pipeline_urls = [
            "https://www.beigene.com/pipeline",
        ]

    def run(self) -> CrawlerStats:
        """运行爬虫"""
        logger.info(f"Starting {self.name} spider...")

        for url in self.pipeline_urls:
            logger.info(f"Fetching: {url}")

            response = self.fetch_page(url)
            if not response:
                self.stats.add_failed(f"Failed to fetch: {url}")
                continue

            # 解析管线数据
            pipelines = self.parse_pipeline_page(response.text)

            # 入库
            for item in pipelines:
                success = self.save_to_database(item)
                if success:
                    self.stats.add_success()
                else:
                    self.stats.add_failed(f"Failed to save: {item.drug_code}")

        logger.info(f"Spider completed. Stats: {self.stats.to_dict()}")
        return self.stats

    def parse_pipeline_page(self, html: str) -> List[PipelineDataItem]:
        """解析管线页面"""
        soup = self.parse_html(html)
        pipelines = []

        # 根据实际 HTML 结构调整选择器
        # 示例：查找表格行
        table = soup.find("table", class_="pipeline-table")
        if table:
            rows = table.find_all("tr")[1:]  # 跳过表头

            for row in rows:
                pipeline_data = self.parse_pipeline_item(row)
                if pipeline_data:
                    pipelines.append(pipeline_data)

        logger.info(f"Parsed {len(pipelines)} pipelines from page")
        return pipelines

    def parse_pipeline_item(self, item_html: Tag) -> Optional[PipelineDataItem]:
        """解析单个管线项目"""
        try:
            # 根据实际 HTML 结构提取数据
            cells = item_html.find_all("td")

            if len(cells) < 3:
                return None

            drug_code = cells[0].text.strip()
            indication = cells[1].text.strip()
            phase = cells[2].text.strip()
            modality = cells[3].text.strip() if len(cells) > 3 else None

            # 验证必填字段
            if not drug_code or not indication or not phase:
                logger.warning(f"Missing required fields: {drug_code}")
                return None

            return PipelineDataItem(
                drug_code=drug_code,
                company_name=self.company_name,
                indication=indication,
                phase=phase,
                modality=modality,
                source_url=self.base_url,
            )

        except Exception as e:
            logger.error(f"Error parsing pipeline item: {e}")
            return None
```

### 步骤 4: 注册爬虫

在 `scripts/run_crawler.py` 中注册：

```python
AVAILABLE_SPIDERS = {
    "hengrui": {...},
    "beigene": {
        "name": "百济神州",
        "class": BeigeneSpider,
        "description": "百济神州管线爬虫",
    },
}
```

### 步骤 5: 测试爬虫

```bash
# 运行测试
python scripts/run_crawler.py --company beigene

# 查看结果
python -c "
from utils.database import SessionLocal
from models.pipeline import Pipeline

db = SessionLocal()
pipelines = db.query(Pipeline).filter(Pipeline.company_name == '百济神州').all()
print(f'Found {len(pipelines)} pipelines')
db.close()
"
```

## 网站分析

### 使用 analyze_company_website.py

```bash
# 分析已配置的公司
python scripts/analyze_company_website.py --company hengrui

# 保存分析结果
python scripts/analyze_company_website.py --company hengrui --output analysis.json
```

### 分析输出示例

```
============================================================
分析结果
============================================================
公司: 恒瑞医药
官网: https://www.hengrui.com
可访问: ✅ 是

找到的管线页面:
  - https://www.hengrui.com/Product
    标题: 产品中心 - 恒瑞医药

页面结构分析:
  容器数量: 0
  表格数量: 2
  表单数量: 0

开发建议:
  ✅ 页面包含表格，可以解析 <table> 元素
  ℹ️  页面可能包含分页，需要处理多页数据
  ℹ️  请检查 robots.txt 确认爬取规则
  ℹ️  建议设置 0.3-0.5 秒的请求间隔
```

## 数据解析

### 常见 HTML 结构模式

#### 1. 表格结构

```html
<table class="pipeline-table">
  <thead>
    <tr>
      <th>药物代码</th>
      <th>适应症</th>
      <th>阶段</th>
      <th>类型</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>BGB-311</td>
      <td>非小细胞肺癌</td>
      <td>Phase 3</td>
      <td>小分子</td>
    </tr>
  </tbody>
</table>
```

解析代码：

```python
table = soup.find("table", class_="pipeline-table")
rows = table.find_all("tr")[1:]  # 跳过表头

for row in rows:
    cells = row.find_all("td")
    drug_code = cells[0].text.strip()
    indication = cells[1].text.strip()
    phase = cells[2].text.strip()
```

#### 2. 卡片结构

```html
<div class="pipeline-card">
  <h3 class="drug-code">BGB-311</h3>
  <p class="indication">非小细胞肺癌</p>
  <span class="phase">Phase 3</span>
</div>
```

解析代码：

```python
cards = soup.find_all("div", class_="pipeline-card")

for card in cards:
    drug_code = card.find("h3", class_="drug-code").text.strip()
    indication = card.find("p", class_="indication").text.strip()
    phase = card.find("span", class_="phase").text.strip()
```

#### 3. 列表结构

```html
<ul class="pipeline-list">
  <li>
    <span class="drug-code">BGB-311</span>
    <span class="indication">非小细胞肺癌</span>
    <span class="phase">Phase 3</span>
  </li>
</ul>
```

解析代码：

```python
items = soup.find_all("li", class_="pipeline-item")

for item in items:
    drug_code = item.find("span", class_="drug-code").text.strip()
    indication = item.find("span", class_="indication").text.strip()
    phase = item.find("span", class_="phase").text.strip()
```

### 阶段标准化

PhaseMapper 会自动标准化阶段：

```python
# 以下都会被标准化为 "Phase 3"
"Phase 3"   -> "Phase 3"
"Phase III" -> "Phase 3"
"Phase 3 trial" -> "Phase 3"
"三期" -> "Phase 3"
"三期临床" -> "Phase 3"
```

## 测试

### 1. 单元测试

创建测试文件 `tests/test_crawlers.py`：

```python
import pytest
from crawlers.company_crawlers.hengrui_spider import HengruiManualSpider
from crawlers.company_spider import PipelineDataItem

def test_hengrui_spider():
    """测试恒瑞医药爬虫"""
    spider = HengruiManualSpider()
    stats = spider.run()

    assert stats.total_fetched == 3
    assert stats.success == 3
    assert stats.failed == 0
```

运行测试：

```bash
pytest tests/test_crawlers.py -v
```

### 2. 手动测试

```bash
# 运行单个爬虫
python scripts/run_crawler.py --company hengrui

# 检查数据库
python -c "
from utils.database import SessionLocal
from models.pipeline import Pipeline

db = SessionLocal()
pipelines = db.query(Pipeline).filter(
    Pipeline.company_name == '恒瑞医药'
).all()

print(f'Found {len(pipelines)} pipelines')
for p in pipelines:
    print(f'  {p.drug_code}: {p.indication} ({p.phase})')
db.close()
"
```

## 部署

### 1. 定时任务

使用 crontab 或 Celery Beat 定期运行爬虫：

```bash
# 每天凌晨 2 点运行所有爬虫
0 2 * * * cd /path/to/back_end && python scripts/run_crawler.py --all
```

### 2. 容器化

Dockerfile 示例：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "scripts/run_crawler.py", "--all"]
```

## 最佳实践

### 1. 遵守 robots.txt

```python
# 检查 robots.txt
import requests
from urllib.robotparser import RobotFileParser

rp = RobotFileParser()
rp.set_url("https://www.example.com/robots.txt")
rp.read()

if rp.can_fetch("MyCrawler", "/pipeline"):
    # 可以爬取
    pass
```

### 2. 速率限制

```python
# 基类已实现速率限制（0.3-0.5 秒）
time.sleep(CrawlerConfig.MIN_DELAY)  # 0.3 秒
```

### 3. 错误处理

```python
try:
    response = self.fetch_page(url)
    if not response:
        self.stats.add_failed(f"Failed to fetch: {url}")
        return
except Exception as e:
    logger.error(f"Error fetching {url}: {e}")
    self.stats.add_failed(f"Error: {e}")
```

### 4. 日志记录

```python
logger.info(f"Fetching: {url}")
logger.debug(f"Parsed {len(pipelines)} pipelines")
logger.warning(f"Missing required fields: {drug_code}")
logger.error(f"Error parsing item: {e}")
```

### 5. 数据验证

```python
# 验证必填字段
if not drug_code or not indication or not phase:
    logger.warning(f"Missing required fields")
    return None

# 验证数据长度
if len(drug_code) > 100:
    logger.warning(f"Drug code too long: {drug_code}")
    return None
```

### 6. 增量更新

```python
# 基类已实现增量更新
# 如果管线已存在，只更新 last_seen_at
existing = db.query(Pipeline).filter(
    Pipeline.drug_code == item.drug_code,
    Pipeline.company_name == item.company_name,
).first()

if existing:
    existing.last_seen_at = datetime.utcnow()
    db.commit()
```

### 7. User-Agent 轮换

```python
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]

self.session.headers.update({
    "User-Agent": random.choice(USER_AGENTS)
})
```

## 常见问题

### Q1: 如何处理 JavaScript 渲染的页面？

**A**: 使用 Playwright 或 Selenium：

```bash
pip install playwright
playwright install chromium
```

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.example.com/pipeline")
    html = page.content()
    browser.close()
```

### Q2: 如何处理分页？

**A**: 循环处理所有页面：

```python
def parse_pipeline_page(self, html: str) -> List[PipelineDataItem]:
    soup = self.parse_html(html)
    pipelines = []

    # 处理当前页
    pipelines.extend(self.parse_current_page(soup))

    # 查找下一页链接
    next_page = soup.find("a", class_="next-page")
    if next_page:
        next_url = self.base_url + next_page["href"]
        response = self.fetch_page(next_url)
        pipelines.extend(self.parse_pipeline_page(response.text))

    return pipelines
```

### Q3: 如何处理登录？

**A**: 使用 Session 保持登录状态：

```python
# 登录
login_data = {
    "username": "your_username",
    "password": "your_password",
}
response = self.session.post(
    "https://www.example.com/login",
    data=login_data
)

# 访问需要登录的页面
response = self.session.get("https://www.example.com/pipeline")
```

### Q4: 如何调试解析逻辑？

**A**: 保存 HTML 到文件：

```python
with open("debug.html", "w", encoding="utf-8") as f:
    f.write(response.text)

# 然后用浏览器打开 debug.html 查看
```

## 参考资料

- [BeautifulSoup 文档](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [requests 文档](https://requests.readthedocs.io/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [robots.txt 标准](https://www.robotstxt.org/)

## 版本历史

- v1.0.0 (2025-02-01): 初始版本
  - ✅ 基础爬虫框架
  - ✅ 恒瑞医药爬虫
  - ✅ 网站分析工具
  - ✅ 阶段标准化
