"""Document request/response schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class StyleInfo(BaseModel):
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
    id: int
    index: int
    original_text: str
    reduced_text: str | None = None
    is_reduced: bool = False
    style_info: StyleInfo | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: int
    original_filename: str
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    paragraphs: list[ParagraphResponse] = []


class ReductionRequest(BaseModel):
    mode: str = Field(..., description="full or paragraph")
    prompt_id: str = Field(..., description="ID of the system prompt to use")
    paragraph_ids: list[int] | None = Field(None, description="Paragraph IDs for paragraph mode")


class ReductionStatusResponse(BaseModel):
    document_id: int
    status: str
    progress: int = 0
    error_message: str | None = None


class PromptInfo(BaseModel):
    id: str
    name: str
    description: str
