# 数据库集成快速启动指南

## 概述

本项目已完成数据库集成，可以端到端运行。以下是快速启动步骤。

---

## 前置条件

### 1. 安装 PostgreSQL

**Windows:**
```bash
# 下载安装包
https://www.postgresql.org/download/windows/

# 或使用 Chocolatey
choco install postgresql
```

**Mac:**
```bash
# 使用 Homebrew
brew install postgresql@14
brew services start postgresql@14
```

**Linux (Ubuntu):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. 创建数据库

```bash
# 进入 PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE drug_intelligence_db;

# 创建用户（可选）
CREATE USER drug_intelligence_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE drug_intelligence_db TO drug_intelligence_user;

# 退出
\q
```

### 3. 配置 .env 文件

在 `code/back_end/` 目录下创建 `.env` 文件：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=drug_intelligence_db
DB_USER=postgres
DB_PASSWORD=your_password

# PubMed API（可选，提升速率限制）
PUBMED_API_KEY=
PUBMED_EMAIL=your_email@example.com
```

---

## 启动步骤

### 步骤 1: 初始化数据库

```bash
cd code/back_end
python scripts/init_db.py
```

**输出示例：**
```
✓ 数据库连接正常
✓ 所有表创建成功
✓ 成功插入 6 条靶点数据
✓ 数据验证通过
```

### 步骤 2: 运行端到端测试

```bash
python tests/test_e2e.py
```

**测试内容：**
- ✓ 数据库 CRUD 操作
- ✓ PubMed API 集成
- ✓ Pipeline 变化检测
- ✓ Target-Publication/Pipeline 关联

### 步骤 3: 启动 API 服务

```bash
python main.py
```

**访问 API 文档：**
```
http://localhost:8000/docs
```

---

## 验证清单

### 数据库检查

```bash
# 连接数据库
psql -U postgres -d drug_intelligence_db

# 查看表
\dt

# 查看靶点数据
SELECT standard_name, category FROM target;

# 查看管线数据
SELECT drug_code, company_name, phase FROM pipeline;

# 退出
\q
```

### API 检查

```bash
# 健康检查
curl http://localhost:8000/health

# 查询靶点
curl http://localhost:8000/api/example/target/EGFR

# 搜索文献
curl -X POST http://localhost:8000/api/pubmed/search \
  -H "Content-Type: application/json" \
  -d '{"target_name": "EGFR", "max_results": 5}'
```

---

## 项目结构

```
code/back_end/
├── scripts/
│   └── init_db.py              # 数据库初始化脚本
├── tests/
│   ├── test_e2e.py             # 端到端测试
│   ├── test_pubmed.py          # PubMed 模块测试
│   └── test_pipeline.py        # Pipeline 模块测试
├── services/
│   ├── database_service.py     # 数据库操作服务（新增）
│   ├── pubmed_service.py       # PubMed 服务
│   └── pipeline_service.py     # Pipeline 服务
├── api/
│   ├── pubmed.py               # PubMed API
│   └── pipeline.py             # Pipeline API
├── models/                     # ORM 模型
├── main.py                     # 应用入口
└── .env                        # 环境配置
```

---

## 常见问题

### Q1: 数据库连接失败

**错误：** `could not connect to server`

**解决：**
1. 检查 PostgreSQL 是否启动
2. 检查端口 5432 是否被占用
3. 检查用户名密码是否正确

```bash
# Windows: 检查服务
sc query postgresql-x64-14

# Linux/Mac: 检查进程
ps aux | grep postgres
```

### Q2: 表已存在错误

**错误：** `relation "target" already exists`

**解决：** 这是正常的，说明表已创建。继续下一步即可。

### Q3: PubMed API 限流

**错误：** `Rate limit exceeded`

**解决：**
1. 获取 NCBI API Key：https://www.ncbi.nlm.nih.gov/account/
2. 在 `.env` 文件中配置 `PUBMED_API_KEY`

---

## 下一步

### 选项 A: 实现 1-2 家公司爬虫

快速验证系统价值：
1. 分析恒瑞/百济官网结构
2. 实现数据提取逻辑
3. 运行爬虫并查看 Phase Jump 预警

### 选项 B: 完善 API 功能

添加更多接口：
1. 靶点 CRUD 接口
2. 数据导出功能
3. 定时任务配置

### 选项 C: 优化数据质量

提升数据准确性：
1. 公司名称归一化
2. Phase 映射优化
3. 多源交叉验证

---

## 技术支持

遇到问题？查看日志：
```bash
tail -f logs/app.log
```

---

*最后更新：2026-02-01*
