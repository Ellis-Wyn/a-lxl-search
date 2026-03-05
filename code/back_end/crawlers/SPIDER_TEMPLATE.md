# 药企爬虫开发模板

## 快速开始

### 1. 文件结构

```
crawlers/
├── base_spider.py         # 基类（不要修改）
├── __init__.py            # 自动发现机制（不要修改）
├── runner.py              # 总控制程序（不要修改）
├── hengrui_spider.py      # 恒瑞医药爬虫
├── beigene_spider.py      # 百济神州爬虫
└── {company}_spider.py    # 新爬虫文件
```

### 2. 爬虫模板

```python
"""
=====================================================
{公司名称}官网爬虫
=====================================================

从{公司名称}官网爬取管线数据：
- 官网：https://www.example.com
- 管线页面：https://www.example.com/pipeline

数据字段：
- 药物代码（drug_code）
- 适应症（indication）
- 研发阶段（phase）
- 药物类型（modality）

注意：
- 遵守 robots.txt
- 速率限制（0.3-0.5 QPS）
- 必须保留 source_url
=====================================================
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup, Tag

# ⚠️ 必须导入的模块
from crawlers.base_spider import (
    CompanySpiderBase,
    PipelineDataItem,
    CrawlerStats,
    spider_register,
)
from core.logger import get_logger

# ⚠️ 甲方三大需求：必须导入这两个检测器
from utils.pipeline_parser import DiscontinuationDetector, CombinationTherapyDetector

logger = get_logger(__name__)


# 使用装饰器注册爬虫（公司标识，英文小写）
@spider_register("company_id")
class CompanySpider(CompanySpiderBase):
    """
    {公司名称}爬虫

    官网：https://www.example.com
    """

    def __init__(self):
        super().__init__()
        self.name = "{公司中文名}"
        self.company_name = "{公司中文名}"  # 入库时使用的公司名称
        self.base_url = "https://www.example.com"

        # 管线页面 URL
        self.pipeline_url = "https://www.example.com/pipeline"

    def run(self) -> CrawlerStats:
        """
        运行爬虫

        Returns:
            爬虫统计信息
        """
        logger.info(f"Starting {self.name} spider...")

        # 1. 获取管线页面
        logger.info(f"Fetching: {self.pipeline_url}")
        response = self.fetch_page(self.pipeline_url)

        if not response:
            self.stats.add_failed(f"Failed to fetch: {self.pipeline_url}")
            return self.stats

        # 2. 解析管线数据
        pipelines = self.parse_pipeline_page(response.text)
        logger.info(f"Parsed {len(pipelines)} pipelines from page")

        # 3. 收集本次看到的药物代码（用于竞品退场检测）
        seen_drug_codes = []

        # 4. 入库
        for item in pipelines:
            seen_drug_codes.append(item.drug_code)

            # ⚠️ 甲方需求1：检测终止关键词
            if DiscontinuationDetector.is_discontinued(item.indication):
                item.status = 'discontinued'
                logger.warning(f"Pipeline {item.drug_code} is discontinued")

            success = self.save_to_database(item)
            if success:
                self.stats.add_success()
            else:
                self.stats.add_failed(f"Failed to save: {item.drug_code}")

        # ⚠️ 甲方需求3：检测消失的管线（竞品退场）
        disappeared = self.check_discontinued_pipelines(seen_drug_codes)

        if disappeared:
            logger.warning(f"Detected {len(disappeared)} disappeared pipelines")

        # 输出性能指标
        metrics = self.get_metrics()
        logger.info(f"Spider completed. Stats: {self.stats.to_dict()}")
        logger.info(f"Performance: {metrics}")

        return self.stats

    def parse_pipeline_page(self, html: str) -> List[PipelineDataItem]:
        """
        解析管线页面

        Args:
            html: 页面 HTML 内容

        Returns:
            管线数据列表
        """
        pipelines = []

        # TODO: 根据官网实际HTML结构编写解析逻辑
        # 示例：使用正则表达式提取管线项目
        pattern = r'<li[^>]*class="pipeline-item[^"]*"[^>]*>(.*?)</li>'
        matches = re.findall(pattern, html, re.DOTALL)

        for match in matches:
            try:
                # 使用 BeautifulSoup 解析单个项目
                item_soup = self.parse_html(match)

                # 提取药物代码
                drug_code_elem = item_soup.find('span', class_='drug-code')
                drug_code = drug_code_elem.text.strip() if drug_code_elem else ''
                if not drug_code:
                    continue

                # 提取适应症
                indication_elem = item_soup.find('span', class_='indication')
                indication_text = indication_elem.text.strip() if indication_elem else ''

                # ⚠️ 甲方需求1：检测联合用药
                is_combination, combination_drugs = CombinationTherapyDetector.detect_combination(
                    indication_text,
                    [drug_code]
                )

                # 清理适应症文本（移除"联合"等治疗方式信息）
                # 因为已经在 is_combination 中标记了
                import re
                indication = re.sub(r'\s*\+\s*', ' ', indication_text)
                indication = indication.replace('单药', '').replace('联合', '').strip()

                # 提取阶段
                phase_elem = item_soup.find('span', class_='phase')
                phase = phase_elem.text.strip() if phase_elem else ''

                # 创建数据项
                pipeline_data = PipelineDataItem(
                    drug_code=drug_code,
                    company_name=self.company_name,
                    indication=indication,
                    phase=phase,  # 原始阶段，save_to_database 会自动标准化
                    source_url=self.pipeline_url,
                    is_combination=is_combination,       # ⚠️ 甲方需求1
                    combination_drugs=combination_drugs  # ⚠️ 甲方需求1
                )

                pipelines.append(pipeline_data)

            except Exception as e:
                logger.error(f"Error parsing pipeline item: {e}")
                continue

        logger.info(f"Parsed {len(pipelines)} pipelines")
        return pipelines


__all__ = ["CompanySpider"]
```

---

## 必须导入的模块清单

### 基础模块（所有爬虫都需要）

```python
from crawlers.base_spider import (
    CompanySpiderBase,      # 基类
    PipelineDataItem,       # 数据模型
    CrawlerStats,           # 统计信息
    spider_register,        # 装饰器
)
from core.logger import get_logger
```

### 甲方三大需求模块（⚠️ 不要遗漏！）

```python
from utils.pipeline_parser import (
    DiscontinuationDetector,      # 终止检测器（竞品退场）
    CombinationTherapyDetector,   # 联合用药检测器
)
```

---

## 甲方三大需求实现说明

### 需求1：联合用药识别

**实现类**：`CombinationTherapyDetector`

**检测模式**：
- `+` 加号：`Drug A + Drug B`
- `in combination with/of`
- `plus`、`&`
- 中文：`联合`、`联用`、`合用`

**使用方法**：
```python
is_combination, combination_drugs = CombinationTherapyDetector.detect_combination(
    text,           # 待检测文本（indication或description）
    [drug_code]     # 已知药物列表（会过滤掉主药）
)

# 返回：
# is_combination: bool - 是否联合用药
# combination_drugs: List[str] - 联合药物代码列表
```

**入库字段**：
```python
PipelineDataItem(
    ...
    is_combination=is_combination,       # 标记是否联合用药
    combination_drugs=combination_drugs  # 联合药物列表
)
```

---

### 需求2：适应症区分

**实现方式**：数据库唯一主键

```python
# 在 base_spider.py 的 save_to_database() 中
# 使用 (drug_code, company_name, indication) 作为唯一键
existing = db.query(Pipeline).filter(
    Pipeline.drug_code == item.drug_code,
    Pipeline.company_name == item.company_name,
    Pipeline.indication == item.indication,  # ⚠️ 不同适应症会创建独立记录
).first()
```

**开发者只需要**：
- 确保 `indication` 字段准确提取
- 同一药物的不同适应症会自动创建独立记录

---

### 需求3：竞品退场预警

**实现方式**：对比两次爬取结果

**步骤1**：在 `run()` 中收集本次爬取的药物代码
```python
seen_drug_codes = []
for item in pipelines:
    seen_drug_codes.append(item.drug_code)
    ...
```

**步骤2**：调用基类方法检测消失管线
```python
disappeared = self.check_discontinued_pipelines(seen_drug_codes)

if disappeared:
    logger.warning(f"Detected {len(disappeared)} disappeared pipelines")
```

**自动完成**：
- 对比数据库中该公司所有活跃管线
- 找出本次未爬取到的管线
- 自动标记为 `discontinued` 状态
- 记录 `discontinued_at` 时间
- 发送预警通知（如果配置了）

---

## 爬虫装饰器注册

```python
# 使用装饰器注册爬虫（英文小写的公司标识）
@spider_register("company_id")
class CompanySpider(CompanySpiderBase):
    ...
```

**注意事项**：
- `spider_register` 的参数是**爬虫标识**（英文小写）
- 用于命令行调用：`python -m crawlers.runner --spider company_id`
- `company_name` 属性是**入库时使用的公司名称**（中文）

---

## 命令行使用

```bash
# 列出所有爬虫
python -m crawlers.runner --list

# 运行单个爬虫
python -m crawlers.runner --spider hengrui

# 运行所有爬虫
python -m crawlers.runner --all
```

---

## 基类提供的方法

### HTTP 请求
```python
response = self.fetch_page(url, timeout=30, use_cache=True)
```

### HTML 解析
```python
soup = self.parse_html(html)
```

### 阶段标准化（自动调用）
```python
phase_normalized = self.normalize_phase(raw_phase)
# 支持60+种中英文阶段表示
# 例如：Ⅲ期 → Phase 3
```

### 数据库入库
```python
success = self.save_to_database(item)
# 自动：MoA识别、临床数据提取、Phase标准化、去重
```

### 竞品退场检测
```python
disappeared = self.check_discontinued_pipelines(seen_drug_codes)
# 返回消失的药物代码列表
```

### 性能指标
```python
metrics = self.get_metrics()
# 返回：请求数、成功率、平均响应时间、缓存命中率、熔断器状态
```

---

## 配置常量（CrawlerConfig）

| 配置项 | 默认值 | 说明 |
|-------|-------|------|
| MIN_DELAY | 0.3s | 最小请求延迟 |
| MAX_DELAY | 0.5s | 最大请求延迟 |
| DEFAULT_TIMEOUT | 30s | 请求超时时间 |
| DEFAULT_RETRY | 3 | 重试次数 |
| CACHE_TTL | 3600s | 缓存有效期（1小时） |
| CIRCUIT_BREAKER_THRESHOLD | 5 | 熔断器阈值（连续失败次数） |

---

## 常见问题

### Q1: 如何调试爬虫？

```python
# 在 run() 方法中添加断点或日志
logger.info(f"HTML length: {len(response.text)}")
logger.debug(f"Matched items: {len(matches)}")
```

### Q2: 如何处理动态加载的页面？

如果页面使用 JavaScript 动态加载内容：
1. 查看是否有 JSON API 接口
2. 使用 Selenium 或 Playwright
3. 手动配置备用数据（参考 `HengruiManualSpider`）

### Q3: 如何处理解析失败的情况？

```python
try:
    # 解析逻辑
    ...
except Exception as e:
    logger.error(f"Error parsing pipeline item: {e}")
    continue  # 跳过当前项目，继续处理下一个
```

### Q4: 如何验证爬取的数据？

```bash
# 运行爬虫
python -m crawlers.runner --spider company_id

# 查看统计信息
# 输出示例：
#   请求总数: 10
#   成功请求: 10
#   获取条目: 50
#   成功条目: 48
#   失败条目: 2
```

---

## 开发检查清单

开发新爬虫时，确保完成以下检查：

- [ ] 导入了 `DiscontinuationDetector` 和 `CombinationTherapyDetector`
- [ ] 使用 `@spider_register()` 装饰器注册爬虫
- [ ] 实现了 `run()` 方法
- [ ] 实现了 `parse_pipeline_page()` 方法
- [ ] 调用 `CombinationTherapyDetector.detect_combination()` 检测联合用药
- [ ] 调用 `DiscontinuationDetector.is_discontinued()` 检测终止状态
- [ ] 调用 `check_discontinued_pipelines()` 检测竞品退场
- [ ] 设置了 `source_url` 保留数据来源
- [ ] 遵守了速率限制（0.3-0.5 QPS）

---

*最后更新：2026-02-03*
