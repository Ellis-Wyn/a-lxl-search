# 腾讯云部署指南 - 病理AI药研情报库

**适用场景**: 将后端API部署到腾讯云服务器，实现公网访问
**最后更新**: 2026-03-13

---

## 📋 目录

1. [服务器购买建议](#服务器购买建议)
2. [安全组配置](#安全组配置)
3. [服务器初始化](#服务器初始化)
4. [Docker环境安装](#docker环境安装)
5. [项目部署](#项目部署)
6. [域名与SSL配置](#域名与ssl配置)
7. [进程守护与开机自启](#进程守护与开机自启)
8. [监控与日志](#监控与日志)
9. [故障排查](#故障排查)

---

## 🛒 服务器购买建议

### 推荐配置

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| **实例规格** | 2核4GB 或 2核8GB | 满足FastAPI + PostgreSQL + Redis |
| **操作系统** | Ubuntu 22.04 LTS 或 24.04 LTS | 社区支持好，Docker兼容性强 |
| **系统盘** | 40GB SSD | 足够运行系统 + Docker + 应用 |
| **数据盘** | 100GB SSD（可选） | 存储数据库和日志 |
| **带宽** | 3-5 Mbps | 按量付费即可，API流量不大 |
| **地域** | 广州/上海/北京 | 根据目标用户选择 |

### 购买步骤

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. **产品** → **云服务器** → **新建实例**
3. 按上述配置选择
4. **网络配置**:
   - 选择私有网络（默认VPC即可）
   - 公网IP选择**分配免费公网IP**
5. **安全组**: 创建新安全组（见下一节）
6. **登录方式**: 选择**密码登录**，设置root密码

### 成本估算

- 2核4GB：约 ¥60-80/月
- 2核8GB：约 ¥100-130/月
- 按量付费稍贵，建议购买**包年包月**节省50%+

---

## 🔒 安全组配置

安全组是腾讯云的虚拟防火墙，必须正确配置才能访问服务。

### 创建安全组

1. **产品** → **安全组** → **新建**
2. 添加以下入站规则：

| 协议 | 端口 | 来源 | 说明 |
|------|------|------|------|
| TCP | 22 | 你的IP/段 | SSH登录（限制你的IP更安全） |
| TCP | 80 | 0.0.0.0/0 | HTTP（用于Let's Encrypt验证） |
| TCP | 443 | 0.0.0.0/0 | HTTPS |
| TCP | 8000 | 0.0.0.0/0 | API端口（可选，建议用Nginx代理） |
| TCP | 3000 | 0.0.0.0/0 | 前端端口（如果需要） |

### 保存安全组ID，绑定到云服务器实例

---

## 🖥️ 服务器初始化

### 1. SSH登录服务器

```bash
# 替换为你的公网IP
ssh root@你的服务器IP
# 输入购买时设置的密码
```

### 2. 更新系统

```bash
apt update && apt upgrade -y
```

### 3. 设置时区（可选）

```bash
timedatectl set-timezone Asia/Shanghai
```

### 4. 创建应用用户（推荐）

```bash
# 创建专用用户（不使用root运行应用）
useradd -m -s /bin/bash pathology
# 设置密码
passwd pathology
# 添加到sudo组（可选）
usermod -aG sudo pathology
```

---

## 🐳 Docker环境安装

### 方式一：一键安装脚本（推荐）

```bash
# 下载并执行Docker官方安装脚本
curl -fsSL https://get.docker.com | sh

# 启动Docker服务
systemctl start docker
systemctl enable docker

# 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 方式二：手动安装

```bash
# 安装依赖
apt install -y ca-certificates curl gnupg lsb-release

# 添加Docker官方GPG密钥
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加Docker仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动服务
systemctl start docker
systemctl enable docker
```

---

## 📦 项目部署

### 1. 安装Git

```bash
apt install -y git
```

### 2. 克隆项目

```bash
# 方式一：从GitHub克隆（如果代码已上传）
cd /opt
git clone https://github.com/你的用户名/A_lxl_search.git

# 方式二：使用SCP从本地上传（在本地电脑执行）
# scp -r D:\26初寒假实习\A_lxl_search root@服务器IP:/opt/A_lxl_search
```

### 3. 配置环境变量

```bash
cd /opt/A_lxl_search/code/back_end

# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

**关键配置项**：

```bash
# 数据库配置（Docker内部网络）
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=pathology_ai
POSTGRES_PASSWORD=你的强密码
POSTGRES_DB=pathology_ai

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379

# API配置
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["https://你的域名","https://你的域名.vercel.app"]

# 爬虫配置
CRAWLER_ENABLED=false  # 生产环境建议关闭或调整调度
```

### 4. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 5. 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 测试API
curl http://localhost:8000/api/pipeline/search?keyword=EGFR
```

---

## 🌐 域名与SSL配置

### 1. 域名解析

在腾讯云**DNSPod**或你的域名服务商添加解析：

| 类型 | 主机记录 | 记录值 |
|------|----------|--------|
| A | api | 你的服务器公网IP |
| A | www | 你的服务器公网IP |

### 2. 安装Nginx反向代理

```bash
apt install -y nginx
```

### 3. 配置Nginx

创建配置文件 `/etc/nginx/sites-available/pathology-api`：

```nginx
# HTTP配置 - 用于Let's Encrypt验证
server {
    listen 80;
    server_name api.你的域名.com;

    # Let's Encrypt验证路径
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # 其他请求重定向到HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS配置
server {
    listen 443 ssl http2;
    server_name api.你的域名.com;

    # SSL证书路径（下面会生成）
    ssl_certificate /etc/letsencrypt/live/api.你的域名.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.你的域名.com/privkey.pem;

    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 日志
    access_log /var/log/nginx/pathology-api-access.log;
    error_log /var/log/nginx/pathology-api-error.log;

    # 反向代理到FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 4. 启用配置

```bash
# 创建符号链接
ln -s /etc/nginx/sites-available/pathology-api /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重启Nginx
systemctl restart nginx
```

### 5. 申请SSL证书（Let's Encrypt）

```bash
# 安装Certbot
apt install -y certbot python3-certbot-nginx

# 申请证书
certbot --nginx -d api.你的域名.com

# 按提示输入邮箱，同意条款
```

### 6. 自动续期

```bash
# Certbot已自动添加续期定时任务
# 验证定时任务
systemctl list-timers | grep certbot

# 手动测试续期
certbot renew --dry-run
```

---

## 🔧 进程守护与开机自启

### Docker Compose自动重启

在 `docker-compose.yml` 中确保添加了重启策略：

```yaml
services:
  fastapi:
    restart: always
    # ...其他配置

  postgres:
    restart: always
    # ...其他配置

  redis:
    restart: always
    # ...其他配置
```

### 验证开机自启

```bash
# Docker服务开机自启
systemctl is-enabled docker

# 测试重启（谨慎操作）
reboot

# 重启后检查
docker-compose ps
```

---

## 📊 监控与日志

### 1. 查看Docker日志

```bash
# 所有服务日志
docker-compose logs -f

# 特定服务日志
docker-compose logs -f fastapi
docker-compose logs -f postgres

# 最近100行
docker-compose logs --tail=100 fastapi
```

### 2. 应用日志（FastAPI）

```bash
# 查看应用日志
tail -f /opt/A_lxl_search/code/back_end/logs/pathology_ai.log
```

### 3. Nginx日志

```bash
# 访问日志
tail -f /var/log/nginx/pathology-api-access.log

# 错误日志
tail -f /var/log/nginx/pathology-api-error.log
```

### 4. 服务器资源监控

```bash
# 安装htop
apt install -y htop

# 查看资源使用
htop

# 查看磁盘使用
df -h

# 查看Docker资源
docker stats
```

---

## 🔍 故障排查

### 问题1: 容器无法启动

```bash
# 查看容器日志
docker-compose logs 服务名

# 检查端口占用
netstat -tlnp | grep 8000

# 重建容器
docker-compose down
docker-compose up -d --force-recreate
```

### 问题2: 数据库连接失败

```bash
# 检查PostgreSQL容器状态
docker-compose ps postgres

# 进入数据库容器
docker-compose exec postgres bash

# 连接数据库
psql -U pathology_ai -d pathology_ai

# 检查数据库列表
\l

# 检查表
\dt
```

### 问题3: API无法访问

```bash
# 检查FastAPI是否运行
curl http://localhost:8000/health

# 检查Nginx配置
nginx -t

# 检查Nginx错误日志
tail -f /var/log/nginx/pathology-api-error.log
```

### 问题4: SSL证书问题

```bash
# 查看证书状态
certbot certificates

# 重新申请证书
certbot --nginx -d api.你的域名.com --force-renewal
```

### 问题5: 安全组拦截

```bash
# 从服务器内部测试
curl http://localhost:8000/health  # 应该成功

# 从外部测试
curl http://你的公网IP:8000/health  # 失败说明是安全组问题
```

---

## 📝 部署检查清单

部署完成后，逐项检查：

- [ ] SSH能正常登录服务器
- [ ] Docker和Docker Compose已安装
- [ ] 项目代码已上传到服务器
- [ ] `.env` 文件已正确配置
- [ ] `docker-compose up -d` 所有容器正常运行
- [ ] `curl http://localhost:8000/health` 返回健康
- [ ] 域名解析已生效
- [ ] Nginx已安装并配置反向代理
- [ ] SSL证书已申请成功
- [ ] `curl https://api.你的域名.com/health` 返回健康
- [ ] 防火墙/安全组已开放必要端口
- [ ] Docker容器设置了开机自启
- [ ] SSL证书自动续期已配置

---

## 🚀 部署后配置

### 更新前端API配置

部署成功后，更新前端配置指向生产API：

**文件**: `code/front_end/src/api/axios.js`

```javascript
// 将
baseURL: 'http://localhost:8000',

// 改为
baseURL: 'https://api.你的域名.com',
```

### 更新Vercel前端

```bash
# 在本地
git add .
git commit -m "chore: 更新生产API地址"
git push
```

Vercel会自动部署更新。

---

## 📞 技术支持

**常见问题**:
1. 查看 `产品开发文档.md` 的 FAQ 部分
2. 查看本文档的故障排查章节

**服务器维护**:
- 定期更新系统: `apt update && apt upgrade -y`
- 定期备份数据库（见备份脚本）
- 监控磁盘使用和日志大小

**备份策略**:
```bash
# 数据库备份
docker-compose exec postgres pg_dump -U pathology_ai pathology_ai > backup_$(date +%Y%m%d).sql

# 定时备份（添加到crontab）
0 2 * * * cd /opt/A_lxl_search/code/back_end && docker-compose exec -T postgres pg_dump -U pathology_ai pathology_ai > /backup/db_$(date +\%Y\%m\%d).sql
```

---

**最后更新**: 2026-03-13
**作者**: Claude Code
**版本**: v1.0
