# 快速启动指南

## 📋 前置条件

1. **Python 3.10+**
2. **PostgreSQL 14+**
3. **Git**（可选）

---

## 🚀 启动步骤

### 第1步：安装 PostgreSQL

**Windows**：
- 下载：https://www.postgresql.org/download/windows/
- 安装时记住设置的密码（默认用户名：postgres）

**验证安装**：
```bash
psql --version
```

---

### 第2步：创建数据库

打开 PostgreSQL 命令行或使用 pgAdmin：

```sql
-- 创建数据库
CREATE DATABASE drug_intelligence_db;

-- 创建用户（可选）
CREATE USER drug_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE drug_intelligence_db TO drug_user;
```

---

### 第3步：创建虚拟环境

```bash
# 进入项目目录
cd D:\26初寒假实习\A_lxl_search\code\back_end

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
Windows: venv\Scripts\activate
Linux/Mac: source venv/bin/activate
```

---

### 第4步：安装依赖

```bash
pip install -r requirements.txt
```

**如果安装失败**（网络问题），使用国内镜像：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 第5步：配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写数据库密码等信息
# notepad .env  (Windows)
# vim .env     (Linux/Mac)
```

**必填项**：
```
DB_PASSWORD=your_postgres_password
PUBMED_EMAIL=your_email@example.com
```

---

### 第6步：初始化数据库

**方式 A：使用 SQL 脚本（推荐）**

```bash
psql -U postgres -d drug_intelligence_db -f ../../database/migrations/001_create_initial_tables.sql
```

**方式 B：使用 ORM（开发环境）**

```python
# 在 Python 中执行
from utils.database import init_database
init_database()
```

---

### 第7步：启动 FastAPI

```bash
# 方式 A：直接运行
python main.py

# 方式 B：使用 uvicorn
uvicorn main:app --reload

# 方式 C：指定端口
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

看到以下输出表示成功：
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started server process [xxxxx]
🚀 病理AI药研情报库启动中...
```

---

## ✅ 验证安装

### 1. 访问 API 文档
浏览器打开：
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

### 2. 测试健康检查
```bash
curl http://localhost:8000/health
```

或访问：http://localhost:8000/health

### 3. 测试示例接口
```bash
curl http://localhost:8000/api/example/target/EGFR
```

---

## 📂 目录结构

```
code/back_end/
├── main.py                 # FastAPI 入口
├── config.py               # 配置文件
├── requirements.txt        # Python 依赖
├── .env                    # 环境变量（不要提交到 Git）
├── .env.example            # 环境变量模板
├── .gitignore             # Git 忽略文件
│
├── api/                   # API 路由
│   ├── __init__.py
│   ├── targets.py         # 靶点接口（待实现）
│   ├── publications.py    # 文献接口（待实现）
│   └── pipelines.py       # 管线接口（待实现）
│
├── models/                # 数据模型（ORM）
│   ├── __init__.py
│   ├── target.py          # Target 模型（待实现）
│   ├── publication.py     # Publication 模型（待实现）
│   └── pipeline.py        # Pipeline 模型（待实现）
│
├── crawlers/              # 爬虫模块
│   ├── __init__.py
│   ├── pubmed_crawler.py  # PubMed 爬虫（待实现）
│   └── company_pipeline.py # 药企爬虫（待实现）
│
├── services/              # 业务逻辑
│   ├── __init__.py
│   └── pubmed_service.py  # PubMed 查询服务（待实现）
│
└── utils/                 # 工具函数
    ├── __init__.py
    ├── database.py        # 数据库连接 ✅
    └── normalizers.py     # 数据归一化（待实现）
```

---

## 🐛 常见问题

### 问题 1：psql 命令不存在
**解决**：将 PostgreSQL 的 bin 目录添加到系统 PATH
- Windows：`C:\Program Files\PostgreSQL\15\bin`

### 问题 2：数据库连接失败
**检查**：
1. PostgreSQL 服务是否启动
2. .env 中的用户名密码是否正确
3. 数据库是否已创建

### 问题 3：依赖安装失败
**解决**：升级 pip
```bash
python -m pip install --upgrade pip
```

### 问题 4：端口 8000 被占用
**解决**：更换端口
```bash
uvicorn main:app --port 8001
```

---

## 📖 下一步

1. **测试数据库连接**
   ```bash
   python -c "from utils.database import check_database_connection; check_database_connection()"
   ```

2. **开始实现第一个功能**
   - 创建 Target ORM 模型
   - 实现 PubMed 爬虫
   - 编写 API 接口

3. **查看项目文档**
   - `CLAUDE.md` - 项目记忆
   - `PROJECT_MINDMAP.md` - 思维导图
   - `../database/migrations/001_create_initial_tables.sql` - 数据库结构

---

**祝开发顺利！** 🎉
