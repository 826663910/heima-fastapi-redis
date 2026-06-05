from sqlalchemy import Column, String, Integer, Boolean, ForeignKey,Text, func, DECIMAL
from sqlalchemy.sql.sqltypes import TIMESTAMP   # 导入数据库类型中的日期时间
from sqlalchemy.orm import relationship   # 导入关系映射
from .database import Base # 模型基类

# 用户表
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(11), unique=True, nullable=False)
    password = Column(String(128), default="")
    nick_name = Column(String(32), default="")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


# 分类表
class Category(Base):
    __tablename__= "category"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)

# 商铺表
class Shop(Base):
    __tablename__="shop"
    id = Column(Integer, primary_key=True, index=True)  # 主键
    typeId = Column(Integer, ForeignKey("category.id", ondelete="CASCADE")) # 外键
    name = Column(String(32), default="")      # 店铺名称
    address = Column(String(255), default="")   # 地址
    area = Column(String(32), default="")   # 区域
    avgPrice = Column(Integer, default=0)   # 人均消费
    comments = Column(Integer, default=0)   # 评论总数
    images = Column(String(255), default="")    # 图片
    openHours = Column(String(64), default="")   # 营业时间
    score = Column(Integer, default=0)  # 评分
    sold = Column(Integer, default=0)   # 销量
    x = Column(DECIMAL(10, 7))  # 经度
    y = Column(DECIMAL(10, 7))  # 纬度
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())    # 创建时间
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())   # 更新时间