# CDE Spider Playwright 实施指南

## 实施日期
2026-02-04

## 问题背景

CDE 网站使用 JavaScript 动态渲染 + 反爬虫机制，普通的 HTTP 请求无法获取数据：
- 返回 202 状态码
- 内容为混淆的 JavaScript 代码
- 数据通过 JS 动态加载

---

## 解决方案

使用 **Playwright** 浏览器自动化工具来获取渲染后的页面内容。

---

## 实施步骤

### 步骤 1: 安装 Playwright

```bash
# 安装 Playwright Python 包
pip install playwright

# 安装浏览器驱动
playwright install chromium
```

**预计时间**: 5-10 分钟（取决于网络速度）

### 步骤 2: 验证安装

```bash
# 测试 Playwright 是否安装成功
python -c "from playwright.sync_api import sync_playwright; print('Playwright installed successfully')"
```

### 步骤 3: 运行测试

```bash
cd D:\26初寒假实习\A_lxl_search\code\back_end
python test_cde_playwright.py
```

---

## 新文件说明

### 1. `crawlers/cde_spider_playwright.py`
Playwright 版本的 CDE 爬虫

**关键特性**：
- 使用异步 Playwright API
- 自动等待页面加载完成
- 支持 JavaScript 渲染
- 保留原有解析逻辑

**主要方法**：
```python
async def fetch_event_list(page, list_url)
async def fetch_event_detail(page, detail_url)
async def _run_async(crawler_run_id)
```

### 2. `test_cde_playwright.py`
Playwright 版本的测试脚本

**功能**：
- 测试爬虫功能
- 统计新增数据
- 显示最新事件

---

## 使用说明

### 基本使用

```python
from crawlers.cde_spider_playwright import CDESpiderPlaywright

# 创建爬虫实例
spider = CDESpiderPlaywright()

# 运行爬虫
stats = spider.run()

# 查看统计
print(stats.to_dict())
```

### 配置选项

在 `config.py` 中已有配置：
```python
CDE_CRAWLER_ENABLED = True
CDE_CRAWLER_BASE_URL = "https://www.cde.org.cn"
CDE_CRAWLER_INFO_URL = "https://www.cde.org.cn/main/xxgk/"
CDE_CRAWLER_INTERVAL_HOURS = 12
CDE_CRAWLER_RATE_LIMIT = 0.3  # QPS
```

---

## 技术细节

### Playwright 工作原理

1. **启动无头浏览器**: `browser = await p.chromium.launch(headless=True)`
2. **创建新页面**: `page = await browser.new_page()`
3. **访问 URL**: `await page.goto(url, wait_until="networkidle")`
4. **等待元素加载**: `await page.wait_for_selector('table')`
5. **获取 HTML**: `html = await page.content()`
6. **使用 BeautifulSoup 解析**: `soup = BeautifulSoup(html, 'html.parser')`

### 异步处理

由于 Playwright 使用异步 API，主运行方法需要包装：

```python
def run(self):
    asyncio.run(self._run_async(crawler_run_id))

async def _run_async(self, crawler_run_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # ... 爬取逻辑
        await browser.close()
```

---

## 对比：原版 vs Playwright 版

| 特性 | 原版 (requests + BS4) | Playwright 版 |
|------|----------------------|--------------|
| 获取静态 HTML | ✅ | ✅ |
| 执行 JavaScript | ❌ | ✅ |
| 处理动态内容 | ❌ | ✅ |
| 速度 | 快 | 慢 |
| 资源消耗 | 低 | 高 |
| 反爬虫绕过 | 弱 | 强 |

---

## 调试技巧

### 1. 查看 Playwright 操作

非无头模式运行（可以看到浏览器操作）：
```python
browser = await p.chromium.launch(headless=False)
```

### 2. 保存调试页面

代码已包含自动保存功能：
```python
debug_file = "debug_playwright_page.html"
with open(debug_file, 'w', encoding='utf-8') as f:
    f.write(html_content)
```

### 3. 截图功能

添加截图代码调试：
```python
await page.screenshot(path="debug_screenshot.png")
```

---

## 常见问题

### Q1: Playwright 安装失败
**解决方案**：
```bash
# 使用国内镜像
pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
playwright install chromium --with-deps
```

### Q2: 浏览器下载失败
**解决方案**：
```bash
# 手动下载浏览器
playwright install
```

### Q3: 仍然获取不到数据
**可能原因**：
1. 网站结构变化
2. 需要登录/验证码
3. API 接口变化

**解决方案**：
1. 手动访问网站确认结构
2. 查找 API 接口
3. 考虑使用其他数据源

---

## 性能优化

### 1. 减少等待时间
```python
# 使用更精确的等待条件
await page.wait_for_selector('table tbody tr')
```

### 2. 并发处理
```python
# 同时启动多个浏览器实例
tasks = [process_url(url) for url in urls]
await asyncio.gather(*tasks)
```

### 3. 缓存机制
```python
# 缓存已访问的页面
if url not in cache:
    cache[url] = await fetch_page(url)
```

---

## 后续改进

### 短期（1周内）
- [ ] 完成 Playwright 安装
- [ ] 测试爬虫功能
- [ ] 验证数据入库
- [ ] 性能调优

### 中期（1个月内）
- [ ] 添加更多列表页 URL
- [ ] 实现增量更新优化
- [ ] 添加错误重试机制
- [ ] 完善监控告警

### 长期（持续）
- [ ] 寻找官方 API
- [ ] 考虑使用第三方数据源
- [ ] 实现分布式爬取
- [ ] 添加数据验证和清洗

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `crawlers/cde_spider_playwright.py` | Playwright 版爬虫实现 |
| `test_cde_playwright.py` | 测试脚本 |
| `docs/CDE_Spider_Test_Report.md` | 测试报告 |
| `docs/CDE_Spider_Implementation_Summary.md` | 实现总结 |

---

## 总结

✅ **已准备**：
- Playwright 版本代码已实现
- 测试脚本已准备
- 文档已完善

⏳ **待完成**：
- Playwright 安装（进行中）
- 功能测试
- 数据验证

🎯 **下一步**：
等待 Playwright 安装完成后，运行测试脚本验证功能。
