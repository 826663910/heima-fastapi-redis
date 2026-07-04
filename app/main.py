from fastapi import FastAPI, Request, HTTPException, status
from contextlib import asynccontextmanager  # 异步上下文管理器
from fastapi.middleware.cors import CORSMiddleware  # cors中间件
from .database import init_db, engine  # 初始化数据库, 获取session, 引擎
from .config import settings  # 配置文件
# pip install starlette itsdangerous
from starlette.middleware.sessions import SessionMiddleware  # 会话中间件
from .router import users, shop, order, voucher  # 路由
# pip install redis
import redis.asyncio as redis   # 异步redis
import asyncio  # 异步io
from .config import settings    # 导入配置文件


# 在应用启动时, 调用init_db函数, 来执行create_all, 完成后自动关闭
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------- 启动阶段 ----------
    # 1. 初始化数据库
    await init_db()

    # 2. 初始化redis连接池, 异步环境
    pool = redis.BlockingConnectionPool.from_url(
        f"redis://{settings.redis_ip}:{settings.redis_port}/{settings.redis_db}", 
        password=f'{settings.redis_password}', 
        decode_responses=True, 
        max_connections=500,       # 最大连接数
        socket_timeout=3,          # 收发数据（读/写）的超时时间
        socket_connect_timeout=3,  # 建立 TCP 连接的超时
        timeout=2,                 # 连接池, 连接满载时, 阻塞超时时间
        health_check_interval=30,  # 健康检查间隔
        socket_keepalive=True      # 是否开启SO_KEEPALIVE
        )
    
    # 3. 创建异步redis客户端, 并测试连接,  
    app.state.redis = redis.Redis(connection_pool=pool)
    try:
        await app.state.redis.ping()
        print("异步Redis连接成功")

        # # 缓存预热
        # preload_count = min(300, pool.max_connections)  
        # if preload_count > 0:
        #     print(f"开始预热 Redis 连接池 (预创建 {preload_count} 个连接)...")
        #     # 并发执行 ping 命令，每个 ping 都会从池中借用一个连接，
        #     # 命令执行完后连接自动归还到池中，但此时 TCP 连接已经建立好并保持活跃
        #     await asyncio.gather(*[app.state.redis.ping() for _ in range(preload_count)])
        #     print("Redis 连接池预热完成！")

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
app.include_router(users.router)    # 用户
app.include_router(shop.router)     # 店铺
app.include_router(order.router)    # 订单
app.include_router(voucher.router)  # 代金券

