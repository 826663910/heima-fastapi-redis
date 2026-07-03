from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from redis.asyncio import Redis
from typing import Annotated    # 注解
from ..database import get_redis
import time

# 路由
router = APIRouter(
    prefix='/order',
    tags=['ORDER']
)


# 全局唯一ID生成器
@router.get('/unique_id')
async def globally_unique_id(r: Annotated[Redis, 'redis客户端', Depends(get_redis)], prefix: str='order'):
    # 1. 生成时间戳
    current_time = int(time.time()) - 1640995200
    # 2. 生成序列号
    # 2.1 获取当天日期, 精确到天
    today = datetime.now(timezone.utc).strftime('%Y%m%d')
    # 2.2 自增长
    count = await r.incr(f"icr:{prefix}:{today}")
    # 3. 拼接字符串并返回, int类型
    uid = (current_time << 32) | count  # 左移32位, 右对齐
    return {"id": uid}


    

