"""Authentication service layer."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import TokenResponse, UserResponse
from app.services.email_service import EmailService


class AuthService:
    """Handles registration, login, verification, and password reset."""

    def __init__(self, db: AsyncSession, email_service: EmailService):
        self.db = db
        self.email_service = email_service

    async def register(self, email: str, password: str) -> dict:
        """Register a new user and send verification email."""
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ConflictError("Email already registered")

        verification_token = str(uuid.uuid4())
        user = User(
            email=email,
            password_hash=hash_password(password),
            verification_token=verification_token,
        )
        self.db.add(user)
        await self.db.flush()

        await self.email_service.send_verification_email(email, verification_token)
        return {"message": "Registration successful. Please check your email to verify your account."}

    async def verify_email(self, token: str) -> dict:
        """Verify a user's email with the token."""
        result = await self.db.execute(
            select(User).where(User.verification_token == token)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("Invalid or expired verification token")

        user.is_verified = True
        user.verification_token = None
        await self.db.flush()
        return {"message": "Email verified successfully. You can now log in."}

    async def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate a user and return a JWT token."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise ForbiddenError("Invalid email or password")

        if not user.is_verified:
            raise ForbiddenError("Please verify your email before logging in")

        access_token = create_access_token(user.id)
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )

    async def get_me(self, user: User) -> UserResponse:
        """Return the current user's profile."""
        return UserResponse.model_validate(user)

    async def forgot_password(self, email: str) -> dict:
        """Generate a reset token and send password reset email."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            # Return success even if user not found to prevent email enumeration
            return {"message": "If the email exists, a password reset link has been sent."}

        reset_token = str(uuid.uuid4())
        user.reset_token = reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await self.db.flush()

        await self.email_service.send_reset_email(email, reset_token)
        return {"message": "If the email exists, a password reset link has been sent."}

    async def reset_password(self, token: str, new_password: str) -> dict:
        """Reset a user's password using the reset token."""
        result = await self.db.execute(
            select(User).where(
                User.reset_token == token,
                User.reset_token_expires > datetime.now(timezone.utc),
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("Invalid or expired reset token")

        user.password_hash = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        await self.db.flush()
        return {"message": "Password reset successfully. You can now log in."}
