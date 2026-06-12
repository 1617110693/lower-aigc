"""
认证路由 (Auth Router)

提供用户认证相关的 REST API 端点:
  POST /register         — 用户注册
  POST /verify-email     — 邮箱验证
  POST /login            — 登录获取 JWT
  GET  /me               — 获取当前用户信息
  POST /forgot-password  — 发送密码重置邮件
  POST /reset-password   — 重置密码

所有端点挂载在 /api/v1/auth 前缀下（在 main.py 中配置）。

扩展指南:
  - 如需添加 OAuth2 登录，新增 /oauth/callback 等端点
  - 如需刷新令牌，新增 POST /refresh 端点
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.services.email_service import get_email_service

router = APIRouter()


@router.post("/register")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册 — POST /api/v1/auth/register

    接收邮箱和密码，创建用户并发送验证邮件。
    密码最少 6 位，邮箱格式由 Pydantic EmailStr 自动校验。

    请求体:
        {"email": "user@example.com", "password": "your_password"}
    响应:
        {"message": "注册成功提示"}
    错误:
        409: 邮箱已被注册
    """
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.register(body.email, body.password)


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    邮箱验证 — POST /api/v1/auth/verify-email

    使用注册邮件中的令牌完成邮箱验证。
    验证成功后 is_verified 设为 True，令牌被清空（一次性使用）。

    请求体:
        {"token": "uuid-verification-token"}
    响应:
        {"message": "验证成功提示"}
    错误:
        404: 令牌无效或已被使用
    """
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.verify_email(body.token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录 — POST /api/v1/auth/login

    校验邮箱和密码，返回 JWT 令牌和用户信息。
    前端应将 access_token 存入 localStorage 并在后续请求中通过
    Authorization: Bearer <token> 请求头携带。

    请求体:
        {"email": "user@example.com", "password": "your_password"}
    响应:
        {"access_token": "jwt_string", "token_type": "bearer", "user": {...}}
    错误:
        403: 密码错误或邮箱未验证
    """
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.login(body.email, body.password)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户信息 — GET /api/v1/auth/me

    需要有效的 JWT Bearer token。
    可用作前端页面刷新时验证 token 是否有效。

    响应:
        {"id": 1, "email": "...", "is_verified": true, "created_at": "..."}
    错误:
        401: token 无效或已过期
    """
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.get_me(current_user)


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    忘记密码 — POST /api/v1/auth/forgot-password

    发送密码重置邮件到指定邮箱。
    安全: 无论邮箱是否存在，都返回相同的成功消息，
    防止攻击者枚举系统已注册邮箱。

    请求体:
        {"email": "user@example.com"}
    响应:
        {"message": "如果邮箱存在，重置链接已发送"}
    """
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.forgot_password(body.email)


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    密码重置 — POST /api/v1/auth/reset-password

    使用重置邮件中的令牌和新密码完成密码重置。
    令牌有效期 1 小时，一次性使用。

    请求体:
        {"token": "uuid-reset-token", "new_password": "new_password"}
    响应:
        {"message": "密码重置成功提示"}
    错误:
        404: 令牌无效或已过期
    """
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.reset_password(body.token, body.new_password)
