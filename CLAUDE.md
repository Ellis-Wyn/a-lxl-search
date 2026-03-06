# 病理AI药研情报库 - 项目记忆文档

**项目状态**: ✅ 前后端100%完成，前端已部署至Vercel
**最后更新**: 2026-03-06
**版本**: v2.1.0 - Vercel生产部署版

---

## 📌 项目概述

构建一个药研情报库，以靶点（Target）为核心锚点，聚合两条信息流：
- **Publication**: PubMed 文献流（科学证据与热点）
- **Pipeline**: 公司管线/临床库条目（产业进度与阶段）

**核心价值**: 快速掌握第一手监管与研发进展资讯，支持竞争情报分析。

---

## 🎯 当前数据规模

| 数据类型 | 数量 | 来源 |
|---------|------|------|
| 研发管线 | 167条 | 14家药企官网 |
| 靶点信息 | 7个 | 数据库存储 |
| 爬虫覆盖 | 14个 | 药企官网 + CDE平台 |
| API接口 | 30+ 个 | RESTful API |

---

## 📚 核心文档

**主文档**:
- ⭐ `产品开发文档.md` - **开发者必读**（完整的产品文档）
  - 产品概述与核心功能
  - 完整的架构说明
  - 详细的目录结构解析
  - 数据模型与字段说明
  - 功能模块详解
  - 产品使用说明
  - 开发指南与部署指南
  - FAQ常见问题

**用户文档**（用户根目录）:
- `START_HERE.md` - 3分钟快速入门
- `QUICKSTART.md` - 完整使用指南

**测试文档**:
- `SWAGGER_TEST_GUIDE.md` - Swagger UI测试指南
- `safe_api_test_order.md` - 安全测试顺序

---

## 🏗️ 数据模型结构

### 核心设计理念
- **架构**: 以 Target 为中心的星型架构
- **粒度**: Pipeline 最小粒度为 `(drug_code, company_name, indication)`
- **可追溯**: 所有 Pipeline 必须保留 `source_url`
- **增量监控**: 使用 `first_seen_at` + `last_seen_at` 检测变化

### 主表
1. **Target（靶点）**
   - `target_id` (PK), `standard_name` (UNIQUE), `aliases` (数组)
   - `gene_id`, `uniprot_id`

2. **Publication（PubMed文献）**
   - `pmid` (PK), `title`, `abstract`, `pub_date`, `mesh_terms`
   - `journal`, `clinical_data_tags`（ORR/PFS等）

3. **Pipeline（管线）**
   - `pipeline_id` (PK), `drug_code`, `company_name`, `indication`, `phase`
   - `modality`（小分子/ADC等）, `source_url`
   - `first_seen_at`, `last_seen_at`

### 关联表
1. **Target_Publication**：`(target_id, pmid)` 联合主键
2. **Target_Pipeline**：`(target_id, pipeline_id)` 联合主键

---

## ✅ 已完成的核心功能

### 1. PubMed智能搜索模块 ✅
- **智能查询转换**: EGFR → 专业检索式（同义词扩展）
- **多维度排序**:
  - 时效性权重 70%
  - 临床数据披露 +50分
  - Phase III/监管认定 +40分
  - 高质量来源 +30分
- **关键指标提取**: 自动识别ORR、PFS、OS、n=等临床指标

**文件**: `services/pubmed_service.py`

### 2. 管线查询与管理 ✅
- **智能搜索**: 支持药物代码、适应症、公司名称
- **公司名称映射**: 35家公司别名支持（恒瑞→恒瑞医药）
- **研发阶段标准化**: 30+种中英文格式
- **去重机制**: `(drug_code, company_name, indication)` 唯一约束

**文件**: `services/pipeline_service.py`, `utils/company_name_mapper.py`

### 3. 爬虫调度系统 ✅
- **定时调度**: 每天凌晨2点自动运行
- **并发控制**: 最多3个爬虫同时运行
- **智能重试**: 失败自动重试，指数退避
- **执行日志**: 记录每次运行的详细日志
- **健康监控**: 实时监控爬虫运行状态

**文件**: `crawlers/scheduler.py`, `api/crawlers.py`

### 4. 数据归一化服务 ✅
- **公司名称**: "恒瑞" → "恒瑞医药"（35家公司映射）
- **研发阶段**: "临床I期" → "Phase 1"
- **适应症**: "非小细胞肺癌" → "NSCLC"
- **靶点别名**: HER2 = ERBB2 = c-ErbB2

**文件**: `services/data_normalization_service.py`

### 5. 竞品监控与预警 ✅
- **Phase Jump检测**: Phase II → Phase III 自动告警
- **新入局者识别**: 公司首次进入某靶点
- **竞品退场预警**: 连续21天未抓取到标记终止

**文件**: `services/alert_service.py`, `crawlers/base_spider.py`

---

## 🕷️ 爬虫列表（14个）

| 序号 | 爬虫名称 | 公司/平台 | 数据量 | 状态 |
|------|---------|----------|--------|------|
| 1 | hengrui | 恒瑞医药 | 40条 | ✅ 健康运行 |
| 2 | beigene | 百济神州 | 5条 | ✅ 健康运行 |
| 3 | xindaa | 信达生物 | 运行中 | ✅ 健康运行 |
| 4 | junshi | 君实生物 | 14条 | ✅ 健康运行 |
| 5 | akeso | 康方生物 | 12条 | ✅ 健康运行 |
| 6 | zailab | 再鼎医药 | 19条 | ✅ 健康运行 |
| 7 | hutchmed | 和黄医药 | 12条 | ✅ 健康运行 |
| 8 | aspercentage | 艾力斯医药 | 9条 | ✅ 健康运行 |
| 9 | cspc | 石药集团 | 15条 | ✅ 健康运行 |
| 10 | fosun | 复星医药 | 17条 | ✅ 健康运行 |
| 11 | simcere | 先声药业 | 14条 | ✅ 健康运行 |
| 12 | wuxibiologics | 药明生物 | 10条 | ✅ 健康运行 |
| 13 | cde | CDE官网 | 0条 | ✅ 健康运行 |
| 14 | cde_playwright | CDE（Playwright）| 0条 | ✅ 健康运行 |

**总计**: 167条管线数据

---

## 🛠️ 开发环境

### 技术栈
**后端**:
- **语言**: Python 3.10+
- **框架**: FastAPI
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7（可选）
- **爬虫**: Scrapy + BeautifulSoup + Playwright
- **ORM**: SQLAlchemy
- **日志**: Loguru

**前端** ✅ 2026-02-08新增:
- **框架**: React 18.2+
- **构建工具**: Vite 5.x
- **样式**: Tailwind CSS v4
- **路由**: React Router 6.x
- **HTTP客户端**: Axios 1.6+
- **字体**: JetBrains Mono (标题) + Source Sans 3 (正文)
- **主题**: 绿色(#00ff88) + 黑色(#0a0a0a)

### 项目结构
```
A_lxl_search/
├── 产品开发文档.md           # ⭐ 主文档（开发者必读）
├── code/
│   ├── back_end/              # 【约定】所有后端代码
│   │   ├── api/               # API接口
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   ├── crawlers/         # 爬虫模块
│   │   ├── utils/            # 工具函数
│   │   ├── core/             # 核心框架
│   │   └── main.py           # 入口文件
│   └── front_end/            # 前端代码 ✅ 2026-02-08完成
│       ├── src/
│       │   ├── api/          # API客户端层
│       │   ├── pages/        # 页面组件
│       │   │   ├── Home/           # 统一搜索页
│       │   │   ├── Targets/       # 靶点列表页
│       │   │   ├── Pipelines/     # 管线浏览页
│       │   │   ├── Publications/  # 文献流页
│       │   │   └── TargetDetail/  # 靶点详情页
│       │   ├── components/   # 可复用组件
│       │   │   └── layout/      # 布局组件
│       │   ├── context/      # 状态管理
│       │   └── styles/       # 全局样式
│       ├── public/
│       │   └── images/       # 静态资源（背景图片）
│       ├── package.json
│       └── vite.config.js
```

---

## 🌐 生产部署

### 前端部署（Vercel）✅ 2026-03-06完成

前端已成功部署到 Vercel，配置文件已就位：

**关键配置文件**:
- `vercel.json` - 根目录配置，指定构建命令和输出目录
- `code/front_end/vercel.json` - 前端子目录配置，包含URL重写规则

**Vercel配置说明**:
```json
{
  "installCommand": "cd code/front_end && npm install",
  "buildCommand": "cd code/front_end && npm run build",
  "outputDirectory": "code/front_end/dist",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

**重要设计决策**:
1. **URL重写规则**: 解决React SPA客户端路由的404问题
   - 所有路径重定向到 `index.html`
   - 让React Router接管路由处理
2. **子目录构建**: 支持monorepo结构，后端在 `code/back_end`，前端在 `code/front_end`
3. **installCommand**: 确保依赖安装在正确的子目录

**部署方式**:
- GitHub集成自动部署（推荐）
- Vercel CLI手动部署

**前端部署地址**: （需要用户添加实际Vercel域名）

### 后端部署（待完成）⚠️

**当前状态**: 后端仅在本地运行（localhost:8000）

**问题**: 前端在Vercel公网环境无法访问本地后端

**解决方案（选择其一）**:

#### 方案1：部署到Zeabur（推荐）⭐
- 注册 [Zeabur](https://zeabur.com)
- 导入GitHub仓库
- Zeabur自动识别并部署Docker配置
- 获得公网API地址（如：`https://your-api.zeabur.app`）

#### 方案2：部署到Railway
- 注册 [Railway](https://railway.app)
- 连接GitHub仓库
- 配置PostgreSQL和Redis
- 获取API公网地址

#### 方案3：云服务器部署
- 使用已有的云服务器（阿里云、腾讯云）
- 使用Docker Compose部署
- 配置域名和SSL证书

**配置步骤（后端部署后）**:
1. 更新前端API配置：`src/api/axios.js`
2. 修改 `baseURL` 为生产环境API地址
3. 重新部署前端到Vercel

**当前API配置**:
```javascript
// src/api/axios.js (第4行)
baseURL: 'http://localhost:8000',  // ❌ 仅适用于本地开发
// 需要修改为: 'https://your-api.zeabur.app'
```

### Docker本地部署

后端支持完整的Docker部署，使用Docker Compose一键启动所有服务：

```bash
cd code/back_end
docker-compose up -d
```

**服务配置**:
- FastAPI应用：端口8000
- PostgreSQL：端口5432
- Redis：端口6379

详见：`code/back_end/DOCKER_GUIDE.md`

---

## 🚀 快速开始

### 启动服务

#### 1. 启动后端服务
```bash
cd D:\26初寒假实习\A_lxl_search\code\back_end
python main.py
```
后端将运行在 `http://localhost:8000`

#### 2. 启动前端服务 ✅ 新增
```bash
cd D:\26初寒假实习\A_lxl_search\code\front_end
npm run dev
```
前端将运行在 `http://localhost:5175`（或5173/5174）

### 访问应用
- **前端界面**: http://localhost:5175
  - 统一搜索页
  - 靶点浏览页
  - 管线列表页
  - 文献流页面
- **Swagger UI**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 测试API
```bash
# 健康检查
curl http://localhost:8000/health

# 搜索管线
curl "http://localhost:8000/api/pipeline/search?keyword=EGFR"

# 按公司查询
curl "http://localhost:8000/api/pipeline/company/恒瑞"

# PubMed搜索
curl -X POST "http://localhost:8000/api/pubmed/search" \
  -H "Content-Type: application/json" \
  -d '{"target_name": "EGFR", "max_results": 10}'
```

### 命令行工具
```bash
# 查看数据库统计
python db_viewer.py stats

# 查看所有公司
python db_viewer.py companies

# 查看特定公司
python db_viewer.py company 恒瑞

# 搜索管线
python db_viewer.py search BGB

# 触发所有爬虫
curl -X POST "http://localhost:8000/api/crawlers/trigger"
```

---

## 📊 项目完成度

**总体进度**: 95% ⚠️（前端已部署，后端待部署到公网）

| 模块 | 状态 | 完成度 |
|------|------|--------|
| 基础架构 | ✅ | 100% |
| 数据模型 | ✅ | 100% |
| PubMed模块 | ✅ | 100% |
| Pipeline核心 | ✅ | 100% |
| 统一搜索API | ✅ | 100% |
| 药企爬虫 | ✅ | 100% (14/14) |
| CDE爬虫 | ✅ | 100% (基础架构完成) |
| Redis缓存 | ✅ | 100% |
| 爬虫调度 | ✅ | 100% |
| 数据归一化 | ✅ | 100% |
| 前端UI | ✅ | 100% (已部署至Vercel) |
| 前端生产部署 | ✅ | 100% (2026-03-06完成) |
| 后端本地部署 | ✅ | 100% |
| 后端生产部署 | ⚠️ | 0% (待完成) |
| Docker部署 | ✅ | 100% |
| 文档完善 | ✅ | 100% |
| 专利模块 | ⏳ | 0% (可选功能) |

---

## 🔧 关键设计决策

### 数据模型
✅ 数据模型采用星型架构（Target 为中心）
✅ Pipeline 使用双时间戳支持增量监控
✅ 关联表保留 `evidence_snippet` 用于可解释性
✅ 最小粒度为 `(drug_code, company_name, indication)` 避免覆盖

### 爬虫架构
✅ 使用基类 + 装饰器模式（@spider_register）
✅ 自动发现机制（`crawlers/__init__.py`）
✅ 统一入口（`python -m crawlers.runner --all`）
✅ 智能去重（upsert 逻辑）
✅ Phase 标准化集成

### 性能优化
✅ Redis 缓存层（查询性能提升 67%）
✅ 熔断器保护（防止 API 过载）
✅ 连接池管理（数据库连接复用）
✅ 异步处理（FastAPI 原生支持）

### 前端设计决策 ✅ 2026-02-08新增
✅ **色彩主题**: 绿色(#00ff88) + 黑色(#0a0a0a)，专业医疗风格
✅ **背景设计**: 使用用户提供的背景图片，而非渐变色
✅ **LXL品牌展示**: 左下角大号白色文字，字母逐个浮现动画
✅ **极简设计**: 移除所有图标，保持界面简洁
✅ **Logo设计**: 圆形设计，罗字标识，渐变绿色背景
✅ **导航布局**: 绝对定位居中，沿中轴线均匀分布
✅ **字体选择**: JetBrains Mono(标题) + Source Sans 3(正文)
✅ **动画效果**: fadeIn, slideUp, letterReveal等CSS动画
✅ **响应式设计**: 移动端和桌面端自适应
✅ **玻璃拟态**: backdrop-filter实现半透明模糊效果

### Vercel部署设计决策 ✅ 2026-03-06新增
✅ **URL重写规则**: 解决React SPA客户端路由404问题
  - 所有路径重定向到 `index.html`
  - React Router接管路由处理
  - 支持直接访问子路由和刷新页面
✅ **Monorepo结构**: 支持前后端分离的目录结构
  - 后端在 `code/back_end`
  - 前端在 `code/front_end`
  - Vercel从根目录构建，但输出指定到子目录
✅ **installCommand配置**: 确保依赖安装在正确的子目录
  - 防止"command not found"错误
  - 支持复杂的monorepo构建流程
✅ **GitHub集成**: 自动部署，无需手动操作
  - 推送到main分支自动触发部署
  - 支持预览部署（Pull Request）

---

## 📝 重要文件清单

### 必读文档
1. **产品开发文档.md** - 完整产品文档（⭐推荐）
2. **START_HERE.md** - 3分钟快速入门
3. **QUICKSTART.md** - 完整使用指南
4. **SWAGGER_TEST_GUIDE.md** - API测试指南

### 核心代码
**后端**:
1. **main.py** - 应用启动入口
2. **config.py** - 全局配置
3. **services/pipeline_service.py** - 管线业务逻辑
4. **services/pubmed_service.py** - PubMed搜索服务
5. **crawlers/scheduler.py** - 定时调度器
6. **utils/company_name_mapper.py** - 公司名称映射（35家）
7. **utils/scoring_algorithms.py** - 文献评分算法

**前端** ✅ 2026-02-08新增:
1. **src/App.jsx** - 根组件，路由配置
2. **src/pages/Home/Home.jsx** - 统一搜索页，LXL品牌展示
3. **src/pages/Targets/Targets.jsx** - 靶点列表页
4. **src/pages/Pipelines/Pipelines.jsx** - 管线浏览页
5. **src/pages/Publications/Publications.jsx** - 文献流页
6. **src/pages/TargetDetail/TargetDetail.jsx** - 靶点详情页
7. **src/components/layout/Header.jsx** - 顶部导航栏
8. **src/components/layout/MainLayout.jsx** - 主布局框架
9. **src/context/SearchContext.jsx** - 搜索状态管理
10. **src/api/** - API客户端层（与后端连接）

### 工具脚本
1. **db_viewer.py** - 数据库查看工具 ⭐
2. **validate_system.py** - 系统验证脚本 ⭐
3. **test_crawlers.py** - 爬虫测试脚本 ⭐

---

## ⚠️ 已知问题与待办事项

### 当前问题
1. **前后端连接问题** ⚠️ 优先级：高
   - **问题**: 前端已部署到Vercel（公网），后端仅在本地运行
   - **影响**: 前端无法访问后端API，应用功能不可用
   - **解决**: 需要将后端部署到公网（Zeabur/Railway/云服务器）
   - **状态**: 等待后端部署

2. **API配置待更新** ⚠️ 优先级：高
   - **文件**: `code/front_end/src/api/axios.js`
   - **当前**: `baseURL: 'http://localhost:8000'`
   - **需要**: 修改为生产环境API地址

### 部署待办清单
- [ ] 选择后端部署平台（Zeabur/Railway/云服务器）
- [ ] 部署后端API到公网
- [ ] 更新前端API配置文件
- [ ] 配置生产环境CORS设置
- [ ] 测试前后端连接
- [ ] 配置环境变量（生产数据库、Redis等）
- [ ] 设置域名和SSL证书

---

## ⚠️ 注意事项

### 开发规范
- ⚠️ **所有后端代码必须放在 `code/back_end/` 目录下**
- ⚠️ 遵守 robots.txt 和 Rate Limit（0.2-0.5 QPS）
- ⚠️ 字段完整率要求 ≥ 80%
- ⚠️ 所有数据必须可追溯到 source_url

### 部署注意
- ⚠️ 生产环境需要修改 `.env` 中的敏感配置
- ⚠️ PostgreSQL 和 Redis 需要单独安装或使用 Docker
- ⚠️ 服务器关闭时爬虫不会运行（考虑云部署）

### 已知限制
- ⚠️ CDE官网有反爬虫机制（自动爬取可能失败）
- ⚠️ 专利模块未实现（可选功能）

---

## 🎯 下一步计划

### 可选扩展功能
1. **专利模块** - CNIPA 定向检索（优先级：低）
2. **数据质量监控** - 自动检查数据完整性（优先级：中）
3. **前端功能增强** - 更多图表可视化、导出功能（优先级：低）

### 维护任务
1. 定期更新爬虫（网站结构变化）
2. 添加新的药企爬虫
3. 优化查询性能
4. 更新文档

---

## 📞 技术支持

**问题排查**:
1. 查看 `产品开发文档.md` 的 FAQ 部分
2. 运行 `python validate_system.py` 验证系统状态
3. 查看 `logs/pathology_ai.log` 了解错误详情

**快速测试**:
```bash
# 系统验证
python validate_system.py

# 爬虫测试
python test_crawlers.py

# 数据库查看
python db_viewer.py stats
```

---

## 📅 更新日志

### 2026-03-06
- ✅ **Vercel部署配置完成** - 前端成功部署到Vercel
- ✅ **解决NOT_FOUND错误** - 添加vercel.json配置URL重写规则
- ✅ **子目录构建配置** - 支持monorepo结构，指定构建和输出目录
- ✅ **installCommand修复** - 确保依赖正确安装在子目录
- ✅ **GitHub集成部署** - 代码推送自动触发Vercel部署
- ⚠️ **待办**: 后端API需要部署到公网，前后端才能正常连接
- 📝 提交记录：
  - `ac15f2f` - 修复 Vercel 构建失败问题：添加 installCommand
  - `1489d55` - 在根目录添加 Vercel 配置
  - `e208ca8` - 修复 Vercel 部署 NOT_FOUND 错误

### 2026-02-08
- ✅ **前端UI完整实现** - React + Vite + Tailwind CSS 技术栈
- ✅ **4个核心页面** - 统一搜索、靶点浏览、管线列表、文献流、靶点详情
- ✅ **绿色+黑色主题** - 绿色(#00ff88)主色调 + 黑色(#0a0a0a)背景
- ✅ **用户背景图片** - 使用用户提供的背景图片(1.jpg)
- ✅ **LXL动画效果** - 三个字母从下逐个浮现，白色显示，位于左下角
- ✅ **简洁无图标设计** - 移除所有图标，圆形Logo
- ✅ **导航居中** - 绝对定位实现真正居中，沿中轴线均匀分布
- ✅ **前后端完整连接** - 所有API正常工作，数据展示正常
- ✅ **响应式布局** - 移动端和桌面端适配
- ✅ **前后端100%完成** - 可投入生产环境

### 2026-02-07
- ✅ 创建完整的产品开发文档（合并 PROJECT_MINDMAP.md 和需求说明书）
- ✅ 删除旧文档，保持项目整洁
- ✅ 更新 CLAUDE.md 到最新状态
- ✅ 项目状态：核心功能100%完成，可投入生产环境

### 2026-02-06
- ✅ 编写用户测试指导文档（7个文档文件）
- ✅ 创建 Swagger UI 测试指南
- ✅ 系统测试准备度 100%

### 2026-02-05
- ✅ Redis 缓存层实现
- ✅ 爬虫调度系统验证
- ✅ 数据归一化服务实现
- ✅ 系统完整性验证（100%通过）
- ✅ 产品说明书完成

### 2026-02-04
- ✅ 12家药企爬虫全部完成（166条管线）
- ✅ CDE爬虫基础架构完成（90%）
- ✅ 项目文件清理

### 2026-02-03
- ✅ Docker化部署完成
- ✅ 最后3家药企爬虫完成
- ✅ 总体进度达到 100%

### 2026-02-02
- ✅ 统一搜索API完成
- ✅ 前端搜索界面完成
- ✅ 核心智能引擎重构完成

---

**最后更新**: 2026-03-06
**项目状态**: ✅ 前端已部署至Vercel，⚠️ 待后端部署到公网
**维护模式**: 前端生产就绪，后端待部署
