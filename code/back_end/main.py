"""
=====================================================
病理AI药研情报库 - FastAPI 主应用
=====================================================

项目：以 Target（靶点）为中心的药研竞争情报平台
核心功能：PubMed文献 + 公司管线的聚合与竞争情报分析

作者：A_lxl_search Team
创建日期：2026-01-29
更新日期：2026-01-30 (集成基础设施层)
=====================================================
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# 核心基础设施
from core.logger import setup_logger, get_logger, bind_context
from core.error_handlers import register_exception_handlers
from core.middleware import setup_middlewares
from core.container import init_container, get_container
from core.circuit_breaker import get_circuit_breaker_manager

# 配置
from config import settings

# 初始化日志
setup_logger(
    app_name="pathology_ai",
    log_level="INFO",
    json_logs=not settings.DEBUG,
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    - 启动时：初始化基础设施、数据库连接、服务容器
    - 关闭时：清理资源
    """
    # ==================== 启动阶段 ====================
    logger.info("=" * 60)
    logger.info("🚀 病理AI药研情报库启动中...")
    logger.info("=" * 60)

    # 1. 初始化服务容器
    container = init_container(app)
    logger.info("✓ 服务容器初始化完成")

    # 2. 测试数据库连接（可选）
    try:
        from utils.database import check_database_connection
        if check_database_connection():
            logger.info("✓ 数据库连接正常")
        else:
            logger.warning("⚠ 数据库连接失败（部分功能可能不可用）")
    except Exception as e:
        logger.warning(f"⚠ 数据库连接检查失败: {e}")

    # 3. 初始化并启动爬虫调度器
    try:
        from crawlers.scheduler import init_scheduler
        scheduler = init_scheduler()
        await scheduler.start()
        logger.info("✓ 爬虫调度器已启动")
    except Exception as e:
        logger.error(f"✗ 爬虫调度器启动失败: {e}")

    # 3. 显示配置信息
    logger.info(f"📊 数据模型：5张主表 + 2张关联表")
    logger.info(f"🔍 核心功能：PubMed + Pipeline + 情报分析")
    logger.info(f"🌍 运行环境：{'生产' if not settings.DEBUG else '开发'}")

    logger.info("=" * 60)
    logger.info("✓ 应用启动完成，开始服务请求")
    logger.info("=" * 60)

    yield

    # ==================== 关闭阶段 ====================
    logger.info("=" * 60)
    logger.info("👋 病理AI药研情报库关闭中...")
    logger.info("=" * 60)

    # 1. 关闭爬虫调度器
    try:
        from crawlers.scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.shutdown()
            logger.info("✓ 爬虫调度器已关闭")
    except Exception as e:
        logger.error(f"✗ 爬虫调度器关闭失败: {e}")

    # 2. 关闭服务容器
    try:
        await container.close_async()
        logger.info("✓ 服务容器已关闭")
    except Exception as e:
        logger.error(f"✗ 服务容器关闭失败: {e}")

    # 2. 显示熔断器状态
    try:
        manager = get_circuit_breaker_manager()
        states = manager.get_states()
        if states:
            logger.info(f"📊 熔断器状态: {states}")
    except Exception as e:
        logger.warning(f"⚠ 无法获取熔断器状态: {e}")

    logger.info("=" * 60)
    logger.info("✓ 应用已关闭")
    logger.info("=" * 60)


# 创建 FastAPI 应用
app = FastAPI(
    title="病理AI药研情报库 API",
    description="""
    以靶点（Target）为中心的药研竞争情报平台

    ## 核心功能
    - **靶点管理**：查询靶点信息、别名、Gene ID
    - **文献聚合**：PubMed 文献智能查询与排序
    - **管线监控**：公司管线动态、Phase Jump 预警
    - **CDE事件跟踪**：药审中心 IND/NDA 受理与审评信息
    - **统一搜索**：跨管线、文献、靶点、CDE事件的一站式搜索
    - **竞争分析**：靶点对比、First-mover 识别

    ## 数据模型
    - Target（靶点）: 核心锚点
    - Publication（文献）: PubMed 科学证据
    - Pipeline（管线）: 产业界研发进度
    - CDEEvent（CDE事件）: 药审中心受理与审评信息

    ## 基础设施
    - **错误处理**：统一的异常处理和错误响应
    - **日志系统**：结构化日志，支持请求追踪
    - **重试机制**：指数退避重试
    - **熔断器**：保护下游服务
    - **依赖注入**：服务容器管理
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ==================== 注册基础设施 ====================

# 1. 注册异常处理器
register_exception_handlers(app)
logger.info("✓ 异常处理器已注册")

# 2. 注册中间件
setup_middlewares(app)
logger.info("✓ 中间件已注册")

# =====================================================
# 健康检查 & 基础接口
# =====================================================

@app.get("/", tags=["基础"])
async def root():
    """
    根路径：欢迎信息
    """
    return {
        "message": "病理AI药研情报库 API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get("/health", tags=["基础"])
async def health_check():
    """
    健康检查：用于监控服务状态
    """
    # 检查数据库连接
    db_status = "unknown"
    try:
        from utils.database import check_database_connection
        db_connected = check_database_connection()
        db_status = "connected" if db_connected else "disconnected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # 获取熔断器状态
    circuit_breaker_status = {}
    try:
        manager = get_circuit_breaker_manager()
        circuit_breaker_status = manager.get_states()
    except Exception:
        pass

    return {
        "status": "healthy",
        "service": "A_lxl_search API",
        "version": "1.0.0",
        "database": db_status,
        "circuit_breakers": circuit_breaker_status,
        "features": {
            "pubmed": "已实现",
            "company_pipeline": "已实现",
            "cde": "已实现",
            "unified_search": "已实现",
            "normalization": "待实现",
        }
    }


# =====================================================
# API 路由
# =====================================================

# PubMed 路由
from api.pubmed import router as pubmed_router
app.include_router(pubmed_router)
logger.info("✓ PubMed 路由已注册")

# Pipeline 路由
from api.pipeline import router as pipeline_router
app.include_router(pipeline_router)
logger.info("✓ Pipeline 路由已注册")

# Targets 路由
from api.targets import router as targets_router
app.include_router(targets_router)
logger.info("✓ Targets 路由已注册")

# Publications 路由
from api.publications import router as publications_router
app.include_router(publications_router)
logger.info("✓ Publications 路由已注册")

# 统一搜索 路由
from api.search import router as search_router
app.include_router(search_router)
logger.info("✓ 统一搜索 路由已注册")

# 爬虫管理 路由
from api.crawlers import router as crawlers_router
app.include_router(crawlers_router)
logger.info("✓ 爬虫管理 路由已注册")

# 爬虫执行历史 路由
from api.crawler_execution import router as crawler_execution_router
app.include_router(crawler_execution_router)
logger.info("✓ 爬虫执行历史 路由已注册")

# CDE 事件 路由
from api.cde import router as cde_router
app.include_router(cde_router)
logger.info("✓ CDE 事件 路由已注册")

# 静态文件服务
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info("✓ 静态文件服务已注册")


# =====================================================
# 示例接口（测试用）
# =====================================================

@app.get("/api/example/target/{target_name}", tags=["示例"])
async def get_target_example(target_name: str):
    """
    示例：查询靶点信息（模拟数据）

    实际功能待实现：
    - 查询数据库 Target 表
    - 返回靶点基础信息
    - 关联的文献和管线
    """
    # 模拟数据
    example_data = {
        "target_id": "550e8400-e29b-41d4-a716-446655440000",
        "standard_name": target_name.upper() if target_name.isupper() else target_name,
        "aliases": ["HER2", "ERBB2", "c-ErbB2"],
        "gene_id": "2064",
        "uniprot_id": "P04626",
        "description": f"{target_name} 靶点的示例数据",
        "stats": {
            "total_publications": 150,
            "total_pipelines": 12,
            "phase_iii_count": 3
        },
        "note": "这是模拟数据，实际功能待实现数据库连接后生效"
    }

    return example_data


@app.get("/api/example/publications", tags=["示例"])
async def search_publications_example(
    target: str = "EGFR",
    limit: int = 10,
    days_ago: int = 365
):
    """
    示例：搜索PubMed文献（模拟数据）

    实际功能待实现：
    - 调用 PubMed API
    - 智能查询转换
    - 加权排序（时间+临床数据）
    """
    # 模拟数据
    example_data = {
        "query": target,
        "total": 120,
        "filters": {
            "days_ago": days_ago,
            "limit": limit
        },
        "results": [
            {
                "pmid": "12345678",
                "title": f"Phase III trial of {target} inhibitor in NSCLC",
                "journal": "J Clin Oncol",
                "pub_date": "2024-01-15",
                "clinical_data": {
                    "ORR": "45.2%",
                    "mPFS": "11.2 months"
                },
                "relevance_score": 92
            },
            {
                "pmid": "87654321",
                "title": f"{target} mutations and resistance mechanisms",
                "journal": "Nature",
                "pub_date": "2023-12-20",
                "publication_type": "Review",
                "relevance_score": 75
            }
        ],
        "note": "这是模拟数据，实际功能待实现 PubMed 爬虫后生效"
    }

    return example_data


# =====================================================
# 启动说明
# =====================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("启动方式：")
    logger.info("1. 开发环境：python main.py")
    logger.info("2. 生产环境：uvicorn main:app --host 0.0.0.0 --port 8000")
    logger.info("3. 自动重载：uvicorn main:app --reload")
    logger.info("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式自动重载
        log_level="info"
    )
