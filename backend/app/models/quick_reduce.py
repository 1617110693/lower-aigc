"""
快速降低AIGC历史记录模型 (QuickReduceHistory Model)

存储登录用户在"快速降低AIGC"页面的改写历史。
游客（未登录用户）的历史记录仍由前端 localStorage 管理。

字段说明:
  - user_id: 关联用户，级联删除（删除用户时自动清除其历史）
  - original_text: 用户输入的原始文本
  - reduced_text: DeepSeek 改写后的文本
  - prompt_id: 使用的改写策略 ID
  - model: 使用的模型名称
  - preserve_word_count: 是否开启了"保持字数"选项
"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QuickReduceHistory(Base):
    """快速降低AIGC历史记录表"""

    __tablename__ = "quick_reduce_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    reduced_text: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    preserve_word_count: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
