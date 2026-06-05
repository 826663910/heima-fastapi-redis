from pydantic import BaseModel

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
    comment: int

class ShopDetailOut(ShopListOut):
    area: str
    address: str
    openHours: str
    images: str
    x: float
    y: float
