"""
邮件服务模块 (Email Service)

提供邮件发送的抽象层和两种实现:
  - ConsoleEmailService: 开发环境使用，打印邮件链接到控制台
  - SmtpEmailService: 生产环境使用，通过 SMTP 发送真实邮件

设计模式: 策略模式 (Strategy Pattern) + 简单工厂 (Simple Factory)

邮件类型:
  1. 验证邮件 (verification email): 用户注册后发送，包含验证链接
  2. 密码重置邮件 (reset email): 忘记密码时发送，包含重置链接

配置说明:
  开发环境且 SMTP_PASSWORD 为空时，自动使用 ConsoleEmailService，
  这样无需配置真实 SMTP 即可完成注册→验证→登录的完整流程测试。

扩展指南:
  - 如需添加新邮件类型（如欢迎邮件、通知邮件），在 EmailService 基类
    新增抽象方法，在两个子类中分别实现
  - 如需对接第三方邮件服务（SendGrid/Mailgun），新建子类并实现接口即可
"""

import logging
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService(ABC):
    """
    邮件服务抽象基类

    定义了所有邮件服务必须实现的接口。
    新增邮件类型时，先在此添加抽象方法。
    """

    @abstractmethod
    async def send_verification_email(self, email: str, token: str) -> None:
        """发送邮箱验证链接"""
        ...

    @abstractmethod
    async def send_reset_email(self, email: str, token: str) -> None:
        """发送密码重置链接"""
        ...


class ConsoleEmailService(EmailService):
    """
    控制台邮件服务 — 开发环境专用

    不发送真实邮件，而是将验证/重置链接打印到控制台日志。
    开发者或测试人员复制链接即可模拟完成验证流程。

    使用条件: ENVIRONMENT=development 且 SMTP_PASSWORD 为空
    """

    async def send_verification_email(self, email: str, token: str) -> None:
        """打印邮箱验证链接到控制台"""
        verify_url = f"{settings.APP_URL}/verify-email?token={token}"
        logger.info("Verification email: %s → %s", email, verify_url)

    async def send_reset_email(self, email: str, token: str) -> None:
        """打印密码重置链接到控制台"""
        reset_url = f"{settings.APP_URL}/reset-password?token={token}"
        logger.info("Password reset email: %s → %s", email, reset_url)


class SmtpEmailService(EmailService):
    """
    SMTP 邮件服务 — 生产环境使用

    通过 SMTP 协议发送真实邮件，支持 TLS 加密。
    SMTP 配置在 .env 中设置（SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD 等）。

    HTML 邮件体包含点击链接和友好提示，兼容主流邮件客户端。
    """

    async def _send(self, to_email: str, subject: str, body: str) -> None:
        """
        发送邮件的内部方法

        使用 aiosmtplib 异步发送，不阻塞事件循环。
        邮件格式: 多部分 MIME，HTML 正文，UTF-8 编码。
        """
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS,
        )

    async def send_verification_email(self, email: str, token: str) -> None:
        """发送包含验证链接的 HTML 邮件"""
        verify_url = f"{settings.APP_URL}/verify-email?token={token}"
        subject = f"[{settings.APP_NAME}] Verify your email"
        body = f"""
        <h2>Welcome to {settings.APP_NAME}!</h2>
        <p>Please click the link below to verify your email:</p>
        <p><a href="{verify_url}">{verify_url}</a></p>
        <p>This link will expire in 24 hours.</p>
        """
        await self._send(email, subject, body)

    async def send_reset_email(self, email: str, token: str) -> None:
        """发送包含密码重置链接的 HTML 邮件"""
        reset_url = f"{settings.APP_URL}/reset-password?token={token}"
        subject = f"[{settings.APP_NAME}] Reset your password"
        body = f"""
        <h2>Password Reset</h2>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you did not request this, please ignore this email.</p>
        """
        await self._send(email, subject, body)


def get_email_service() -> EmailService:
    """
    邮件服务工厂函数

    根据配置自动选择邮件服务实现:
      - 开发环境 + 无 SMTP 密码 → ConsoleEmailService（控制台打印）
      - 其他情况 → SmtpEmailService（真实发送）

    调用方无需关心具体实现，始终通过 EmailService 接口操作。
    """
    if settings.ENVIRONMENT == "development" and not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured — using console email service")
        return ConsoleEmailService()
    return SmtpEmailService()
