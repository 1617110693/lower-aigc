"""
认证服务模块 (Authentication Service)

实现用户认证的全部业务逻辑:
  - 注册 (register): 创建用户 + 发送验证邮件
  - 邮箱验证 (verify_email): 核对令牌，激活账号
  - 登录 (login): 校验密码 + 返回 JWT
  - 忘记密码 (forgot_password): 生成重置令牌 + 发送邮件
  - 密码重置 (reset_password): 校验令牌 + 更新密码
  - 用户信息 (get_me): 返回当前登录用户信息

安全措施:
  - 密码使用 bcrypt 哈希存储
  - 忘记密码接口不区分"用户存在"和"不存在"，防止邮箱枚举攻击
  - 重置令牌有 1 小时有效期
  - 验证令牌为随机 UUID，不可猜测

扩展指南:
  - 如需添加登录失败次数限制，可在 User 模型新增 failed_attempts 字段
  - 如需支持 OAuth2 第三方登录，新增 OAuthService 并在路由层添加回调端点
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import TokenResponse, UserResponse
from app.services.email_service import EmailService


class AuthService:
    """
    认证服务核心类

    每个 HTTP 请求创建独立的 AuthService 实例，
    需要注入数据库会话和邮件服务。

    用法:
        service = AuthService(db, email_service)
        result = await service.login(email, password)
    """

    def __init__(self, db: AsyncSession, email_service: EmailService):
        self.db = db
        self.email_service = email_service

    async def register(self, email: str, password: str) -> dict:
        """
        用户注册

        流程:
          1. 检查邮箱是否已注册（唯一性校验）
          2. 生成随机验证令牌 (UUID4)
          3. 创建 User 记录（密码 bcrypt 哈希）
          4. 发送验证邮件（开发环境打印到控制台）

        参数:
            email: 用户邮箱
            password: 明文密码（最少 6 位）
        返回:
            {"message": "注册成功提示"}
        异常:
            ConflictError: 邮箱已被注册
        """
        # 检查邮箱唯一性
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ConflictError("Email already registered")

        # 生成验证令牌并创建用户
        verification_token = str(uuid.uuid4())
        user = User(
            email=email,
            password_hash=hash_password(password),
            verification_token=verification_token,
        )
        self.db.add(user)
        await self.db.flush()

        # 发送验证邮件
        await self.email_service.send_verification_email(email, verification_token)
        return {
            "message": "Registration successful. Please check your email to verify your account."
        }

    async def verify_email(self, token: str) -> dict:
        """
        邮箱验证

        流程:
          1. 根据 token 查找用户
          2. 设置 is_verified=True
          3. 清空 verification_token（令牌一次性使用）

        参数:
            token: 注册邮件中的验证令牌
        返回:
            {"message": "验证成功提示"}
        异常:
            NotFoundError: 令牌无效或已被使用
        """
        result = await self.db.execute(
            select(User).where(User.verification_token == token)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("Invalid or expired verification token")

        user.is_verified = True
        user.verification_token = None  # 清空令牌，防止重复使用
        await self.db.flush()
        return {"message": "Email verified successfully. You can now log in."}

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        用户登录

        流程:
          1. 根据邮箱查找用户
          2. 校验密码（bcrypt verify）
          3. 检查邮箱是否已验证（生产环境）
          4. 创建 JWT 令牌并返回

        参数:
            email: 用户邮箱
            password: 明文密码
        返回:
            TokenResponse: 包含 JWT token 和用户信息
        异常:
            ForbiddenError: 密码错误或邮箱未验证
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # 注意: 用统一的错误消息防止用户名枚举
        if not user or not verify_password(password, user.password_hash):
            raise ForbiddenError("Invalid email or password")

        # 检查邮箱验证状态（生产环境强制要求，开发环境可通过 .env 关闭）
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            raise ForbiddenError("Please verify your email before logging in")

        access_token = create_access_token(user.id)
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )

    async def get_me(self, user: User) -> UserResponse:
        """获取当前登录用户信息"""
        return UserResponse.model_validate(user)

    async def forgot_password(self, email: str) -> dict:
        """
        忘记密码 — 发送重置邮件

        安全考量: 无论邮箱是否存在，都返回相同的成功消息，
        防止攻击者通过接口枚举系统已注册的邮箱地址。

        流程:
          1. 查找用户（找不到也返回成功）
          2. 生成 UUID 重置令牌，有效期 1 小时
          3. 发送重置邮件
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            # 不暴露用户是否存在的提示，防止邮箱枚举攻击
            return {
                "message": "If the email exists, a password reset link has been sent."
            }

        # 生成重置令牌，1 小时有效
        reset_token = str(uuid.uuid4())
        user.reset_token = reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await self.db.flush()

        await self.email_service.send_reset_email(email, reset_token)
        return {
            "message": "If the email exists, a password reset link has been sent."
        }

    async def reset_password(self, token: str, new_password: str) -> dict:
        """
        密码重置

        流程:
          1. 根据 token 查找用户，同时检查令牌是否过期
          2. 更新密码（bcrypt 哈希）
          3. 清空重置令牌

        参数:
            token: 重置邮件中的令牌
            new_password: 新密码（最少 6 位）
        异常:
            NotFoundError: 令牌无效或已过期（超过 1 小时）
        """
        result = await self.db.execute(
            select(User).where(
                User.reset_token == token,
                # 同时检查过期时间，一行查询完成
                User.reset_token_expires > datetime.now(timezone.utc),
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("Invalid or expired reset token")

        user.password_hash = hash_password(new_password)
        user.reset_token = None        # 清空令牌
        user.reset_token_expires = None
        await self.db.flush()
        return {"message": "Password reset successfully. You can now log in."}
