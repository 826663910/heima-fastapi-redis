# pip install sqlalchemy[aiomysql]
# 导入异步引擎, 异步会话类, 异步会话工厂
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base    # 声明基类
from typing import AsyncGenerator   # 异步生成器
from .config import settings
# 数据库配置
DATABASE_URL = f"mysql+aiomysql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}"

"""
数据库的max_connections, 最大是151,
公式为: (pool_size + max_overflow) * worker进程数 <= max_connections

查询max_connections的SQL语句:
SHOW VARIABLES LIKE 'max_connections';

临时修改max_connections的SQL语句, 重启SQL失效:
SET GLOBAL max_connections = 500;
"""

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 打印 SQL 语句，生产环境设为 False
    pool_size=10,   # 连接池常驻连接数
    max_overflow=20,    # 额外临时连接数
    pool_recycle=3600,   # 连接池回收时间（秒）
)

# 创建会话工厂
async_session_maker = async_sessionmaker(
    engine,         # 指定引擎  
    class_=AsyncSession,    # 指定使用异步会话类, 异步必须设置这个
    expire_on_commit=False,  # 提交后不使对象过期,避免额外的查询，提升性能
    autoflush=False,        # 关闭自动 flush
    autocommit=False,       # 关闭自动提交（必须显式 commit）
)

# 声明基类
Base = declarative_base()

# 获取异步会话
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            pass

# 在启动时创建数据库表(数据表不存在时, 异步执行create_all)
async def init_db():
    from . import models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
