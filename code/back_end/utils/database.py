"""
=====================================================
数据库连接工具
=====================================================

提供数据库连接池管理和会话管理
使用 SQLAlchemy ORM
=====================================================
"""

from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from loguru import logger

from config import get_settings

# 获取配置
settings = get_settings()

# =====================================================
# SQLAlchemy 全局配置
# =====================================================

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_size=settings.DB_POOL_SIZE,           # 连接池大小
    max_overflow=settings.DB_MAX_OVERFLOW,      # 最大溢出连接数
    pool_timeout=settings.DB_POOL_TIMEOUT,      # 连接超时
    pool_recycle=settings.DB_POOL_RECYCLE,      # 连接回收时间（秒）
    echo=settings.DEBUG,                         # 是否打印SQL（开发模式）
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类（ORM模型继承此类）
Base = declarative_base()


# =====================================================
# 数据库会话管理
# =====================================================

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入）

    使用方式（FastAPI路由中）：
        @app.get("/api/targets")
        def get_targets(db: Session = Depends(get_db)):
            return db.query(Target).all()

    特性：
    - 自动管理会话生命周期
    - 使用后自动关闭
    - 异常时自动回滚
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    获取数据库会话（上下文管理器）

    使用方式（脚本/爬虫中）：
        with get_db_context() as db:
            targets = db.query(Target).all()

    特性：
    - 支持with语句
    - 自动提交或回滚
    - 异常安全
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        db.close()


# =====================================================
# 数据库初始化
# =====================================================

def init_database():
    """
    初始化数据库
    - 创建所有表（如果不存在）
    - 建议在应用启动时调用一次
    """
    try:
        logger.info("正在初始化数据库...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库初始化成功")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


def drop_database():
    """
    删除所有表（⚠️ 危险操作，仅开发环境使用）
    """
    try:
        logger.warning("正在删除所有表...")
        Base.metadata.drop_all(bind=engine)
        logger.warning("✅ 所有表已删除")
    except Exception as e:
        logger.error(f"❌ 删除表失败: {e}")
        raise


# =====================================================
# 数据库健康检查
# =====================================================

def check_database_connection() -> bool:
    """
    检查数据库连接是否正常

    返回：
        bool: True=连接正常，False=连接失败
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ 数据库连接正常")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False


# =====================================================
# 测试
# =====================================================

if __name__ == "__main__":
    """
    测试数据库连接
    """
    from config import settings

    print("=" * 60)
    print("数据库连接测试")
    print("=" * 60)
    print(f"数据库地址: {settings.database_url}")
    print(f"连接池大小: {settings.DB_POOL_SIZE}")
    print("=" * 60)

    # 测试连接
    if check_database_connection():
        print("✅ 数据库连接成功！")
        print("\n下一步：")
        print("1. 执行 SQL 脚本创建表：")
        print("   psql -U {user} -d {db} -f code/database/migrations/001_create_initial_tables.sql".format(
            user=settings.DB_USER,
            db=settings.DB_NAME
        ))
        print("2. 或使用 init_database() 通过ORM创建表（开发环境）")
    else:
        print("❌ 数据库连接失败！")
        print("\n请检查：")
        print("1. PostgreSQL 是否已启动")
        print("2. 数据库用户名密码是否正确")
        print("3. .env 文件配置是否正确")

    print("=" * 60)
