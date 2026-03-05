# PostgreSQL 安装指南（Windows）

## 方案一：使用安装包（推荐，图形界面）

### 步骤 1：下载安装包

访问 PostgreSQL 官网下载页面：
```
https://www.postgresql.org/download/windows/
```

**推荐版本**：PostgreSQL 14.x 或 15.x

**直接下载链接**：
- PostgreSQL 15.3-1: https://get.enterprisedb.com/postgresql/postgresql-15.3-1-windows-x64.exe
- PostgreSQL 14.8-1: https://get.enterprisedb.com/postgresql/postgresql-14.8-1-windows-x64.exe

### 步骤 2：运行安装程序

1. 双击下载的 `.exe` 文件
2. **重要**：安装路径建议使用默认路径 `C:\Program Files\PostgreSQL\15`
3. 端口使用默认 `5432`
4. **超级用户密码**：设置一个强密码（请记住！）
   - 建议：`Postgres2024!` 或您自己设定的密码
5. 其他选项保持默认

### 步骤 3：配置环境变量

安装完成后，将以下路径添加到系统 PATH：
```
C:\Program Files\PostgreSQL\15\bin
```

**手动添加方法**：
1. 右键"此电脑" → 属性
2. 高级系统设置 → 环境变量
3. 在"系统变量"中找到 `Path`，点击编辑
4. 添加新路径：`C:\Program Files\PostgreSQL\15\bin`

---

## 方案二：使用 Chocolatey（命令行，更快捷）

### 步骤 1：安装 Chocolatey（如果还没有）

以**管理员身份**运行 PowerShell：
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### 步骤 2：安装 PostgreSQL

```powershell
choco install postgresql --params '/Password:your_password'
```

将 `your_password` 替换为您想要的密码。

---

## 安装后验证

打开**命令提示符**或**PowerShell**：

```bash
# 检查版本
psql --version

# 输出应类似：psql (PostgreSQL) 15.3
```

---

## 创建数据库

### 方法一：使用 pgAdmin（图形界面）

1. 安装完成后，pgAdmin 会自动启动
2. 连接到服务器（localhost，端口 5432）
3. 右键"Databases" → Create → Database
4. 数据库名称：`drug_intelligence_db`
5. 点击"Save"

### 方法二：使用命令行（更快）

```bash
# 连接到 PostgreSQL
psql -U postgres

# 输入您设置的密码

# 创建数据库
CREATE DATABASE drug_intelligence_db;

# 验证
\l

# 退出
\q
```

---

## 配置项目

在 `code/back_end/` 目录下创建 `.env` 文件：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=drug_intelligence_db
DB_USER=postgres
DB_PASSWORD=您设置的密码

# PubMed（可选）
PUBMED_EMAIL=your_email@example.com
```

---

## 下一步

安装完成后，运行初始化脚本：

```bash
cd code/back_end
python scripts/init_db.py
```

---

## 常见问题

### Q: 端口 5432 被占用？
**A**: 检查是否有其他 PostgreSQL 实例在运行：
```bash
netstat -ano | findstr :5432
```

### Q: 忘记密码？
**A**: 重新安装或重置密码（需要停止服务）

### Q: 安装失败？
**A**:
1. 检查是否有杀毒软件阻止
2. 以管理员身份运行安装程序
3. 临时关闭防火墙

---

*安装大约需要 10-15 分钟*
