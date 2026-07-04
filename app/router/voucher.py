from fastapi import APIRouter, Depends
from typing import Annotated, List    # 注解
from sqlalchemy.ext.asyncio import AsyncSession # 异步注解
from sqlalchemy import select   # SQL查询构造器
from ..database import get_db, get_redis    # 获取异步数据库会话和redis客户端
from .. import models, schemas  # 导入模型和模式

router = APIRouter(
    prefix="/voucher",
    tags=["VOUCHER"]
)

@router.get('/', response_model=List[schemas.VoucherListOut])
async def get_voucher(db: Annotated[AsyncSession, '数据库会话', Depends(get_db)]):
    # 查询平价券
    stmt = select(models.Voucher).where(models.Voucher.type==0).order_by(models.Voucher.id)
    result = await db.execute(stmt) # 执行sql
    vouchers = result.scalars().all()   # 返回所有
    return vouchers # 返回平价券列表

@router.get('/seckill', response_model=List[schemas.VoucherSeckillListOut])
async def get_seckill(db: Annotated[AsyncSession, '数据库会话', Depends(get_db)]):
    # 查询秒杀券
    stmt = (select(models.Voucher, models.VoucherSeckill.stock, models.VoucherSeckill.start_time, models.VoucherSeckill.end_time)
            .join(models.VoucherSeckill, models.Voucher.id==models.VoucherSeckill.voucher_id)
            .where(models.Voucher.type==1)
            .order_by(models.Voucher.id))
    result = await db.execute(stmt) # 执行sql
    vouchers = result.mappings().all()   # 返回所有
    return vouchers # 返回秒杀券列表




