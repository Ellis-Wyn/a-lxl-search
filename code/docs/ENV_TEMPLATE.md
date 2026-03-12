# =====================================================
# 病理AI药研情报库 - 环境变量配置模板
# =====================================================
#
# 使用说明：
# 1. 复制此文件到 .env 文件
# 2. 修改配置值（删除行首的 # 和 说明文字）
# 3. 根据实际环境调整参数
#
# 配置优先级：
# - .env 文件 > 环境变量 > config.py 默认值
#
# 注意事项：
# - 不要将包含敏感信息的 .env 文件提交到 Git
# - 生产环境请设置 DEBUG=false
# - 数据库密码请使用强密码
#
# =====================================================

# =====================================================
# 应用基础配置
# =====================================================
APP_NAME="病理AI药研情报库"
APP_VERSION="1.0.0"
DEBUG=true                    # 生产环境设为 false

# =====================================================
# 数据库配置（PostgreSQL）
# =====================================================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=drug_intelligence_db
DB_USER=postgres
DB_PASSWORD=yang051028     # 修改为你的数据库密码

# 数据库连接池配置
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# =====================================================
# PubMed API 配置
# =====================================================
PUBMED_EMAIL=test@example.com     # 必填：你的邮箱地址
PUBMED_API_KEY=                   # 可选：从 https://www.ncbi.nlm.nih.gov/account/ 获取
PUBMED_RATE_LIMIT=3               # 无API密钥时的请求限制

# =====================================================
# 爬虫配置
# =====================================================
CRAWLER_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CRAWLER_TIMEOUT=30
CRAWLER_DELAY=0.5                  # 请求间隔（秒），推荐 0.5-1.0

# 药企官网爬虫
COMPANY_CRAWLER_ENABLED=true       # true=启用, false=禁用
COMPANY_CRAWLER_INTERVAL=24        # 执行间隔（小时）

# CDE平台爬虫
CDE_CRAWLER_ENABLED=true
CDE_CRAWLER_INTERVAL=12            # 执行间隔（小时）

# 专利爬虫
PATENT_CRAWLER_ENABLED=true
PATENT_CRAWLER_INTERVAL=168         # 执行间隔（小时，168=每周）

# =====================================================
# 爬虫调度器配置
# =====================================================
CRAWLER_SCHEDULER_ENABLED=true     # 启用自动调度
CRAWLER_SCHEDULER_TIME="02:00"     # 执行时间（24小时制 HH:MM）
CRAWLER_SCHEDULER_MAX_CONCURRENT=3 # 最大并发爬虫数（建议 2-5）
CRAWLER_SCHEDULER_TIMEZONE="Asia/Shanghai"

# =====================================================
# 爬虫重试配置
# =====================================================
CRAWLER_RETRY_ENABLED=true
CRAWLER_RETRY_MAX_ATTEMPTS=3
CRAWLER_RETRY_BASE_DELAY=60.0       # 基础延迟（秒）
CRAWLER_RETRY_BACKOFF_FACTOR=5.0    # 退避因子
CRAWLER_RETRY_MAX_DELAY=900.0       # 最大延迟（15分钟）

# =====================================================
# 预警配置
# =====================================================
# Phase Jump 预警
ALERT_PHASE_JUMP_ENABLED=true       # 启用 Phase Jump 预警
ALERT_PHASE_JUMP_PHASES=["II", "III"]  # 监控的阶段跳转

# 竞品退场预警
ALERT_DISAPPEARED_THRESHOLD=21     # 连续21天未抓取到即预警
ALERT_DISAPPEARED_CHECK_ENABLED=true

# 新入局者预警
ALERT_NEW_ENTRY_ENABLED=true

# =====================================================
# 数据处理配置
# =====================================================
# 文献排序权重
WEIGHT_RECENCY_DAYS=730           # 考虑最近730天（24个月）
WEIGHT_RECENCY_RATIO=0.7           # 时间权重占比

# 临床数据加分
SCORE_CLINICAL_DATA=50            # 有临床数据加分
SCORE_PHASE_III=40                # Phase III 加分
SCORE_FIRST_IN_CLASS=30           # 首创药加分

# 综述减分
SCORE_REVIEW=-10                  # 综述减分
SCORE_CASE_REPORT=-20             # 病例报告减分

# =====================================================
# Redis 缓存配置
# =====================================================
REDIS_ENABLED=true                # 启用Redis缓存
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=                   # Redis密码（如需要）

# 缓存TTL配置（秒）
REDIS_TTL_PUBMED=7200             # PubMed缓存：2小时
REDIS_TTL_SEARCH=1800             # 搜索缓存：30分钟
REDIS_TTL_PIPELINE=3600           # 管线缓存：1小时
REDIS_TTL_CDE=86400               # CDE缓存：24小时
REDIS_TTL_DEFAULT=3600           # 默认缓存：1小时

# =====================================================
# 日志配置
# =====================================================
LOG_LEVEL=INFO                    # 日志级别：DEBUG/INFO/WARNING/ERROR
LOG_FILE=logs/app.log

# =====================================================
# CORS 配置
# =====================================================
CORS_ORIGINS=["*"]                # 允许的来源（开发环境用 "*"）
CORS_CREDENTIALS=true
CORS_METHODS=["*"]
CORS_HEADERS=["*"]

# =====================================================
# API 限流配置（可选）
# =====================================================
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=60

# =====================================================
# 配置说明
# =====================================================
#
# 【数据库配置】
# - DB_HOST: 数据库服务器地址，本地用 localhost
# - DB_PORT: PostgreSQL 默认端口 5432
# - DB_NAME: 数据库名称
# - DB_USER: 数据库用户名
# - DB_PASSWORD: 数据库密码（请修改）
#
# 【PubMed配置】
# - PUBMED_EMAIL: 必须提供，NCBI 要求
# - PUBMED_API_KEY: 可选，有密钥每秒可发10个请求，无密钥只能3个
#
# 【爬虫配置】
# - COMPANY_CRAWLER_ENABLED: 控制药企爬虫总开关
# - CDE_CRAWLER_ENABLED: 控制CDE爬虫开关
# - PATENT_CRAWLER_ENABLED: 控制专利爬虫开关
# - CRAWLER_DELAY: 请求间隔，建议0.5-1.0秒
#
# 【调度器配置】
# - CRAWLER_SCHEDULER_TIME: 24小时制时间，如 "02:00" 表示凌晨2点
# - CRAWLER_SCHEDULER_MAX_CONCURRENT: 并发爬虫数
#   * 开发环境：1-2个
#   * 生产环境：3-5个
#   * 网络较差：1个
#
# 【预警配置】
# - ALERT_PHASE_JUMP_ENABLED: 监控管线阶段跳变（如 I → II）
# - ALERT_DISAPPEARED_THRESHOLD: 多少天未抓到判定为退场
#
# 【Redis配置】
# - 如未安装Redis，可设置 REDIS_ENABLED=false
#
# 【日志配置】
# - DEBUG: 最详细，包含所有调试信息
# - INFO: 一般信息，推荐生产环境使用
# - WARNING: 仅警告和错误
# - ERROR: 仅错误
#
# =====================================================
