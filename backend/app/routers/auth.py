"""Authentication router."""

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
    """Register a new user account."""
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.register(body.email, body.password)


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify email address with token."""
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.verify_email(body.token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login and receive an access token."""
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.login(body.email, body.password)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user."""
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.get_me(current_user)


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset email."""
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.forgot_password(body.email)


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password with token."""
    email_service = get_email_service()
    service = AuthService(db, email_service)
    return await service.reset_password(body.token, body.new_password)
