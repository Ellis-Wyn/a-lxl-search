"""
=====================================================
配置文件
=====================================================

使用环境变量 + .env 文件管理配置
敏感信息（数据库密码、API密钥）不要提交到 Git
=====================================================
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    应用配置类
    从环境变量或 .env 文件读取配置
    """

    # =====================================================
    # 应用基础配置
    # =====================================================
    APP_NAME: str = "病理AI药研情报库"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # =====================================================
    # 数据库配置
    # =====================================================
    DATABASE_URL: str = ""  # 可选：完整的数据库连接URL（优先于单独的配置）
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "drug_intelligence_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"

    # 数据库连接池
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # =====================================================
    # PubMed API 配置
    # =====================================================
    PUBMED_API_KEY: str = ""  # 可选：从 https://www.ncbi.nlm.nih.gov/account/ 获取
    PUBMED_EMAIL: str = ""    # 必填：NCBI 要求提供邮箱
    PUBMED_TOOL: str = "A_lxl_search"

    # PubMed Rate Limit
    PUBMED_RATE_LIMIT: int = 3  # 每秒请求数（无API Key时限制为3）
    PUBMED_MAX_RETRIES: int = 3

    # =====================================================
    # 爬虫配置
    # =====================================================
    # 通用爬虫设置
    CRAWLER_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    CRAWLER_TIMEOUT: int = 30  # 秒
    CRAWLER_DELAY: float = 0.3  # 请求间隔（秒），遵守 Rate Limit

    # 药企官网爬虫
    COMPANY_CRAWLER_ENABLED: bool = True
    COMPANY_CRAWLER_INTERVAL: int = 24  # 小时：每24小时爬一次

    # CDE 平台爬虫
    CDE_CRAWLER_ENABLED: bool = True
    CDE_CRAWLER_INTERVAL: int = 12  # 小时：每12小时爬一次

    # 专利爬虫
    PATENT_CRAWLER_ENABLED: bool = True
    PATENT_CRAWLER_INTERVAL: int = 168  # 小时：每周爬一次

    # =====================================================
    # 爬虫调度器配置
    # =====================================================
    CRAWLER_SCHEDULER_ENABLED: bool = True          # 是否启用调度器
    CRAWLER_SCHEDULER_TIME: str = "02:00"          # 调度时间（24小时制，HH:MM）
    CRAWLER_SCHEDULER_MAX_CONCURRENT: int = 3      # 最大并发爬虫数
    CRAWLER_SCHEDULER_TIMEZONE: str = "Asia/Shanghai"  # 时区

    # =====================================================
    # CDE 爬虫配置
    # =====================================================
    CDE_CRAWLER_ENABLED: bool = True               # 是否启用CDE爬虫
    CDE_CRAWLER_BASE_URL: str = "https://www.cde.org.cn"  # CDE官网
    CDE_CRAWLER_INFO_URL: str = "https://www.cde.org.cn/main/xxgk/"  # 信息公开页面
    CDE_CRAWLER_INTERVAL_HOURS: int = 12           # 调度间隔（小时）
    CDE_CRAWLER_RATE_LIMIT: float = 0.3            # 请求频率限制（QPS）

    # =====================================================
    # 爬虫重试配置
    # =====================================================
    CRAWLER_RETRY_ENABLED: bool = True                    # 是否启用重试
    CRAWLER_RETRY_MAX_ATTEMPTS: int = 3                   # 最大重试次数
    CRAWLER_RETRY_BASE_DELAY: float = 60.0                # 基础延迟（秒）
    CRAWLER_RETRY_BACKOFF_FACTOR: float = 5.0             # 退避因子
    CRAWLER_RETRY_MAX_DELAY: float = 900.0                # 最大延迟（15分钟）

    # =====================================================
    # 爬虫执行历史配置
    # =====================================================
    CRAWLER_EXECUTION_LOG_RETENTION_DAYS: int = 90        # 执行日志保留天数
    CRAWLER_EXECUTION_LOG_ENABLED: bool = True            # 是否记录执行历史

    # =====================================================
    # 爬虫告警配置
    # =====================================================
    CRAWLER_ALERT_CONSECUTIVE_FAILURES: int = 3           # 连续失败N次触发告警
    CRAWLER_ALERT_ENABLED: bool = True                    # 是否启用告警
    CRAWLER_ALERT_COOLDOWN_MINUTES: int = 60              # 告警冷却时间（分钟）

    # =====================================================
    # Pipeline 监控配置
    # =====================================================
    PIPELINE_DISAPPEARED_THRESHOLD_DAYS: int = 21         # 竞品退场阈值（天）
    PIPELINE_DISAPPEARED_CHECK_ENABLED: bool = True       # 是否启用竞品退场检测
    PIPELINE_AUTO_DISCOVER_URL_ENABLED: bool = True       # 是否启用URL自动发现

    # =====================================================
    # 数据处理配置
    # =====================================================
    # 文献排序权重
    WEIGHT_RECENCY_DAYS: int = 730  # 近24个月（730天）
    WEIGHT_RECENCY_RATIO: float = 0.7  # 时间权重占比

    # 临床数据加分
    SCORE_CLINICAL_DATA: int = 50
    SCORE_PHASE_III: int = 40
    SCORE_FIRST_IN_CLASS: int = 30

    # 综述减分
    SCORE_REVIEW: int = -10
    SCORE_CASE_REPORT: int = -20

    # =====================================================
    # Redis 缓存配置
    # =====================================================
    REDIS_ENABLED: bool = True                    # 是否启用缓存
    REDIS_HOST: str = "localhost"                # Redis 主机
    REDIS_PORT: int = 6379                       # Redis 端口
    REDIS_DB: int = 0                            # Redis 数据库编号
    REDIS_PASSWORD: str = ""                     # Redis 密码（如果需要）
    REDIS_URL: str = ""                          # 完整连接URL（优先于单独配置）

    # 缓存 TTL 配置（秒）
    REDIS_TTL_PUBMED: int = 7200                 # PubMed 缓存：2小时
    REDIS_TTL_SEARCH: int = 1800                 # 搜索缓存：30分钟
    REDIS_TTL_PIPELINE: int = 3600               # 管线缓存：1小时
    REDIS_TTL_CDE: int = 86400                   # CDE 缓存：24小时
    REDIS_TTL_DEFAULT: int = 3600                # 默认缓存：1小时

    # 缓存键前缀
    REDIS_KEY_PREFIX: str = "pathology_ai"

    # =====================================================
    # 预警配置
    # =====================================================
    # Phase Jump 预警
    ALERT_PHASE_JUMP_ENABLED: bool = True
    ALERT_PHASE_JUMP_PHASES: list = ["II", "III"]  # 监控 Phase II → III

    # 竞品退场预警
    ALERT_DISAPPEARED_THRESHOLD: int = 21  # 天：连续21天（3周）抓不到

    # 新入局者预警
    ALERT_NEW_ENTRY_ENABLED: bool = True

    # =====================================================
    # CORS 配置
    # =====================================================
    CORS_ORIGINS: list = ["*"]  # MVP 阶段允许所有来源
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]

    # =====================================================
    # 日志配置
    # =====================================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "30 days"

    # =====================================================
    # API 限流配置（V1）
    # =====================================================
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def database_url(self) -> str:
        """
        构建数据库连接 URL
        优先使用 DATABASE_URL 环境变量，否则从单独配置构建
        格式：postgresql://user:password@host:port/dbname 或 sqlite:///./path/to/db.db
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def redis_url(self) -> str:
        """
        构建 Redis 连接 URL
        优先使用 REDIS_URL 环境变量，否则从单独配置构建
        格式：redis://[[password>@]host[:port]]/[db]
        """
        if self.REDIS_URL:
            return self.REDIS_URL

        # 构建 Redis URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        else:
            return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def async_database_url(self) -> str:
        """
        构建异步数据库连接 URL
        格式：postgresql+asyncpg://user:password@host:port/dbname
        """
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        """
        Pydantic 配置
        """
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的环境变量


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例

    使用方式：
        from config import get_settings
        settings = get_settings()
        print(settings.database_url)
    """
    return Settings()


# =====================================================
# 导出
# =====================================================

settings = get_settings()

# =====================================================
# 测试
# =====================================================

if __name__ == "__main__":
    # 打印所有配置
    print("=" * 60)
    print("配置信息（用于调试）")
    print("=" * 60)
    print(f"应用名称: {settings.APP_NAME}")
    print(f"数据库: {settings.database_url}")
    print(f"PubMed Email: {settings.PUBMED_EMAIL}")
    print(f"爬虫延迟: {settings.CRAWLER_DELAY}秒")
    print("=" * 60)
