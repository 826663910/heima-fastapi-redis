from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List    # 注解
from sqlalchemy.ext.asyncio import AsyncSession # 异步注解
from sqlalchemy import select   # SQL查询构造器
from sqlalchemy import or_  # 或
from ..database import get_db, get_redis    # 获取异步数据库会话和redis客户端
from .. import models, schemas  # 导入模型和模式

router = APIRouter(
    prefix="/voucher",
    tags=["VOUCHER"]
)

@router.get('/', response_model=List[schemas.VoucherListOut])
async def get_voucher(db: Annotated[AsyncSession, '数据库会话', Depends(get_db)]):
    # 查询平价券
    stmt = (select(models.Voucher)
            .where(models.Voucher.type==0)
            .where(models.Voucher.shop_id)
            .order_by(models.Voucher.id))
    result = await db.execute(stmt) # 执行sql
    vouchers = result.scalars().all()   # 返回所有
    return vouchers # 返回平价券列表

@router.get('/shop/{shop_id}/seckill', response_model=List[schemas.VoucherSeckillListOut])
async def get_seckill(shop_id: int, db: Annotated[AsyncSession, '数据库会话', Depends(get_db)]):
    # 查询秒杀券
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
            .join(models.VoucherSeckill, models.Voucher.id==models.VoucherSeckill.voucher_id)
            .where(models.Voucher.type==1)
            .where(models.Voucher.shop_id==shop_id)
            .order_by(models.Voucher.id))
    result = await db.execute(stmt) # 执行sql
    vouchers = result.mappings().all()   # 返回所有
    return vouchers # 返回秒杀券列表

@router.post('/')
async def create_seckill(post: schemas.VoucherSeckillPost, 
                           db: Annotated[AsyncSession, '数据库会话', Depends(get_db)]):
    
    # 剔除秒杀券的字段
    base_post = post.model_dump(exclude={'stock', 'start_time', 'end_time'})
    voucher = models.Voucher(**base_post)   # 将post转为orm对象
    db.add(voucher)  # 添加到数据库

    # 如果为1, 则添加秒杀券数据
    if post.type ==1:
        await db.flush()    # 刷新数据库(提交前, 获取voucher_id)
        # 构造秒杀券数据
        seckill_data = {
            'voucher_id': voucher.id,
            'stock': post.stock,
            'start_time': post.start_time,
            'end_time': post.end_time
        }
        # 添加秒杀券数据
        seckill = models.VoucherSeckill(**seckill_data)
        db.add(seckill)
    
    # 否则, 为普通券
    await db.commit()       # 提交事务
    await db.refresh(voucher)   # 刷新orm对象
    return voucher  # 返回优惠卷



