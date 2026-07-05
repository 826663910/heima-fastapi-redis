from sqlalchemy import Column, String, Integer, Boolean, ForeignKey,Text, func, DECIMAL, BigInteger
from sqlalchemy.dialects.mysql import BIGINT, TINYINT    # mysql的类型, 
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

# 优惠券订单
class VoucherOrder(Base):
    __tablename__ = "voucher_order"
    id = Column(BigInteger, primary_key=True, autoincrement=False, nullable=False)   # 订单id
    user_id = Column(BIGINT(unsigned=True), nullable=False)    # 下单的用户id, 无符号
    voucher_id = Column(BIGINT(unsigned=True), nullable=False)  # 下单的券id, 无符号
    pay_type = Column(TINYINT(unsigned=True), nullable=False, server_default='1')   # 支付方式, 1:余额支付, 2:支付宝支付, 3:微信支付
    status = Column(TINYINT(unsigned=True), nullable=False, server_default='1')   # 订单状态, 1:未支付, 2:已支付, 3:已核销, 4:已取消, 5:退款中, 6:已退款, 7:已过期
    created_time = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())    # 下单时间
    pay_time = Column(TIMESTAMP(timezone=True), nullable=True)   # 支付时间
    use_time = Column(TIMESTAMP(timezone=True), nullable=True)   # 核销时间
    refund_time = Column(TIMESTAMP(timezone=True), nullable=True)   # 退款时间
    updated_time = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())   # 更新时间


# 普通优惠券
class Voucher(Base):
    __tablename__ = "voucher"
    id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False)    # 主键
    shop_id = Column(BIGINT(unsigned=True), server_default=None)  # 商铺id, 无符号
    title = Column(String(255), nullable=False) # 代金券标题
    sub_title = Column(String(255), nullable=False) # 代金券副标题
    pay_value = Column(BIGINT(unsigned=True), nullable=False)  # 支付金额, 单位是分, 例如200代表2元
    actual_value = Column(BIGINT(unsigned=True), nullable=False)  # 抵扣金额, 单位是分, 例如200代表2元
    type = Column(TINYINT(unsigned=True), nullable=False, server_default='0')   # 券类型, 0:普通券, 1:秒杀券
    status = Column(TINYINT(unsigned=True), nullable=False, server_default='1')   # 券状态, 1:上架, 2:下架, 3:过期
    created_time = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())    # 创建时间
    updated_time = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())   # 更新时间


# 秒杀优惠券
class VoucherSeckill(Base):
    __tablename__ = "voucher_seckill"
    id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False)    # 主键
    voucher_id = Column(BIGINT(unsigned=True), nullable=False)  # 关联的优惠券id, 无符号
    stock = Column(BIGINT(unsigned=True), nullable=False)  # 秒杀库存
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)   # 秒杀开始时间
    end_time = Column(TIMESTAMP(timezone=True), nullable=False)   # 秒杀结束时间
    created_time = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())    # 创建时间
    updated_time = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())   # 更新时间
    
