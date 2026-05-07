from sqlalchemy import Column, String, Integer, Boolean, ForeignKey,Text, func
from sqlalchemy.sql.sqltypes import TIMESTAMP   # 导入数据库类型中的日期时间
from sqlalchemy.orm import relationship   # 导入关系映射
from .database import Base # 模型基类

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(11), unique=True, nullable=False)
    password = Column(String(128), default="")
    nick_name = Column(String(32), default="")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())