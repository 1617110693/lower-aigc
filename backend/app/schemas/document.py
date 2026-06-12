"""
文档模块的请求/响应 Schema (Document Schemas)

定义了文档相关接口（上传、降重、导出）的输入输出数据结构。

关键 Schema:
  - StyleInfo: 段落格式化信息，在解析 DOCX 时提取，导出时还原
  - ReductionRequest: 降重请求，支持 full(全文) / paragraph(逐段) 两种模式
  - PromptInfo: 内置降重策略的描述信息（不含完整提示词）

扩展指南:
  在 StyleInfo 中新增格式字段时，需同步更新 docx_parser.extract_style_info()
  和 docx_builder._add_paragraph_with_style() 两处。
"""

from datetime import datetime
from pydantic import BaseModel, Field


class StyleInfo(BaseModel):
    """
    段落样式信息

    从 DOCX 原始段落中提取，导出时用于还原格式。
    所有字段均为可选（None 表示忽略该格式）。

    字段说明:
      - alignment: 0=左对齐, 1=居中, 2=右对齐, 3=两端对齐
      - line_spacing: 行距倍数（如 1.5 表示 1.5 倍行距）
      - first_line_indent: 首行缩进值，单位 pt
      - is_heading: 是否为标题样式
      - heading_level: 标题级别 1-9
    """
    font_name: str | None = None
    font_size: float | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    alignment: int | None = None
    line_spacing: float | None = None
    first_line_indent: float | None = None
    is_heading: bool = False
    heading_level: int | None = None


class ParagraphResponse(BaseModel):
    """段落响应 — 包含原文和降重结果的完整段落数据"""
    id: int
    index: int
    original_text: str
    reduced_text: str | None = None
    is_reduced: bool = False
    style_info: StyleInfo | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """文档列表响应 — 不含段落详情，仅用于列表展示"""
    id: int
    original_filename: str
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应 — 继承 DocumentResponse，增加段落列表"""
    paragraphs: list[ParagraphResponse] = []


class ReductionRequest(BaseModel):
    """
    降重请求

    mode: full(全文降重) 或 paragraph(逐段降重)
    prompt_id: 要使用的系统提示词 ID（见 /prompts 接口返回的列表）
    paragraph_ids: 逐段模式下需降重的段落 ID 列表，全文模式可省略
    """
    mode: str = Field(..., description="full or paragraph")
    prompt_id: str = Field(..., description="ID of the system prompt to use")
    paragraph_ids: list[int] | None = Field(
        None, description="Paragraph IDs for paragraph mode"
    )


class ReductionStatusResponse(BaseModel):
    """
    降重状态响应 — 前端轮询此接口获取进度

    progress 仅在 reducing 状态时有意义 (0-100)，
    其他状态下可根据 status 判断最终结果。
    """
    document_id: int
    status: str
    progress: int = 0
    error_message: str | None = None


class PromptInfo(BaseModel):
    """降重策略信息 — 展示策略的 ID、名称和描述"""
    id: str
    name: str
    description: str
