# 文档目录

欢迎来到病理AI药研情报库系统文档中心！

## 📚 文档列表

### 架构文档
- **[架构文档](architecture.md)** - 系统整体架构、模块说明、数据流

### 使用文档
- **[API使用示例](api_examples.md)** - 完整的API请求/响应示例，包含Python客户端代码

### 部署文档
- **[部署和维护](deployment.md)** - 环境准备、部署流程、配置管理、常见问题

---

## 🚀 快速开始

### 我想要...

**了解系统架构**
→ 阅读 [架构文档](architecture.md)

**调用API接口**
→ 阅读 [API使用示例](api_examples.md)

**部署到生产环境**
→ 阅读 [部署和维护](deployment.md)

**运行测试**
→ 阅读 [测试文档](../tests/README.md)

**查看Phase 1改进**
→ 阅读 [完成报告](../PHASE1_COMPLETION_REPORT.md)

---

## 📋 文档结构

```
docs/
├── README.md              # 本文档
├── architecture.md        # 架构文档
├── api_examples.md        # API示例
└── deployment.md          # 部署文档
```

---

## 🔍 关键概念

### 核心实体

1. **Target（靶点）**
   - 标准名称、别名、Gene ID、UniProt ID
   - 与文献、管线的多对多关联

2. **Publication（文献）**
   - PubMed ID、标题、摘要、临床数据标签
   - 时效性评分算法

3. **Pipeline（管线）**
   - 药物代码、公司、适应症、阶段
   - Phase Jump检测、消失检测

### 服务层

- **DatabaseService** - 数据库CRUD操作
- **PubmedService** - PubMed智能查询
- **PhaseMapper** - 阶段标准化（30+种变体）

### 爬虫系统

- **CompanySpiderBase** - 爬虫基类
- **重试机制** - 指数退避 + 随机抖动
- **缓存** - TTL缓存减少重复请求
- **熔断器** - 失败率阈值保护

---

## 📖 阅读顺序建议

### 新手入门
1. [架构文档](architecture.md) - 了解整体架构
2. [API使用示例](api_examples.md) - 学习API调用
3. [部署文档](deployment.md#环境准备) - 准备开发环境

### 开发者
1. [架构文档](architecture.md) - 深入系统设计
2. [测试文档](../tests/README.md) - 编写测试
3. [API使用示例](api_examples.md) - 集成API

### 运维人员
1. [部署文档](deployment.md) - 生产部署
2. [架构文档](architecture.md#监控与日志) - 监控配置
3. [部署文档](deployment.md#维护操作) - 日常维护

---

## 📝 文档规范

### Markdown 格式
- 使用标准 Markdown 语法
- 代码块指定语言（\```python）
- 链接使用相对路径

### 代码示例
- 包含完整可运行的示例
- 添加注释说明
- 提供错误处理

### 更新频率
- 每次重大更新后同步文档
- 每月检查文档准确性
- 根据用户反馈改进

---

## 🔗 外部资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [pytest 文档](https://docs.pytest.org/)
- [PubMed API 文档](https://www.ncbi.nlm.nih.gov/books/NBK25501/)

---

## 💡 贡献指南

发现文档错误或有改进建议？

1. 编辑对应的 `.md` 文件
2. 更新文档底部的"最后更新"日期
3. 提交 Pull Request

---

**最后更新**: 2026-02-02
**文档维护**: Development Team
