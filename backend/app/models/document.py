"""
文档与段落模型 (Document & Paragraph Models)

核心数据模型，存储用户上传的论文文档及其解析后的段落。

Document (文档):
  - 每个文档属于一个用户 (user_id FK→users)
  - status 反映文档的生命周期状态，详见下方状态流转说明
  - progress 记录降重进度百分比 (0-100)

Paragraph (段落):
  - 每个段落属于一个文档 (document_id FK→documents, 级联删除)
  - index 表示段落原始顺序
  - original_text 为解析出的原文，reduced_text 为降重后的文本
  - style_info 以 JSON 格式存储段落格式信息（字体、字号、对齐等）
  - is_reduced 标记该段落是否已完成降重

状态流转 (status lifecycle):
  uploaded → parsed → reducing → completed
                     ↘ failed

扩展指南:
  - 如需支持多版本降重结果，可新增版本号字段或单独建表
  - style_info 字段可扩展更多格式属性（颜色、背景色等）
"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    """文档表 — 存储上传的论文文档"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    title: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    # 文档状态: uploaded(已上传) / parsed(已解析) / reducing(降重中) / completed(已完成) / failed(失败)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    # 降重进度百分比 (0-100)，仅在 reducing 状态时有意义
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 一对多关联: 一个文档包含多个段落
    # cascade="all, delete-orphan": 删除文档时自动删除所有段落，
    #   从文档中移除的段落也会被删除（防止孤儿数据）
    paragraphs: Mapped[list["Paragraph"]] = relationship(
        "Paragraph",
        back_populates="document",
        order_by="Paragraph.index",
        cascade="all, delete-orphan",
    )


class Paragraph(Base):
    """段落表 — 存储文档中每个段落的原文和降重结果"""

    __tablename__ = "paragraphs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), index=True, nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    # 降重后的文本，默认为 NULL（尚未降重）
    reduced_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 是否已完成降重（区分"降重后与原文相同"和"尚未降重"）
    is_reduced: Mapped[bool] = mapped_column(Boolean, default=False)
    # 段落格式信息: JSON 存储，包含字体名、字号、加粗、斜体、对齐方式、行距、首行缩进等
    style_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # 多对一关联: 反向引用所属文档
    document: Mapped["Document"] = relationship(
        "Document", back_populates="paragraphs"
    )
