"""
系统路由 (System Router)

提供系统级 API 端点:
  POST /reduce-text          — 粘贴文本快速降低AIGC（无需上传文档）

扩展指南:
  - 如需添加系统配置端点，在此文件中新增路由
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.deepseek_service import deepseek_client, get_prompt_content

logger = logging.getLogger(__name__)

router = APIRouter()


# ── 请求/响应模型 ──────────────────────────────────────────────────────────────

class ReduceTextRequest(BaseModel):
    """
    文本降低AIGC请求

    参数:
        text: 待处理的文本（支持段落或全文）
        prompt_id: 降低AIGC策略 ID（如 "academic-paraphrase"）
    """
    text: str = Field(..., min_length=10, max_length=50000, description="待处理的文本")
    prompt_id: str = Field(..., min_length=1, description="降低AIGC策略ID")


class ReduceTextResponse(BaseModel):
    """
    文本降低AIGC响应

    返回:
        original_text: 原始文本
        reduced_text: 降低AIGC后的文本
    """
    original_text: str
    reduced_text: str


# ── 端点 ────────────────────────────────────────────────────────────────────────

@router.post("/reduce-text", response_model=ReduceTextResponse)
async def reduce_text(request: ReduceTextRequest):
    """
    快速降低AIGC — POST /api/v1/system/reduce-text

    直接粘贴文本即可降低AIGC，无需上传 DOCX 文件。
    适用于快速改写单个段落或全文。

    请求体:
        {
            "text": "待改写的文本内容...",
            "prompt_id": "academic-paraphrase"
        }

    响应:
        {
            "original_text": "原始文本",
            "reduced_text": "降低AIGC后的文本"
        }

    错误:
        400: 文本过长或 prompt_id 无效
        500: API 调用失败
    """
    # 验证提示词 ID
    system_prompt = get_prompt_content(request.prompt_id)
    if not system_prompt:
        raise ValueError(f"Unknown prompt ID: {request.prompt_id}")

    # 调用 DeepSeek API 进行降低AIGC
    reduced = await deepseek_client.reduce_text(request.text, system_prompt)

    return ReduceTextResponse(
        original_text=request.text,
        reduced_text=reduced,
    )
