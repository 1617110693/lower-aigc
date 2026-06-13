"""
自定义改写策略模型 (CustomPrompt Model)

用户可以创建自己的降AIGC改写策略，与内置策略并行使用。
内置策略仍保留在代码中（deepseek_service.py），不可被用户编辑或删除。

字段说明:
  - user_id: 关联用户，级联删除
  - name: 策略名称（用户自定义）
  - description: 策略描述摘要
  - system_content: 完整的系统提示词内容
  - is_active: 是否启用，禁用后不会出现在策略选择器中
"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CustomPrompt(Base):
    """用户自定义改写策略表"""

    __tablename__ = "custom_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    system_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
