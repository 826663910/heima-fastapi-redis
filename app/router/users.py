# 路由器, 依赖注入, http异常信息, 状态码, 请求, 表单
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession  # 导入异步会话类注解
from sqlalchemy import select  # 导入select函数
from typing import Optional, Annotated # 导入可选类型注解
import redis.asyncio as redis
import phonenumbers  # 导入手机号码库
from phonenumbers import is_valid_number    # 验证手机号码是否有效
from ..database import get_db, get_redis   # 导入获取异步数据库会话的函数和获取异步redis的函数
from .. import models, schemas, auth  # 导入模型和模式
import random  # 用于生成随机验证码
import string  # 用于生成随机字符串
# 安装依赖 pip install httpx 
import httpx

# 路由前缀, 标签
router = APIRouter(
    prefix="/user",
    tags=["user"]
)

"""发送验证码的请求函数"""
async def request_code(code: str, phone: str):
    body = {'name': '推送助手', 'code': code, 'to': phone} 
    async with httpx.AsyncClient(timeout=10.0) as client:   # 异步的上下文管理器
        res = await client.post('https://push.spug.cc/sms/4_YCGgRIS7C3ABq6ufhycg', json=body)
        print(res.text)
        return res


"""点击发送验证码的接口"""
@router.post("/code")
async def register(r: Annotated[redis.Redis, 'redis客户端', Depends(get_redis)], 
                   phone: str):
    
    # 1. 检验手机号
    validated_phone = phonenumbers.parse(phone, "CN")
    # 如果手机号不合法, 抛出422异常
    if not is_valid_number(validated_phone):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="手机号有误")
    
    # 2. 生成验证码
    code = str(random.randint(100000, 999999))
    # 3. 保存验证码到redis
    await r.setex(f"phone_code:{phone}", 60, code)  # 60秒后过期
    # 4. 发送验证码
    print(f'发送验证码: {code} 到手机号: {phone}')
    # res = await request_code(code, phone)
    # if res.status_code != 200: 
    #     raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='短信发送失败')
    # 5. 返回响应
    return {"msg": "ok"}


"""随机字符串函数"""
def random_string(length: int = 8) -> str:
    """生成包含字母和数字的随机字符串"""
    chars = string.ascii_letters + string.digits  # 大小写字母+数字
    return ''.join(random.choice(chars) for _ in range(length))


"""创建用户的函数"""
async def create_user(phone: str, db: AsyncSession):
    # 创建用户对象
    user = models.User(phone=phone, nick_name='user_' + random_string(5))
    # 添加到数据库
    db.add(user)
    await db.commit() # 提交事务
    await db.refresh(user)  # 刷新用户对象
    return schemas.UserInfo.model_validate(user).model_dump()  # 返回用户id


"""登录和注册接口"""
@router.post("/login")
async def login(request: Request, 
                r: Annotated[redis.Redis, 'redis客户端', Depends(get_redis)],
                db: Annotated[AsyncSession, '数据库会话', Depends(get_db)],   
                phone: str = Form(...), code: str = Form(...),     # 表单提交, ...表示必填
                password: Optional[str] = Form(None)):  # 可选密码字段
    
    # 1. 校验手机号
    validated_phone = phonenumbers.parse(phone, "CN")
    # 如果手机号不合法, 抛出422异常
    if not is_valid_number(validated_phone):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="手机号有误")

    # 2.校验验证码, 从redis中获取验证码
    redis_code = await r.get(f"phone_code:{phone}")
    print(redis_code)
    if redis_code != code:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="验证码有误")

    # 3. 一致, 根据手机号查询用户
    stmt = select(models.User).where(models.User.phone == phone)
    result = await db.execute(stmt)  # 执行查询
    user = result.scalar_one_or_none()   # 获取查询结果, 如果没有结果, 返回None

    # 4. 判断用户是否存在
    if user is None:
        # 5. 不存在创建新用户并保存
        user = await create_user(phone, db)
    else:
        # 用户已存在，使用现有用户id
        user = schemas.UserInfo.model_validate(user).model_dump()
    
    # 6. 保存用户到session, 这个会自动保存到cookie中
    request.session['user'] = user

    return {"msg": "登录成功"}


"""获取当前用户信息"""
@router.get('/user/me', response_model=schemas.UserOut)
async def userinfo(request: Request, 
                   db: Annotated[AsyncSession, '数据库会话', Depends(get_db)],
                   current_user: Annotated[dict, '当前用户', Depends(auth.check_login)]
                   ):
    
    # 查询当前用户
    stmt = select(models.User).where(models.User.id == current_user['id'])
    # 执行sql
    result = await db.execute(stmt)
    # 返回数据或者None
    user = result.scalar_one_or_none()
    if user == None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户不存在")
    return user
