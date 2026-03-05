# CDE Spider 实现总结

## 实施日期
2026-02-04

## 实施内容
完成了 CDE（药审中心）爬虫的核心 HTML 解析逻辑实现，包括：
1. `fetch_event_list()` - 列表页解析
2. `fetch_event_detail()` - 详情页解析
3. `_parse_acceptance_no_type()` - 受理号类型解析
4. 配置更新 - 实际 CDE URL

---

## 修改的文件

### 1. `crawlers/cde_spider.py`

#### 1.1 更新 `list_page_urls` (line 83-91)
```python
# 更新前：TODO 示例 URL
self.list_page_urls = [
    f"{self.base_url}/main/xxgk/listPage/xxxxxxxx",
]

# 更新后：实际 CDE URL
self.list_page_urls = [
    "https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d",
]
```

#### 1.2 实现 `fetch_event_list()` (line 166-282)
**功能**：
- 从 CDE 列表页提取事件数据
- 支持分页遍历（最多100页）
- 解析表格结构（7列数据）
- 提取受理号链接

**解析逻辑**：
```python
# 表格结构
序号 | 受理号 | 药品名称 | 药品类型 | 申请类型 | 注册分类 | 企业名称 | 承办日期
```

**关键特性**：
- 自动分页处理
- 日期格式验证
- 速率限制遵守
- 详细的错误日志

#### 1.3 实现 `fetch_event_detail()` (line 284-395)
**功能**：
- 从详情页提取额外信息
- 支持多种 HTML 选择器（容错性强）
- 提取所有附件 URL（PDF、图片等）

**提取字段**：
- `indication` - 适应症
- `review_status` - 审评状态
- `acceptance_date` - 受理日期
- `public_date` - 公示日期
- `attachment_urls` - 附件列表

**选择器策略**：
- 使用多个备选选择器提高成功率
- 支持表格和 div 两种布局

#### 1.4 实现 `_parse_acceptance_no_type()` (line 555-618)
**功能**：从受理号和申请类型解析事件类型

**受理号编码规则**：
| 前缀 | 含义 | 事件类型 |
|------|------|----------|
| CXSL | 化药临床试验 | IND |
| CXHS | 化药新药 | IND |
| CYHS | 化药仿制 | NDA |
| JXHB | 化药补充申请 | 补充资料 |
| S* | 生物制品 | CTA/BLA |
| Z* | 中药 | IND/NDA |

---

### 2. `tests/test_cde_parsing.py` (新建)

**测试内容**：
1. 受理号解析测试（4个测试用例）
2. CDEEventData 创建测试
3. URL 配置验证
4. 编码规则说明

**测试结果**：全部通过

---

## 验证结果

### 测试 1: 基础实现验证 (`tests/test_cde_simple.py`)
```
[OK] CDEEvent model imported
[OK] CDESpider and CDEEventData imported
[OK] UnifiedSearchService imported
[OK] CDE and Search routers imported
[OK] All CDE configs exist
[OK] CDEEventData instance created
[OK] create_cde_event factory function works
```

### 测试 2: 解析逻辑验证 (`tests/test_cde_parsing.py`)
```
[OK] CXHS2600023 + 新药 -> IND
[OK] JXHB2600014 + 补充申请 -> 补充资料
[OK] CYHS2600368 + 仿制 -> NDA
[OK] CXSL2400001 + 新药 -> IND
```

---

## 数据流

```
CDE 网站 (https://www.cde.org.cn/main/xxgk/listpage/...)
    ↓
fetch_event_list()
    ↓ 解析表格
CDEEventData 对象
    ↓
fetch_event_detail()
    ↓ 提取额外信息
更新 CDEEventData
    ↓
save_to_database()
    ↓
CDEEvent ORM 表
```

---

## 下一步

### 1. 数据库初始化
```bash
cd D:\26初寒假实习\A_lxl_search\code\back_end
python scripts/init_db.py
```

### 2. 手动测试爬虫
```python
from crawlers.cde_spider import CDESpider
spider = CDESpider()
stats = spider.run()
print(stats.to_dict())
```

### 3. 检查数据库
```sql
SELECT COUNT(*) FROM cde_events;
SELECT * FROM cde_events ORDER BY undertake_date DESC LIMIT 10;
```

### 4. 测试 API
```bash
# 启动服务
python main.py

# 测试查询
curl "http://localhost:8000/api/cde/events?limit=10"

# 测试统计
curl "http://localhost:8000/api/cde/events/stats"
```

### 5. 查看文档
访问 http://localhost:8000/docs

---

## 注意事项

### 1. 反爬虫策略
- 严格遵守速率限制（0.3 QPS）
- 使用 User-Agent 轮换
- 遵守 robots.txt

### 2. 错误处理
- 如果某个页面解析失败，继续处理其他页面
- 所有错误都记录到日志
- 返回空数据而不是抛出异常

### 3. 增量更新
- 基于 `acceptance_no` 唯一约束
- 更新 `last_seen_at` 时间戳
- 合并 `source_urls` 去重

---

## 附录：CDE 网站结构

### 列表页 URL
```
https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d
```

### 表格结构
```html
<table class="table">
  <tr>
    <th>序号</th>
    <th>受理号</th>
    <th>药品名称</th>
    <th>药品类型</th>
    <th>申请类型</th>
    <th>注册分类</th>
    <th>企业名称</th>
    <th>承办日期</th>
  </tr>
  <tr>
    <td>1</td>
    <td><a href="...">JXHB2600014</a></td>
    <td>Ulixacaltamide缓释片</td>
    <td>化药</td>
    <td>补充申请</td>
    <td>1</td>
    <td>Praxis Precision Medicines</td>
    <td>2026-02-04</td>
  </tr>
  ...
</table>
```

### 示例数据
- 受理号: `CXHS2600023`
- 药品名称: `HR091506片`
- 药品类型: `化药`
- 申请类型: `新药`
- 注册分类: `2.2`
- 企业名称: `江苏恒瑞医药股份有限公司`
- 承办日期: `2026-02-04`

---

## 总结

✅ **已完成**：
- CDE Spider 核心解析逻辑实现
- 受理号编码规则解析
- 列表页分页支持
- 详情页多选择器容错
- 单元测试验证

🚀 **可用性**：
- 代码已可直接运行
- 支持增量更新
- 完善的错误处理
- 详细的日志记录

📋 **待验证**：
- 实际网站爬取（需要网络连接）
- 数据完整性验证
- 性能测试（1851条记录）
- API 端到端测试
