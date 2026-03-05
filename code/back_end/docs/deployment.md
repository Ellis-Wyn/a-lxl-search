# 部署和维护文档

## 目录

- [环境准备](#环境准备)
- [开发环境部署](#开发环境部署)
- [生产环境部署](#生产环境部署)
- [配置管理](#配置管理)
- [日志和监控](#日志和监控)
- [常见问题](#常见问题)
- [维护操作](#维护操作)

---

## 环境准备

### 系统要求

- **操作系统**: Linux (Ubuntu 20.04+ 推荐) / Windows / macOS
- **Python**: 3.9+
- **数据库**: SQLite (开发) / PostgreSQL 13+ (生产)
- **内存**: 最低 2GB，推荐 4GB+
- **磁盘**: 最低 10GB，推荐 50GB+

### 依赖安装

```bash
# 克隆代码
git clone <repository_url>
cd back_end

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

---

## 开发环境部署

### 1. 配置环境变量

创建 `.env` 文件：

```bash
# 数据库配置
DATABASE_URL=sqlite:///./data/pharma_intelligence.db

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# PubMed配置
PUBMED_EMAIL=your-email@example.com
PUBMED_API_KEY=your_api_key_here  # 可选

# 爬虫配置
CRAWLER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
CRAWLER_TIMEOUT=30
CRAWLER_MIN_DELAY=0.3
CRAWLER_MAX_DELAY=0.5
CRAWLER_ENABLE_CACHE=True
CRAWLER_CACHE_TTL=3600
```

### 2. 初始化数据库

```bash
# 创建数据库表
python -c "from utils.database import init_database; init_database()"

# 或者使用 Alembic（如果配置了迁移）
alembic upgrade head
```

### 3. 启动开发服务器

```bash
# 方式1: 使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 方式2: 使用 FastAPI CLI
fastapi dev main.py

# 方式3: 使用 Python
python main.py
```

### 4. 验证部署

```bash
# 访问 API 文档
open http://localhost:8000/docs

# 健康检查
curl http://localhost:8000/api/pipeline/health

# 运行测试
pytest --cov=.
```

---

## 生产环境部署

### 1. 使用 Gunicorn + Nginx

#### 安装 Gunicorn

```bash
pip install gunicorn
```

#### 创建 Gunicorn 配置文件

`gunicorn.conf.py`:

```python
import multiprocessing

# 服务器socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker进程
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2

# 日志
accesslog = "/var/log/pharma_intelligence/access.log"
errorlog = "/var/log/pharma_intelligence/error.log"
loglevel = "info"

# 进程命名
proc_name = "pharma_intelligence"

# Daemon模式（可选）
daemon = False
pidfile = "/var/run/pharma_intelligence.pid"
umask = 0o007
```

#### 启动 Gunicorn

```bash
# 前台运行（测试）
gunicorn -c gunicorn.conf.py main:app

# 后台运行
gunicorn -c gunicorn.conf.py main:app --daemon

# 使用 systemd 管理（推荐）
sudo systemctl start pharma_intelligence
sudo systemctl enable pharma_intelligence
```

#### 配置 Nginx 反向代理

`/etc/nginx/sites-available/pharma_intelligence`:

```nginx
upstream pharma_intelligence {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;

    # 客户端最大请求体大小
    client_max_body_size 10M;

    # 日志
    access_log /var/log/nginx/pharma_intelligence_access.log;
    error_log /var/log/nginx/pharma_intelligence_error.log;

    # 静态文件（如果有）
    location /static {
        alias /var/www/pharma_intelligence/static;
        expires 30d;
    }

    # API代理
    location / {
        proxy_pass http://pharma_intelligence;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/pharma_intelligence /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. 使用 Docker

#### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/pharma
      - LOG_LEVEL=INFO
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=pharma
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
```

启动服务：

```bash
docker-compose up -d
```

---

## 配置管理

### 环境变量说明

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `DATABASE_URL` | 数据库连接URL | - | 是 |
| `API_HOST` | API监听地址 | 0.0.0.0 | 否 |
| `API_PORT` | API监听端口 | 8000 | 否 |
| `LOG_LEVEL` | 日志级别 | INFO | 否 |
| `PUBMED_EMAIL` | PubMed邮箱 | - | 是 |
| `PUBMED_API_KEY` | PubMed API密钥 | - | 否 |
| `CRAWLER_TIMEOUT` | 爬虫超时（秒） | 30 | 否 |
| `CRAWLER_ENABLE_CACHE` | 启用爬虫缓存 | True | 否 |

### 多环境配置

创建不同环境的配置文件：

```bash
configs/
├── development.py
├── testing.py
└── production.py
```

`configs/production.py`:

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "postgresql://user:pass@localhost/pharma"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False

    # 日志
    LOG_LEVEL: str = "WARNING"
    LOG_FILE: str = "/var/log/pharma_intelligence/app.log"

    # 爬虫
    CRAWLER_TIMEOUT: int = 30
    CRAWLER_ENABLE_CACHE: bool = True

    class Config:
        env_file = ".env.production"

settings = Settings()
```

使用配置：

```python
import sys
sys.path.insert(0, 'configs')

# 根据环境变量加载配置
ENV = os.getenv('ENV', 'development')
if ENV == 'production':
    from production import settings
elif ENV == 'testing':
    from testing import settings
else:
    from development import settings
```

---

## 日志和监控

### 日志配置

`core/logger.py` 已配置结构化日志：

```python
from core.logger import get_logger

logger = get_logger(__name__)

logger.info("Processing pipeline", extra={"drug_code": "SHR-1210"})
logger.error("Failed to fetch", exc_info=True)
```

### 日志级别

- `DEBUG`: 详细调试信息
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

### 日志文件

```
logs/
├── app.log          # 应用日志
├── error.log        # 错误日志
├── crawler.log      # 爬虫日志
└── api.log          # API访问日志
```

### 监控指标

#### 1. 爬虫性能监控

```python
# 爬虫统计信息
crawler_metrics = {
    "total_requests": 150,
    "successful_requests": 145,
    "failed_requests": 5,
    "success_rate": 96.7,
    "avg_response_time": 1.2,
    "pipelines_created": 37
}
```

#### 2. API性能监控

```python
# API端点性能
api_metrics = {
    "endpoint": "/api/v1/targets",
    "requests": 500,
    "avg_response_time": 0.15,
    "error_rate": 0.02,
    "status_codes": {
        "200": 450,
        "404": 40,
        "500": 10
    }
}
```

#### 3. 数据库性能监控

```python
# 数据库查询统计
db_metrics = {
    "total_queries": 1000,
    "avg_query_time": 0.05,
    "slow_queries": 5,
    "connections": 10
}
```

### 告警配置

使用钉钉或企业微信发送告警：

```python
def send_alert(message: str):
    """发送告警消息"""
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=xxx"

    data = {
        "msgtype": "text",
        "text": {
            "content": f"[Pharma Intelligence Alert] {message}"
        }
    }

    requests.post(webhook_url, json=data)
```

---

## 常见问题

### 1. 数据库连接失败

**问题**: `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file`

**解决方案**:
```bash
# 创建数据目录
mkdir -p data

# 检查文件权限
chmod 755 data/

# 检查 DATABASE_URL 路径是否正确
```

### 2. PubMed API 速率限制

**问题**: `429 Too Many Requests`

**解决方案**:
```bash
# 添加 API Key（提升速率限制）
PUBMED_API_KEY=your_api_key_here

# 增加延迟
CRAWLER_MIN_DELAY=1.0
CRAWLER_MAX_DELAY=2.0
```

### 3. 爬虫超时

**问题**: `requests.exceptions.Timeout`

**解决方案**:
```bash
# 增加超时时间
CRAWLER_TIMEOUT=60

# 启用缓存
CRAWLER_ENABLE_CACHE=True
CRAWLER_CACHE_TTL=7200
```

### 4. 内存不足

**问题**: `MemoryError` 或系统卡顿

**解决方案**:
```python
# 限制查询结果数量
pipelines = service.get_pipelines_by_company(
    company_name="恒瑞医药",
    limit=100  # 限制数量
)

# 使用分页
for offset in range(0, 1000, 100):
    results = db.query(Pipeline).limit(100).offset(offset).all()
    # 处理结果
```

---

## 维护操作

### 1. 数据库备份

```bash
# SQLite 备份
cp data/pharma_intelligence.db data/backup/pharma_$(date +%Y%m%d).db

# PostgreSQL 备份
pg_dump -U user pharma > backup/pharma_$(date +%Y%m%d).sql

# 恢复
psql -U user pharma < backup/pharma_20260202.sql
```

### 2. 日志清理

```bash
# 清理30天前的日志
find logs/ -name "*.log" -mtime +30 -delete

# 压缩日志
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
```

### 3. 数据库维护

```python
# 清理消失的管线（180天未更新）
from services.pipeline_service import get_pipeline_service

service = get_pipeline_service()
disappeared = service.cleanup_discontinued_pipelines(threshold_days=180)

print(f"Cleaned up {len(disappeared)} discontinued pipelines")
```

### 4. 缓存清理

```bash
# 清理爬虫缓存
rm -rf data/cache/*.json

# 或者在代码中
from crawlers.company_spider import CompanySpiderBase

spider = CompanySpiderBase()
spider.cache.clear()
```

### 5. 性能优化

```sql
-- 创建索引
CREATE INDEX idx_target_standard_name ON targets(standard_name);
CREATE INDEX idx_publication_pmid ON publications(pmid);
CREATE INDEX idx_pipeline_drug_company ON pipelines(drug_code, company_name);

-- 分析查询
EXPLAIN QUERY PLAN SELECT * FROM targets WHERE standard_name = 'EGFR';
```

---

## 更新部署

### 滚动更新流程

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 备份数据库
cp data/pharma_intelligence.db data/backup/pharma_pre_update_$(date +%Y%m%d).db

# 3. 安装新依赖
pip install -r requirements.txt

# 4. 运行测试
pytest --cov=. --cov-report=term-missing

# 5. 重启服务
sudo systemctl restart pharma_intelligence

# 6. 验证
curl http://localhost:8000/api/pipeline/health
```

### 数据库迁移

```bash
# 使用 Alembic
alembic revision --autogenerate -m "Add new column"
alembic upgrade head

# 回滚
alembic downgrade -1
```

---

## 安全检查清单

- [ ] 修改默认密码
- [ ] 配置 HTTPS（Let's Encrypt）
- [ ] 启用防火墙（只开放 80, 443 端口）
- [ ] 配置 API 速率限制
- [ ] 启用日志审计
- [ ] 定期备份数据库
- [ ] 更新依赖包（`pip-check`）
- [ ] 配置错误告警

---

**最后更新**: 2026-02-02
**维护者**: DevOps Team
