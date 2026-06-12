"""
依赖注入模块 (FastAPI Dependencies)

提供可在路由端点中复用的依赖项，通过 Depends() 注入。

核心依赖:
  - get_current_user: 从请求头 Bearer token 中提取 JWT，
    解码获取用户 ID，从数据库加载用户对象并返回。
    如果 token 无效或无对应用户，自动返回 401 错误。

用法:
    @router.get("/profile")
    async def profile(current_user: User = Depends(get_current_user)):
        return {"email": current_user.email}

扩展指南:
  - 如需添加角色控制（如管理员权限），可在 get_current_user 基础上
    创建新的依赖项，检查 user.role 后决定是否放行。
  - 如需支持 API Key 认证，可新增 get_current_api_key 依赖。
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User

# HTTP Bearer Token 安全方案 — 从 Authorization: Bearer <token> 头中提取令牌
security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    从请求中提取并验证当前登录用户

    认证流程:
      1. 从 Authorization 头中提取 Bearer token
      2. 使用 JWT 解码 token，获取其中的 user_id (sub 字段)
      3. 用 user_id 查询数据库，加载 User 对象
      4. 返回已认证的 User 对象，供后续业务逻辑使用

    参数:
        credentials: FastAPI 自动从请求头解析的 Bearer token
        db: 数据库会话（由 get_db 依赖注入）
    返回:
        已认证的 User ORM 对象
    异常:
        HTTPException(401): token 无效、过期或用户不存在
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # 从数据库加载用户对象，确认用户未被删除
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
