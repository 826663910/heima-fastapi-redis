from pydantic import BaseModel

# 验证用户信息
class UserInfo(BaseModel):
    id: int
    phone: str
    nick_name: str

    # 配置从属性中读取数据
    class Config:
        from_attributes=True


class UserOut(BaseModel):
    id: int
    nick_name: str
    