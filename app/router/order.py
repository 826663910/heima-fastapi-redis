from fastapi import APIRouter, Depends, HTTPException, status  # 路由和依赖
from fastapi.encoders import jsonable_encoder  # 序列化
from sqlalchemy import select, update, func   # 查询和更新和内置函数
from sqlalchemy.ext.asyncio import AsyncSession # 异步注解
from datetime import datetime, timezone 
from redis.asyncio import Redis # 异步redis
from typing import Annotated    # 注解
from ..database import get_redis, get_db    # 获取redis客户端
from .. import models, schemas, auth  # 导入模型和模式和验证
import time 

# 路由
router = APIRouter(
    prefix='/voucher-order',
    tags=['VOUCHER-ORDER']
)


# 全局唯一ID生成器
async def globally_unique_id(r: Redis, prefix: str='order') -> int:
    # 1. 生成时间戳
    current_time = int(time.time()) - 1640995200
    # 2. 生成序列号
    # 2.1 获取当天日期, 精确到天
    today = datetime.now(timezone.utc).strftime('%Y%m%d')
    # 2.2 自增长
    count = await r.incr(f"icr:{prefix}:{today}")
    # 3. 拼接字符串并返回, int类型
    uid = (current_time << 32) | count  # 左移32位, 右对齐
    return uid

# 下秒杀券订单
@router.post('/seckill/{voucher_id}')
async def seckill(voucher_id: int,  
                  db: Annotated[AsyncSession, '数据库会话', Depends(get_db)],
                  r: Annotated[Redis, 'redis客户端', Depends(get_redis)],
                  ):
    
    # 1. 查询优惠券
    stmt = (select(models.Voucher.id,               # 显式列出
                models.Voucher.shop_id,
                models.Voucher.title,
                models.Voucher.sub_title,
                models.Voucher.pay_value,
                models.Voucher.actual_value,
                models.Voucher.status, 
                models.VoucherSeckill.stock, 
                models.VoucherSeckill.start_time, 
                models.VoucherSeckill.end_time)
            .join(models.VoucherSeckill, models.Voucher.id == models.VoucherSeckill.voucher_id)
            .where(models.Voucher.type==1, models.Voucher.id == voucher_id))
    result = await db.execute(stmt)  # 执行sql
    seckill = result.mappings().first()   # RowMapping 对象
    await db.commit()

    # 如果不存在, 则抛出异常
    if not seckill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="优惠券不存在")

    # 获取utc时间, （Aware, 有时区）
    now = datetime.now(timezone.utc)
    # 2. 判断秒杀是否开始
    if seckill['start_time'].replace(tzinfo=timezone.utc) > now:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="秒杀尚未开始")

    # 3. 判断秒杀是否结束
    if seckill['end_time'].replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="秒杀已结束")

    # 4. 判断库存是否充足
    if seckill['stock'] <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="库存不足")

    """ 开启事务块, 退出时自动 commit, 异常时自动 rollback """
    async with db.begin():  

        # 4.1 根据优惠券id和用户id查询是否存在订单
        stmt = (select(func.count(models.VoucherOrder.id))      # 用内置函数计数订单数量
                .where(models.VoucherOrder.voucher_id == voucher_id, 
                       models.VoucherOrder.user_id == 2))
        is_order = await db.execute(stmt)
        count = is_order.scalar()   # 获取结果数量
        if count > 0:   # 如果数量大于0, 则说明存在订单
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="订单已存在")

        # 5. 扣减库存
        # 执行sql语句
        stock = await db.execute(update(models.VoucherSeckill)                          # 1. 更新语句
                                    .where(models.VoucherSeckill.voucher_id==voucher_id,   # 2. 条件, 秒杀券id=传入的id
                                            models.VoucherSeckill.stock > 0)                # 3. 乐观锁, 库存必须大于0 
                                    .values(stock=models.VoucherSeckill.stock - 1 ))       # 4. 更新字段

        # 如果影响行数为0, 则说明库存不足
        if stock.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="库存不足")

        # 6. 生成订单
        # 6.1. 订单id
        uid = await globally_unique_id(r, 'order')
        # 6.2. 用户id
        user_id = 2
        # 6.3. 代金券id
        v_id = voucher_id
        voucher_order = models.VoucherOrder(id=uid, user_id=user_id, voucher_id=v_id)
        db.add(voucher_order)   # 添加进数据库

    # 7. 返回订单id
    return {'order_id': uid, 'msg': '秒杀成功'}
