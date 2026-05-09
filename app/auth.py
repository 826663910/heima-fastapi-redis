from fastapi import Request, HTTPException, status

# 登录校验的依赖, 会在session中间件后和接口前运行
async def check_login(request: Request) -> dict:
    """登录校验依赖项"""
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='未登录')
    return user