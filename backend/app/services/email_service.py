"""Email service abstraction and implementations."""

import logging
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService(ABC):
    """Abstract email service interface."""

    @abstractmethod
    async def send_verification_email(self, email: str, token: str) -> None:
        """Send email verification link."""
        ...

    @abstractmethod
    async def send_reset_email(self, email: str, token: str) -> None:
        """Send password reset link."""
        ...


class ConsoleEmailService(EmailService):
    """Logs emails to console — for development use."""

    async def send_verification_email(self, email: str, token: str) -> None:
        verify_url = f"{settings.APP_URL}/verify-email?token={token}"
        logger.info("=" * 60)
        logger.info(f"VERIFICATION EMAIL to: {email}")
        logger.info(f"Verification link: {verify_url}")
        logger.info("=" * 60)

    async def send_reset_email(self, email: str, token: str) -> None:
        reset_url = f"{settings.APP_URL}/reset-password?token={token}"
        logger.info("=" * 60)
        logger.info(f"PASSWORD RESET EMAIL to: {email}")
        logger.info(f"Reset link: {reset_url}")
        logger.info("=" * 60)


class SmtpEmailService(EmailService):
    """Sends real emails via SMTP."""

    async def _send(self, to_email: str, subject: str, body: str) -> None:
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
    """Factory: returns the appropriate email service based on config."""
    if settings.ENVIRONMENT == "development" and not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured — using console email service")
        return ConsoleEmailService()
    return SmtpEmailService()
