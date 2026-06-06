from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.encoders import jsonable_encoder  # 序列化
from sqlalchemy.ext.asyncio import AsyncSession  # 异步注解
from sqlalchemy import select   # SQL查询构造器
from ..database import get_db, get_redis    # 获取异步数据库会话和redis客户端
from .. import models, schemas  # 导入模型和模式
import redis.asyncio as redis # 异步redis客户端
from typing import Optional, Annotated, List
import json # 用于序列化和反序列化


router = APIRouter(
    prefix="/shop",
    tags=["SHOP"]
)

# 商铺列表
@router.get("/", response_model=List[schemas.ShopListOut])
async def get_shops(db: Annotated[AsyncSession, '数据库会话', Depends(get_db)],
                    r: Annotated[redis.Redis, 'redis客户端', Depends(get_redis)],
                    category_name: Optional[str]=None, limit: int=10, skip: int=0):
    # 1. 从redis中查询商铺缓存
    shops = await r.get(f"shop:list:cat_{category_name or 'all'}:{limit}:{skip}")

    # 2. 判断是否存在
    if shops:
        # 3. 存在缓存, 直接返回商铺信息
        shops = json.loads(shops)   # 反序列化, 将json字符串, 转为py对象
        return shops

    # 4. 不存在, 查询数据库
    stmt = select(models.Shop).join(models.Category, models.Shop.typeId==models.Category.id)    # 内连接
    # 只有在传入了分类名时才添加 WHERE 条件
    if category_name:
        stmt = stmt.where(models.Category.name==category_name)
    # 排序+分页
    stmt = stmt.order_by(models.Shop.id).limit(limit).offset(skip)
    result = await db.execute(stmt)  # 执行sql
    shops = result.scalars().all()   # 返回所有
    shops = jsonable_encoder(shops)  # 将orm对象, 转为py对象
    shops_json = json.dumps(shops, ensure_ascii=False)   # 序列化, 将py对象, 转为json字符串

    # 5. 写入redis缓存中, 300秒后过期
    await r.setex(f"shop:list:cat_{category_name or 'all'}:{limit}:{skip}", 300, shops_json)

    # 6. 返回商铺信息
    return shops


# 商铺详情
@router.get('/{id}', response_model=schemas.ShopDetailOut)
async def get_shop(id:int, db: Annotated[AsyncSession, '数据库会话', Depends(get_db)], 
                   r: Annotated[redis.Redis, 'redis客户端', Depends(get_redis)]):
    # 1. 从redis中查询商铺缓存
    shop = await r.get(f"shop:detail:{id}")
    # 2. 判断是否存在
    if shop:
        # 3. 存在缓存, 直接返回商铺信息
        shop = json.loads(shop)   # 反序列化, 将json字符串, 转为py对象
        return shop
    
    # 4. 不存在, 根据id查询数据库
    stmt = select(models.Shop).where(models.Shop.id == id)
    result = await db.execute(stmt)
    shop = result.scalar_one_or_none()

    # 5. 查询数据库, 不存在id, 返回错误404
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商铺不存在")
    
    shop = jsonable_encoder(shop)   # 将orm对象, 转为py对象
    shop_json = json.dumps(shop, ensure_ascii=False)   # 序列化, 将py对象, 转为json字符串

    # 6. 存在id, 写入redis缓存中, 300秒后过期
    await r.setex(f"shop:detail:{id}", 300, shop_json)

    # 7. 返回商铺信息
    return shop