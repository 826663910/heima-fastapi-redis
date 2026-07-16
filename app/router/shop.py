from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.encoders import jsonable_encoder  # 序列化
from sqlalchemy.ext.asyncio import AsyncSession  # 异步注解
from sqlalchemy import select   # SQL查询构造器
from ..database import get_db, get_redis, async_session_maker    # 获取异步数据库会话和redis客户端
from .. import models, schemas, auth  # 导入模型和模式
import redis.asyncio as redis # 异步redis客户端
from typing import Optional, Annotated, List
import json # 用于序列化和反序列化
from random import randint
from redis.exceptions import LockError
import time
import asyncio  # 异步io

router = APIRouter(
    prefix="/shop",
    tags=["SHOP"]
)

# 商铺列表
@router.get("/", response_model=List[schemas.ShopListOut])
async def get_shops(db: Annotated[AsyncSession, '数据库会话', Depends(get_db)],
                    r: Annotated[redis.Redis, 'redis客户端', Depends(get_redis)],
                    current_user: Annotated[dict, '当前用户', Depends(auth.check_login)],
                    category_name: Optional[str]=None, limit: int=10, skip: int=0):
    # 1. 从redis中查询商铺缓存
    shops = await r.get(f"shop:list:cat_{category_name or 'all'}:{limit}:{skip}")

    # 2. 判断是否存在
    if shops:
        print('命中缓存')
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

    # 5. 写入redis缓存中, 300秒+随机时间, 防止缓存雪崩
    await r.setex(f"shop:list:cat_{category_name or 'all'}:{limit}:{skip}", 300 + randint(0, 120), shops_json)

    # 6. 返回商铺信息
    return shops


# 商铺详情
# 分布式锁(逻辑过期+setnx/非阻塞)
@router.get('/logic_expired/{id}', response_model=schemas.ShopDetailOut)
async def get_shop(id:int, db: Annotated[AsyncSession, '数据库会话', Depends(get_db)], 
                   r: Annotated[redis.Redis, 'redis客户端', Depends(get_redis)],
                   current_user: Annotated[dict, '当前用户', Depends(auth.check_login)]):
    cache_key = f"shop:detail:{id}"     # 缓存key
    lock_key = f"lock:shop:detail:{id}"  # 重建锁key(逻辑过期, 非阻塞)
    mutex_key = f"mutex:shop:detail:{id}"   # 冷启动阻塞锁(官方锁)

    # 1. 从redis中查询商铺缓存
    shop = await r.get(cache_key)
    # 2. 判断缓存是否存在, 不存在, 冷启动(降级获取官方锁)
    if not shop or shop == 'null':
        print('未命中缓存, 冷启动(降级获取官方锁)')
        try: 
            # 4. 不存在缓存, 开始加锁 (官方锁), 异步上下文管理器, 自动释放锁
            # timeout=5: 锁的自动过期时间（防止死锁）
            # blocking_timeout=2: 最多等待 2 秒，超时抛出 LockError
            async with r.lock(mutex_key, timeout=5, blocking_timeout=2):
                # 4.3 Double Check, 双重检查, 防止缓存击穿
                shop = await r.get(cache_key)
                if shop:
                    print('命中缓存')
                    if shop == 'null':
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商铺不存在")
                    shop = json.loads(shop)   # 反序列化, 将json字符串, 转为py对象
                    return shop['data']

                # 4.4 查询数据库（只有真正抢到锁的线程执行）
                stmt = select(models.Shop).where(models.Shop.id == id)
                result = await db.execute(stmt)
                shop = result.scalar_one_or_none()

                # 5. 查询数据库后, 如果不存在id, 将null写入缓存, 防止缓存穿透, 并且返回错误404
                if shop is None:
                    await r.setex(f"shop:detail:{id}", 60, 'null')
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商铺不存在")

                shop = jsonable_encoder(shop)   # 将orm对象, 转为py对象
                # 缓存值, 包含数据和过期时间
                cache_value = {
                    'data': shop, 
                    'expire_time': int(time.time() * 1000) + 300 * 1000
                    }  
                # 6. 存在id, 写入redis缓存中, 1小时+随机时间, 防止缓存雪崩, json.dumps序列化: 将py对象转为json对象
                await r.setex(cache_key, 3600 + randint(0, 300), json.dumps(cache_value, ensure_ascii=False))

                # 7. 返回商铺信息
                return shop

        # 处理锁超时：2 秒内没抢到锁，说明系统繁忙
        except LockError:
            raise HTTPException(status_code=503, detail="系统繁忙，请稍后再试")
        
        # 如果是 404 业务异常，直接原样抛出
        except HTTPException as e:
            raise e

        # 兜底捕获其他异常（DB 超时等）    
        except Exception as e:
            print(f"系统异常: {e}")
            raise HTTPException(status_code=500, detail="服务器错误")

    else:
        print('命中缓存， 检查逻辑过期')
        cache_data = json.loads(shop)    # 反序列化, 将json字符串, 转为py对象
        shop_data = cache_data['data']   # 获取缓存数据
        expire_at = cache_data['expire_time']   # 获取过期时间
        
        # 3. 检查逻辑过期时间
        if expire_at > int(time.time() * 1000):
            print('未过期')
            # 4. 未过期, 直接返回
            return shop_data
        print('过期')
        # 5. 过期, 重建缓存, 2秒后自动删除, 防止死锁
        lock = await r.set(lock_key, '1', nx=True, ex=2)

        # 如果抢到了锁
        if lock:
            # 开启异步任务, 刷新缓存
            asyncio.create_task(refresh_cache(id, r))

        # 否则返回旧数据
        return shop_data
        
        
# 异步任务, 刷新缓存
async def refresh_cache(id: int, r: redis.Redis):

    cache_key = f"shop:detail:{id}"     # 缓存key

    # 异步会话工厂
    async with async_session_maker() as db:
        try:
            # 再次双重检查(Double Check), 防止重复查DB
            shop = await r.get(cache_key)
            if shop:
                cache_data = json.loads(shop)  # 反序列化, 将json字符串, 转为py对象
                # 如果距离上一次重建不到 1 秒，说明别的线程刚刷新过，跳过
                if cache_data['expire_time'] > int(time.time() * 1000):
                    return
            
            # 查询数据库
            stmt = select(models.Shop).where(models.Shop.id == id)
            result = await db.execute(stmt)
            shop = result.scalar_one_or_none()  

            # 如果数据存在
            if shop:
                shop_dict = jsonable_encoder(shop)   # 将orm对象, 转为py对象
                # 重建缓存值, 包含数据和过期时间
                cache_value = {
                    'data': shop_dict, 
                    'expire_time': int(time.time() * 1000) + 300 * 1000
                    }  
                # 写入redis缓存中, 1小时+随机时间, 防止缓存雪崩, json.dumps序列化: 将py对象转为json对象
                await r.setex(cache_key, 3600 + randint(0, 300), json.dumps(cache_value, ensure_ascii=False))

            else:
                # 数据不存在，设置空缓存，防止缓存击穿
                await r.setex(cache_key, 60, 'null')
        except Exception as e:
            print(f"异步缓存刷新失败: {e}")


# 商铺详情
# 分布式锁(官方互斥锁/阻塞)
@router.get('/mutex/{id}', response_model=schemas.ShopDetailOut)
async def get_shop(id:int, db: Annotated[AsyncSession, '数据库会话', Depends(get_db)], 
                   r: Annotated[redis.Redis, 'redis客户端', Depends(get_redis)],
                   current_user: Annotated[dict, '当前用户', Depends(auth.check_login)]):
    cache_key = f"shop:detail:{id}"     # 缓存key
    lock_key = f"lock:shop:detail:{id}"  # 互斥锁key

    # 1. 从redis中查询商铺缓存
    shop = await r.get(cache_key)
    # 2. 判断缓存是否存在
    if shop:
        print('命中缓存')
        if shop == 'null':
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商铺不存在")
        # 3. 存在缓存, 直接返回商铺信息
        shop = json.loads(shop)   # 反序列化, 将json字符串, 转为py对象
        return shop
    
    try: 
        # 4. 不存在缓存, 开始加锁 (官方锁), 异步上下文管理器, 自动释放锁
        # timeout=5: 锁的自动过期时间（防止死锁）
        # blocking_timeout=2: 最多等待 2 秒，超时抛出 LockError
        async with r.lock(lock_key, timeout=5, blocking_timeout=2):
            # 4.3 Double Check, 双重检查, 防止缓存击穿
            shop = await r.get(cache_key)
            if shop:
                print('命中缓存')
                if shop == 'null':
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商铺不存在")
                shop = json.loads(shop)   # 反序列化, 将json字符串, 转为py对象
                return shop

            # 4.4 查询数据库（只有真正抢到锁的线程执行）
            stmt = select(models.Shop).where(models.Shop.id == id)
            result = await db.execute(stmt)
            shop = result.scalar_one_or_none()

            # 5. 查询数据库后, 如果不存在id, 将null写入缓存, 防止缓存穿透, 并且返回错误404
            if shop is None:
                await r.setex(f"shop:detail:{id}", 60, 'null')
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商铺不存在")

            shop = jsonable_encoder(shop)   # 将orm对象, 转为py对象
            shop_json = json.dumps(shop, ensure_ascii=False)   # 序列化, 将py对象, 转为json字符串

            # 6. 存在id, 写入redis缓存中, 300秒+随机时间, 防止缓存雪崩
            await r.setex(cache_key, 300 + randint(0, 120), shop_json)

            # 7. 返回商铺信息
            return shop

    # 处理锁超时：2 秒内没抢到锁，说明系统繁忙
    except LockError:
        raise HTTPException(status_code=503, detail="系统繁忙，请稍后再试")
    
    # 如果是 404 业务异常，直接原样抛出
    except HTTPException as e:
        raise e

    # 兜底捕获其他异常（DB 超时等）    
    except Exception as e:
        print(f"系统异常: {e}")
        raise HTTPException(status_code=500, detail="服务器错误")
        

# 商铺更新
@router.patch('/{id}')
async def update_shop(id:int, shop_data: schemas.ShopUpdate,
                      db: Annotated[AsyncSession, '数据库会话', Depends(get_db)],
                      r: Annotated[redis.Redis, 'redis客户端', Depends(get_redis)],
                      current_user: Annotated[dict, '当前用户', Depends(auth.check_login)],):
    # 1. 查询店铺id是否存在, 
    stmt = select(models.Shop).where(models.Shop.id==id)
    result = await db.execute(stmt)
    shop = result.scalar_one_or_none()
    # 不存在报错404
    if shop == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商铺不存在")
    
    # 2.存在, 更新数据库
    for key, value in shop_data.model_dump().items():
        if value is not None:
            setattr(shop, key, value)
    await db.commit()   # 提交
    await db.refresh(shop)  # 刷新shop对象

    # 3.删除缓存
    await r.delete(f"shop:detail:{id}")
    
    # 4. 删除所有列表缓存（模糊匹配 shop:list:cat_*）
    pattern = "shop:list:cat_*"
    cursor = 0  # 初始有标配
    keys_to_delete = []  # 放缓存key的列表
    while True:
        cursor, batch = await r.scan(cursor, match=pattern, count=100)  # 扫描redis, 获取匹配的key
        keys_to_delete.extend(batch)    # 将扫描出来的key, 放入列表
        if cursor == 0: 
            break
    if keys_to_delete:
        await r.delete(*keys_to_delete)

    # 返回
    return shop