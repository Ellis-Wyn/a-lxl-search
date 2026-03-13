# 部署后配置指南

**用途**: 后端部署完成后，配置前端连接生产环境API
**最后更新**: 2026-03-13

---

## 📋 部署后检查清单

### 1. 后端验证

```bash
# 服务器上执行
curl http://localhost:8000/health
curl https://api.your-domain.com/health
```

### 2. 前端配置更新

#### 方式一：修改配置文件（推荐）

编辑 `code/front_end/src/api/axios.js`:

```javascript
// 将
const API_BASE_URL = ... 'https://api.your-domain.com'

// 改为你的实际API域名
const API_BASE_URL = ... 'https://api.lxl-research.com'
```

#### 方式二：使用环境变量

在构建时设置环境变量：

```bash
# 本地构建测试
cd code/front_end
VITE_API_BASE_URL=https://api.your-domain.com npm run build

# Vercel部署（在Vercel控制台设置环境变量）
# 1. 进入项目设置 → Environment Variables
# 2. 添加: VITE_API_BASE_URL = https://api.your-domain.com
# 3. 重新部署
```

### 3. 重新部署前端

```bash
# 提交代码
git add .
git commit -m "chore: 更新生产API地址"
git push
```

Vercel会自动部署更新。

### 4. 验证前后端连接

1. 访问你的Vercel前端地址
2. 打开浏览器开发者工具 (F12)
3. 查看Network标签，确认API请求到正确的域名
4. 测试搜索功能是否正常

---

## 🔧 配置CORS

### 后端CORS配置

确保后端 `.env` 或 `docker-compose.yml` 中的 `CORS_ORIGINS` 包含：

```json
["https://your-project.vercel.app", "https://api.your-domain.com"]
```

### 重启后端服务

```bash
cd /opt/A_lxl_search/code/back_end
docker-compose restart app
```

---

## 📊 监控与维护

### 查看后端日志

```bash
# 实时日志
docker-compose logs -f app

# 最近100行
docker-compose logs --tail=100 app
```

### 数据库备份

```bash
# 手动备份
docker-compose exec postgres pg_dump -U pathology_ai pathology_ai > backup_$(date +%Y%m%d).sql

# 定时备份（添加到crontab）
0 2 * * * cd /opt/A_lxl_search/code/back_end && docker-compose exec -T postgres pg_dump -U pathology_ai pathology_ai > /backup/db_$(date +\%Y\%m\%d).sql
```

---

## ⚠️ 常见问题

### 问题1: CORS错误

**症状**: 浏览器控制台显示 "CORS policy: No 'Access-Control-Allow-Origin' header"

**解决**:
1. 检查后端CORS_ORIGINS配置
2. 确保包含你的前端域名
3. 重启后端服务

### 问题2: API请求失败

**症状**: 前端显示网络错误

**解决**:
1. 检查后端服务是否运行: `docker-compose ps`
2. 检查Nginx配置: `nginx -t`
3. 检查安全组是否开放443端口

### 问题3: SSL证书过期

**症状**: 浏览器显示证书警告

**解决**:
```bash
# 手动续期
certbot renew

# 重启Nginx
systemctl restart nginx
```

---

**最后更新**: 2026-03-13
