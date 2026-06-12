"""
用户模型 (User Model)

用户认证系统的核心数据表，存储注册用户的基本信息、
密码哈希、邮箱验证状态和密码重置令牌。

字段说明:
  - password_hash: bcrypt 哈希后的密码，绝不存储明文
  - is_verified: 邮箱是否已验证（未验证用户不能登录）
  - verification_token: 邮箱验证令牌（验证成功后清空）
  - reset_token / reset_token_expires: 密码重置令牌及过期时间

索引:
  - users.email 建有唯一索引，确保邮箱不重复且查询高效

扩展指南:
  如需扩展用户信息（昵称、角色、配额等），在此文件新增字段，
  然后在 auth_service.py 中相应处理业务逻辑。
"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """用户表 — 存储所有注册用户信息"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    verification_token: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    reset_token: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    reset_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
