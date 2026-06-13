"""
认证模块的请求/响应 Schema (Auth Schemas)

定义了认证相关接口的输入输出数据结构。
使用 Pydantic v2 进行自动校验，如密码长度、邮箱格式等。

扩展指南:
  如需新增用户字段（如昵称），在 RegisterRequest 和 UserResponse 中
  同时添加即可。Pydantic 的 from_attributes=True 会自动从 ORM 模型映射。
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """注册请求 — 前端提交的注册表单数据"""
    email: EmailStr                              # EmailStr 自动校验邮箱格式
    password: str = Field(min_length=6, max_length=128)  # 密码最少 6 位


class LoginRequest(BaseModel):
    """登录请求 — 前端提交的登录表单数据"""
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    """邮箱验证请求 — 携带注册时邮件中的验证令牌"""
    token: str


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求 — 发送密码重置邮件"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """密码重置请求 — 携带重置令牌和新密码"""
    token: str
    new_password: str = Field(min_length=6, max_length=128)


class UserResponse(BaseModel):
    """
    用户信息响应

    返回给前端的用户公开信息，不含密码哈希等敏感字段。
    from_attributes=True: 允许直接从 SQLAlchemy ORM 对象创建此 Schema，
    无需手动逐字段赋值。
    """
    id: int
    email: str
    is_verified: bool
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """
    登录成功响应 — 包含 JWT 令牌和用户信息

    token_type 固定为 "bearer"，前端应通过 Authorization: Bearer <access_token> 携带
    """
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
