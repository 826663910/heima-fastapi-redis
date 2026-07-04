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

class VoucherListOut(BaseModel):
    id: int
    title: str
    sub_title: str
    pay_value: int
    actual_value: int
    status: int

class VoucherSeckillListOut(VoucherListOut):
    stock: int
    start_time: datetime
    end_time: datetime
    