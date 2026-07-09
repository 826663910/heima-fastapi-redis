from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 验证用户信息
class UserInfo(BaseModel):
    id: int
    phone: str
    nick_name: str

    # 配置从属性中读取数据
    class Config:
        from_attributes=True


# 响应
class UserOut(BaseModel):
    id: int
    nick_name: str


# 商铺
class ShopListOut(BaseModel):
    id: int
    name: str
    typeId: int
    avgPrice: int
    score: int
    comments: int

class ShopDetailOut(ShopListOut):
    area: str
    address: str
    openHours: Optional[str] = None
    images: Optional[str] = None
    x: float
    y: float

class ShopUpdate(BaseModel):
    name: Optional[str] = None
    typeId: Optional[int] = None
    avgPrice: Optional[int] = None
    score: Optional[int] = None
    comments: Optional[int] = None
    area: Optional[str] = None
    address: Optional[str] = None
    openHours: Optional[str] = None
    images: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None


# 优惠券列表
class VoucherListOut(BaseModel):
    id: int
    shop_id: Optional[int] = None
    title: str
    sub_title: str
    pay_value: int
    actual_value: int
    status: int

class VoucherSeckillListOut(VoucherListOut):
    stock: int
    start_time: datetime
    end_time: datetime


# 创建优惠券
class VoucherPost(BaseModel):
    shop_id : Optional[int] = None
    title: str
    sub_title: str
    pay_value: int
    actual_value: int
    type: int
    status: int


class VoucherSeckillPost(VoucherPost):
    stock: int
    start_time: datetime
    end_time: datetime

class VoucherPatch(BaseModel):
    title: Optional[str] = None
    sub_title: Optional[str] = None
    status: Optional[int] = None

class VoucherOut(BaseModel):
    title: str
    sub_title: str
    status: int