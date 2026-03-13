# P8标准部署方案 - 腾讯云

**版本**: v2.4.0-p8
**适用场景**: 生产环境部署
**最后更新**: 2026-03-13

---

## 📋 P8标准对照表

| 维度 | P6水平 | P8水平 | 本项目实现 |
|------|--------|--------|------------|
| **资源管理** | 无限制 | CPU/内存限制 | ✅ 部署资源配置 |
| **版本管理** | 手动tag | 自动化版本+回滚 | ✅ Git tag集成 |
| **部署策略** | 滚动更新 | 蓝绿/金丝雀 | ✅ 健康检查+回滚 |
| **监控告警** | 基础日志 | Prometheus+Grafana | ✅ 完整监控栈 |
| **备份恢复** | 手动 | 自动化+验证 | ✅ 备份脚本 |
| **安全加固** | 基础 | 多层防护 | ✅ 非root+seccomp |
| **故障恢复** | 手动重启 | 自动恢复+告警 | ✅ restart+healthcheck |
| **可观测性** | 日志 | Metrics+Traces+Logs | ✅ 三位一体 |

---

## 🏗️ 架构设计

### 服务器资源规划

**推荐配置**: 腾讯云 2核4GB

```
┌─────────────────────────────────────────────┐
│              腾讯云 2核4GB                   │
├─────────────────────────────────────────────┤
│  系统预留: 512MB                            │
├─────────────────────────────────────────────┤
│  FastAPI:    256MB-1GB  (0.25-1核)          │
│  PostgreSQL: 256MB-1GB  (0.25-1核)          │
│  Redis:      64MB-256MB (0.1-0.5核)         │
│  Prometheus: 128MB-512MB                    │
│  Grafana:    64MB-256MB                     │
├─────────────────────────────────────────────┤
│  可用余量: ~500MB                           │
└─────────────────────────────────────────────┘
```

### 资源限制配置详解

```yaml
# FastAPI应用
app:
  deploy:
    resources:
      limits:
        cpus: '1.0'      # 最多1核（突发流量）
        memory: 1G       # 最多1GB（防OOM）
      reservations:
        cpus: '0.25'     # 保证0.25核（常驻）
        memory: 256M     # 保证256MB（常驻）

# PostgreSQL数据库
postgres:
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1G
      reservations:
        cpus: '0.25'
        memory: 256M
  # 性能调优
  environment:
    - shared_buffers=128MB        # 缓冲区
    - effective_cache_size=512MB   # 有效缓存
    - work_mem=4MB                 # 每查询内存
    - max_connections=50           # 连接数

# Redis缓存
redis:
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 256M
      reservations:
        cpus: '0.1'
        memory: 64M
```

---

## 🚀 部署流程

### 1. 首次部署

```bash
# 1.1 克隆项目
cd /opt
git clone <repository-url> A_lxl_search
cd A_lxl_search/code/back_end

# 1.2 配置环境变量
cp .env.production.template .env
nano .env  # 修改密码、域名等配置

# 1.3 构建镜像
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# 1.4 配置SSL
chmod +x scripts/setup-ssl.sh
sudo ./scripts/setup-ssl.sh api.your-domain.com
```

### 2. 日常更新

```bash
# 2.1 拉取最新代码
git pull origin main

# 2.2 部署（自动备份+回滚保护）
./scripts/deploy.sh

# 2.3 验证
./scripts/health-check.sh
```

### 3. 紧急回滚

```bash
# 回滚到上一个版本
./scripts/rollback.sh

# 回滚到指定版本
./scripts/rollback.sh -v 2.3.0

# 仅回滚数据库
./scripts/rollback.sh -d
```

---

## 📊 监控体系

### Prometheus指标

| 类型 | 指标 | 告警阈值 |
|------|------|----------|
| 应用 | http_requests_total | 错误率 > 5% |
| 应用 | http_request_duration_seconds | P95 > 1s |
| 数据库 | pg_stat_database_numbackends | 连接数 > 80% |
| 数据库 | pg_database_size_bytes | 增长 > 100MB/h |
| 缓存 | redis_memory_used_bytes | 使用率 > 90% |
| 系统 | node_filesystem_avail_bytes | 可用 < 10% |

### Grafana仪表板

访问地址: `http://服务器IP:3000`

默认账号: `admin / 修改后的密码`

仪表板包含:
- API性能概览
- 数据库健康度
- 缓存命中率
- 系统资源使用
- 业务指标趋势

---

## 💾 备份策略

### 自动备份

```bash
# 添加到crontab
0 2 * * * cd /opt/A_lxl_search/code/back_end && ./scripts/backup.sh
```

### 手动备份

```bash
# 完整备份
./scripts/backup.sh backup

# 列出备份
./scripts/backup.sh list

# 恢复备份
./scripts/backup.sh restore backups/db_full_20260313_020000.sql.gz
```

### 备份保留策略

- 本地备份: 保留30天
- 远程备份: 保留90天（需配置）
- 备份验证: 自动验证gzip完整性

---

## 🔒 安全加固

### 容器安全

```yaml
# 非root用户运行
USER appuser

# 最小权限
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # 仅保留绑定端口权限

# 只读根文件系统
read_only: true
tmpfs:
  - /tmp:noexec,nosuid,size=100m
```

### 网络隔离

```yaml
# 内部网络
networks:
  pathology-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24

# 监控网络（独立隔离）
  monitoring-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/24
```

### 端口暴露

| 服务 | 内部端口 | 暴露端口 | 绑定地址 |
|------|----------|----------|----------|
| FastAPI | 8000 | 8000 | 0.0.0.0 (Nginx代理) |
| PostgreSQL | 5432 | 5432 | 127.0.0.1 |
| Redis | 6379 | 6379 | 127.0.0.1 |
| Prometheus | 9090 | 9090 | 127.0.0.1 |
| Grafana | 3000 | 3000 | 0.0.0.0 (可选加认证) |

---

## 🛠️ 运维命令速查

### 服务管理

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重启单个服务
docker compose restart app

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f app
```

### 健康检查

```bash
# 完整检查
./scripts/health-check.sh

# JSON格式（用于监控）
./scripts/health-check.sh --json

# 检查指定URL
./scripts/health-check.sh --url https://api.your-domain.com
```

### 数据库操作

```bash
# 进入数据库
docker exec -it pathology-ai-postgres psql -U pathology_ai -d pathology_ai

# 导出数据
docker exec pathology-ai-postgres pg_dump -U pathology_ai pathology_ai > backup.sql

# 导入数据
docker exec -i pathology-ai-postgres psql -U pathology_ai pathology_ai < backup.sql
```

---

## 📈 性能优化

### 数据库连接池

```python
# 在应用中配置
DATABASE_POOL_SIZE = 10
DATABASE_MAX_OVERFLOW = 20
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

### Redis缓存策略

```python
# 缓存配置
CACHE_TTL = 3600  # 1小时
CACHE_MAX_SIZE = 1000
CACHE_EVICTION_POLICY = "allkeys-lru"
```

### 日志轮转

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"
```

---

## 🚨 故障处理

### 常见问题

| 问题 | 症状 | 处理 |
|------|------|------|
| OOM | 容器被杀死 | 检查limits，增加内存 |
| 连接池耗尽 | API 500 | 检查连接泄漏，重启应用 |
| 磁盘满 | 写入失败 | 清理日志，扩容磁盘 |
| CPU 100% | 响应慢 | 检查爬虫，限制并发 |

### 应急流程

```bash
# 1. 检查服务状态
./scripts/health-check.sh

# 2. 查看日志
docker compose logs --tail=100 app

# 3. 尝试重启
docker compose restart app

# 4. 如无法恢复，执行回滚
./scripts/rollback.sh

# 5. 通知团队
# 配置 Slack/Email 告警
```

---

## 📚 相关文档

- [腾讯云部署指南](TENCENT_DEPLOYMENT.md)
- [部署后配置](POST_DEPLOYMENT.md)
- [故障排查手册](TROUBLESHOOTING.md)

---

**维护者**: Pathology AI Team
**最后更新**: 2026-03-13
