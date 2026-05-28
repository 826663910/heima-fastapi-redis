from fastapi import FastAPI, Request, HTTPException, status
from contextlib import asynccontextmanager  # 异步上下文管理器
from fastapi.middleware.cors import CORSMiddleware  # cors中间件
from .database import init_db, engine  # 初始化数据库, 获取session, 引擎
from .config import settings  # 配置文件
# pip install starlette itsdangerous
from starlette.middleware.sessions import SessionMiddleware  # 会话中间件
from .router import users  # 路由
# pip install redis
import redis.asyncio as redis   # 异步redis
from .config import settings    # 导入配置文件

# 在应用启动时, 调用init_db函数, 来执行create_all, 完成后自动关闭
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------- 启动阶段 ----------
    # 1. 初始化数据库
    await init_db()

    # 2. 初始化redis连接池, 异步环境
    pool = redis.ConnectionPool.from_url(
        f"redis://{settings.redis_ip}:{settings.redis_port}/{settings.redis_db}", 
        password=f'{settings.redis_password}', 
        decode_responses=True, 
        max_connections=100,       # 最大连接数
        socket_timeout=3,          # 连接满载时, 等待可用连接的超时时间
        health_check_interval=30,  # 健康检查间隔
        socket_keepalive=True      # 是否开启SO_KEEPALIVE
        )
    
    # 3. 创建异步redis客户端, 并测试连接
    app.state.redis = redis.Redis(connection_pool=pool)
    try:
        await app.state.redis.ping()
        print("异步Redis连接成功")

    except Exception as e:
        print("异步Redis连接失败:", e)

    yield   # 应用运行期间

    # ---------- 停止阶段 ----------
    # 先关闭 Redis
    await app.state.redis.aclose()
    await pool.disconnect()
    # 再关闭数据库引擎
    await engine.dispose()
    

# 启动应用
app = FastAPI(lifespan=lifespan)


"""给应用添加CORS中间件"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


"""给应用添加session中间件"""
# 给应用添加session中间件,使用这个中间件后, 接口就能用request.session保存和获取session了
# SessionMiddleware 必须在 CORS 之前添加
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key, max_age=2 * 60 * 60)

# 给应用包含的路由对象
app.include_router(users.router)
