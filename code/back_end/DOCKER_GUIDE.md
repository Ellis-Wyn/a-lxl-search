# 🐳 Docker 部署指南

## 📋 目录
- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [常用命令](#常用命令)
- [配置说明](#配置说明)
- [故障排查](#故障排查)
- [生产部署](#生产部署)

---

## 前置要求

### 必须安装
1. **Docker Desktop** (Windows/Mac) 或 **Docker Engine** (Linux)
   - 下载地址：https://www.docker.com/products/docker-desktop
   - 版本要求：20.10+

2. **Docker Compose** (通常随Docker Desktop自动安装)
   - 检查版本：`docker-compose --version`

### 验证安装
```bash
# 检查Docker
docker --version

# 检查Docker Compose
docker-compose --version

# 测试Docker运行
docker run hello-world
```

---

## 快速开始

### 1️⃣ 准备配置文件

```bash
# 进入项目目录
cd D:\26初寒假实习\A_lxl_search\code\back_end

# 复制环境变量模板（可选）
# docker-compose.yml 已内置环境变量，无需额外配置
```

### 2️⃣ 一键启动所有服务

```bash
# 构建并启动所有服务（首次运行会自动下载镜像）
docker-compose up -d

# 查看启动日志
docker-compose logs -f app

# 等待看到 "✓ 应用启动完成" 字样
```

### 3️⃣ 验证服务

```bash
# 方法1：浏览器访问
# 打开浏览器访问：http://localhost:8000

# 方法2：API健康检查
curl http://localhost:8000/health

# 方法3：查看API文档
# 打开浏览器：http://localhost:8000/docs
```

### 4️⃣ 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| **API服务** | http://localhost:8000 | FastAPI应用 |
| **API文档** | http://localhost:8000/docs | 交互式API文档 |
| **搜索界面** | http://localhost:8000/static/search.html | 前端搜索页面 |
| **PostgreSQL** | localhost:5432 | 数据库（可选连接） |
| **Redis** | localhost:6379 | 缓存（可选连接） |

---

## 常用命令

### 🔄 服务管理

```bash
# 启动所有服务（后台运行）
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启所有服务
docker-compose restart

# 重启单个服务
docker-compose restart app

# 停止并删除所有数据卷（危险！会清空数据库）
docker-compose down -v
```

### 📊 查看状态

```bash
# 查看所有容器状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app

# 查看PostgreSQL日志
docker-compose logs -f postgres

# 查看Redis日志
docker-compose logs -f redis

# 查看所有服务日志
docker-compose logs -f
```

### 🔧 进入容器

```bash
# 进入应用容器
docker-compose exec app bash

# 进入PostgreSQL容器
docker-compose exec postgres psql -U pathology_user -d pathology_db

# 进入Redis容器
docker-compose exec redis redis-cli
```

### 🛠️ 构建和更新

```bash
# 重新构建镜像（代码修改后）
docker-compose build

# 重新构建并启动
docker-compose up -d --build

# 强制重新构建（不使用缓存）
docker-compose build --no-cache
```

### 💾 数据管理

```bash
# 备份数据库
docker-compose exec postgres pg_dump -U pathology_user pathology_db > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U pathology_user pathology_db < backup.sql

# 查看数据卷
docker volume ls

# 删除数据卷（危险！）
docker-compose down -v
```

---

## 配置说明

### 环境变量配置

在 `docker-compose.yml` 中的 `environment` 部分修改：

```yaml
environment:
  # 数据库密码
  - POSTGRES_PASSWORD=your-secure-password

  # 应用密钥（生产环境必须修改）
  - SECRET_KEY=your-random-secret-key

  # 允许的跨域来源
  - CORS_ORIGINS=http://localhost:8000,http://your-domain.com

  # PubMed邮箱
  - PUBMED_EMAIL=your-email@example.com
```

### 端口映射

如果端口冲突，可以修改映射：

```yaml
services:
  app:
    ports:
      - "8080:8000"  # 主机8080 -> 容器8000

  postgres:
    ports:
      - "5433:5432"  # 主机5433 -> 容器5432

  redis:
    ports:
      - "6380:6379"  # 主机6380 -> 容器6379
```

### 资源限制

防止容器占用过多资源：

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

---

## 故障排查

### ❌ 问题1：端口已被占用

**错误信息：**
```
Error: bind: address already in use
```

**解决方案：**
```bash
# 方法1：停止占用端口的进程
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Linux/Mac

# 方法2：修改docker-compose.yml中的端口映射
ports:
  - "8080:8000"  # 使用其他端口
```

### ❌ 问题2：数据库连接失败

**错误信息：**
```
connection refused, database "pathology_db" does not exist
```

**解决方案：**
```bash
# 1. 检查PostgreSQL是否健康
docker-compose ps postgres

# 2. 查看PostgreSQL日志
docker-compose logs postgres

# 3. 等待数据库完全启动（健康检查通过）
docker-compose up -d --wait

# 4. 手动初始化数据库（如果需要）
docker-compose exec app python scripts/init_db.py
```

### ❌ 问题3：容器启动失败

**解决方案：**
```bash
# 1. 查看详细日志
docker-compose logs app

# 2. 检查镜像构建
docker-compose build --no-cache

# 3. 删除旧容器和镜像重新构建
docker-compose down
docker rmi $(docker images -q pathology-ai-app)
docker-compose up -d --build
```

### ❌ 问题4：日志文件权限错误

**错误信息：**
```
Permission denied: '/app/logs'
```

**解决方案：**
```bash
# 在主机上创建日志目录
mkdir -p logs
chmod 777 logs

# 或在docker-compose.yml中添加用户配置
user: "${UID:-1000}:${GID:-1000}"
```

### ❌ 问题5：内存不足

**错误信息：**
```
Cannot allocate memory
```

**解决方案：**
```bash
# 1. 给Docker Desktop分配更多内存
# Settings -> Resources -> Memory -> 4GB+

# 2. 限制容器内存使用（见上面的"资源限制"）

# 3. 清理未使用的镜像和容器
docker system prune -a
```

---

## 生产部署

### 🔒 安全配置

1. **修改所有默认密码**
   ```yaml
   POSTGRES_PASSWORD=use-strong-password-here
   SECRET_KEY=use-random-50-char-string
   ```

2. **不要暴露数据库端口**
   ```yaml
   services:
     postgres:
       ports: []  # 移除端口映射，仅容器内可访问
   ```

3. **使用环境变量文件**
   ```bash
   # 创建 .env 文件（不要提交到Git）
   cp .env.docker.example .env
   # 编辑 .env 填入真实配置
   ```

### 🚀 性能优化

1. **使用生产级配置**
   ```yaml
   command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **启用Nginx反向代理**
   ```yaml
   nginx:
     image: nginx:alpine
     ports:
       - "80:80"
       - "443:443"
     volumes:
       - ./nginx.conf:/etc/nginx/nginx.conf
   ```

3. **配置SSL证书**
   - 使用Let's Encrypt免费证书
   - 或购买商业证书

### 📊 监控和日志

1. **日志收集**
   ```bash
   # 查看实时日志
   docker-compose logs -f

   # 保存日志到文件
   docker-compose logs > logs/docker-$(date +%Y%m%d).log
   ```

2. **健康检查**
   ```bash
   # 检查所有服务健康状态
   docker-compose ps

   # 手动健康检查
   curl http://localhost:8000/health
   ```

3. **资源监控**
   ```bash
   # 查看容器资源使用
   docker stats

   # 查看磁盘使用
   docker system df
   ```

---

## 开发技巧

### 🔧 开发模式

**自动重载（代码修改自动重启）：**

修改 `docker-compose.yml`：
```yaml
services:
  app:
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app  # 挂载代码目录
```

### 🐛 调试模式

**启用详细日志：**
```yaml
environment:
  - DEBUG=True
  - LOG_LEVEL=DEBUG
```

**进入容器调试：**
```bash
docker-compose exec app bash
python -m pytest tests/
```

### 📦 数据导入导出

**导出数据库：**
```bash
docker-compose exec postgres pg_dump -U pathology_user pathology_db > backup.sql
```

**导入数据库：**
```bash
docker-compose exec -T postgres psql -U pathology_user pathology_db < backup.sql
```

---

## 🎯 最佳实践

1. ✅ **定期备份数据**
   - 每天自动备份数据库
   - 备份到远程存储

2. ✅ **使用版本标签**
   - 不要使用 `latest` 标签
   - 使用版本号：`v1.0.0`

3. ✅ **限制容器资源**
   - 设置CPU和内存限制
   - 防止容器耗尽主机资源

4. ✅ **定期清理**
   - 删除未使用的镜像
   - 清理日志文件
   - 释放磁盘空间

5. ✅ **监控服务状态**
   - 设置健康检查
   - 配置告警通知
   - 定期检查日志

---

## 📚 参考资料

- [Docker官方文档](https://docs.docker.com/)
- [Docker Compose文档](https://docs.docker.com/compose/)
- [FastAPI部署指南](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL Docker镜像](https://hub.docker.com/_/postgres)
- [Redis Docker镜像](https://hub.docker.com/_/redis)

---

## 🆘 获取帮助

遇到问题？

1. 查看日志：`docker-compose logs -f`
2. 检查配置：`docker-compose config`
3. 验证服务：`docker-compose ps`
4. 查阅本文档的"故障排查"部分
5. 提交Issue：项目GitHub仓库

---

**最后更新：2026-02-03**
**维护者：A_lxl_search Team**
