from fastapi import FastAPI, Request, HTTPException, status
from contextlib import asynccontextmanager  # 异步上下文管理器
from fastapi.middleware.cors import CORSMiddleware  # cors中间件
from .database import init_db, engine  # 初始化数据库, 获取session, 引擎
from .config import settings  # 配置文件
# pip install starlette itsdangerous
from starlette.middleware.sessions import SessionMiddleware  # 会话中间件
from .router import users  # 路由

# 在应用启动时, 调用init_db函数, 来执行create_all, 完成后自动关闭
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
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
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key, max_age=60)


# 给应用包含的路由对象
app.include_router(users.router)
