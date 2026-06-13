"""
系统路由 (System Router)

提供系统级 API 端点:
  POST /reduce-text              — 粘贴文本快速降低AIGC（无需上传文档）
  GET  /quick-reduce-history      — 获取快速降低AIGC历史记录（需登录）
  POST /quick-reduce-history      — 保存快速降低AIGC历史记录（需登录）
  DELETE /quick-reduce-history/{id} — 删除单条历史记录
  DELETE /quick-reduce-history    — 清空全部历史记录

扩展指南:
  - 如需添加系统配置端点，在此文件中新增路由
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User, QuickReduceHistory, CustomPrompt
from app.schemas.document import (
    CustomPromptCreate,
    CustomPromptUpdate,
    CustomPromptResponse,
)
from app.services.deepseek_service import deepseek_client, get_prompt_content, get_prompts

logger = logging.getLogger(__name__)

router = APIRouter()


# ── 请求/响应模型 ──────────────────────────────────────────────────────────────

class ReduceTextRequest(BaseModel):
    """
    文本降低AIGC请求

    参数:
        text: 待处理的文本（支持段落或全文）
        prompt_id: 降低AIGC策略 ID（如 "academic-paraphrase"）
        model: 模型名称，deepseek-v4-flash(快速) 或 deepseek-v4-pro(高质量)
    """
    text: str = Field(..., min_length=10, max_length=50000, description="待处理的文本")
    prompt_id: str = Field(..., min_length=1, description="降低AIGC策略ID")
    model: str = Field(
        "deepseek-v4-flash",
        description="Model name: deepseek-v4-flash or deepseek-v4-pro"
    )
    preserve_word_count: bool = Field(
        False,
        description="Whether to keep output word count similar to input"
    )


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
async def reduce_text(
    request: ReduceTextRequest,
    db: AsyncSession = Depends(get_db),
):
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
    # 验证提示词 ID（支持内置和自定义策略）
    system_prompt = await get_prompt_content(request.prompt_id, db)
    if not system_prompt:
        raise ValueError(f"Unknown prompt ID: {request.prompt_id}")

    logger.info(
        "reduce-text: prompt_id=%s, model=%s, text_len=%d, preserve_word_count=%s",
        request.prompt_id, request.model, len(request.text), request.preserve_word_count,
    )

    # 调用 DeepSeek API 进行降低AIGC
    reduced = await deepseek_client.reduce_text(
        request.text,
        system_prompt,
        model=request.model,
        preserve_word_count=request.preserve_word_count,
    )

    return ReduceTextResponse(
        original_text=request.text,
        reduced_text=reduced,
    )


# ── 快速降低AIGC历史记录 (Quick Reduce History) ─────────────────────────────────
# 登录用户的历史记录存储在服务端，游客仍使用前端 localStorage
# 这样用户换浏览器/设备也能看到自己的历史

class SaveHistoryRequest(BaseModel):
    """保存历史记录请求"""
    original_text: str
    reduced_text: str
    prompt_id: str
    model: str
    preserve_word_count: bool = False


class HistoryItem(BaseModel):
    """单条历史记录"""
    id: int
    original_text: str
    reduced_text: str
    prompt_id: str
    model: str
    preserve_word_count: bool
    created_at: str

    model_config = {"from_attributes": True}


class HistoryListResponse(BaseModel):
    """历史记录列表"""
    items: list[HistoryItem]
    total: int


class SaveHistoryResponse(BaseModel):
    """保存历史记录响应"""
    id: int
    message: str = "saved"


@router.get("/quick-reduce-history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(50, ge=1, le=100, description="每页条数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的快速降低AIGC历史记录 — GET /api/v1/system/quick-reduce-history
    按创建时间倒序排列，支持分页。
    """
    logger.info(
        "GET quick-reduce-history: user_id=%s, page=%s, size=%s",
        current_user.id, page, size,
    )
    # 查询总数
    count_q = select(func.count()).select_from(QuickReduceHistory).where(
        QuickReduceHistory.user_id == current_user.id
    )
    total = (await db.execute(count_q)).scalar() or 0

    # 查询列表
    q = (
        select(QuickReduceHistory)
        .where(QuickReduceHistory.user_id == current_user.id)
        .order_by(QuickReduceHistory.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(q)).scalars().all()

    items = [
        HistoryItem(
            id=r.id,
            original_text=r.original_text,
            reduced_text=r.reduced_text,
            prompt_id=r.prompt_id,
            model=r.model,
            preserve_word_count=r.preserve_word_count,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]
    return HistoryListResponse(items=items, total=total)


@router.post("/quick-reduce-history", response_model=SaveHistoryResponse)
async def save_history(
    request: SaveHistoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    保存一条快速降低AIGC历史记录 — POST /api/v1/system/quick-reduce-history
    """
    logger.info(
        "POST quick-reduce-history: user_id=%s, prompt_id=%s, model=%s, text_len=%d",
        current_user.id, request.prompt_id, request.model, len(request.original_text),
    )
    entry = QuickReduceHistory(
        user_id=current_user.id,
        original_text=request.original_text,
        reduced_text=request.reduced_text,
        prompt_id=request.prompt_id,
        model=request.model,
        preserve_word_count=request.preserve_word_count,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return SaveHistoryResponse(id=entry.id)


@router.delete("/quick-reduce-history/{entry_id}")
async def delete_history_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除单条历史记录 — DELETE /api/v1/system/quick-reduce-history/{id}
    """
    q = delete(QuickReduceHistory).where(
        QuickReduceHistory.id == entry_id,
        QuickReduceHistory.user_id == current_user.id,
    )
    result = await db.execute(q)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "deleted"}


@router.delete("/quick-reduce-history")
async def clear_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    清空当前用户全部历史记录 — DELETE /api/v1/system/quick-reduce-history
    """
    q = delete(QuickReduceHistory).where(
        QuickReduceHistory.user_id == current_user.id
    )
    result = await db.execute(q)
    return {"message": f"cleared {result.rowcount} entries"}


# ── 自定义改写策略 (Custom Prompts) ────────────────────────────────────────────


@router.get("/prompts", response_model=list[CustomPromptResponse])
async def list_custom_prompts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的自定义改写策略 — GET /api/v1/system/prompts

    返回完整内容（含 system_content），供管理页面使用。
    按创建时间升序排列。
    """
    result = await db.execute(
        select(CustomPrompt)
        .where(CustomPrompt.user_id == current_user.id)
        .order_by(CustomPrompt.created_at.asc())
    )
    customs = result.scalars().all()
    return [
        CustomPromptResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            system_content=c.system_content,
            is_active=c.is_active,
            created_at=c.created_at.isoformat() if c.created_at else "",
            updated_at=c.updated_at.isoformat() if c.updated_at else "",
        )
        for c in customs
    ]


@router.post("/prompts", response_model=CustomPromptResponse, status_code=201)
async def create_custom_prompt(
    request: CustomPromptCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建自定义改写策略 — POST /api/v1/system/prompts
    """
    prompt = CustomPrompt(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        system_content=request.system_content,
    )
    db.add(prompt)
    await db.flush()
    await db.refresh(prompt)
    logger.info("Custom prompt created: id=%d, user_id=%d", prompt.id, current_user.id)
    return CustomPromptResponse(
        id=prompt.id,
        name=prompt.name,
        description=prompt.description,
        system_content=prompt.system_content,
        is_active=prompt.is_active,
        created_at=prompt.created_at.isoformat() if prompt.created_at else "",
        updated_at=prompt.updated_at.isoformat() if prompt.updated_at else "",
    )


@router.put("/prompts/{prompt_id}", response_model=CustomPromptResponse)
async def update_custom_prompt(
    prompt_id: int,
    request: CustomPromptUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新自定义改写策略 — PUT /api/v1/system/prompts/{id}
    """
    result = await db.execute(
        select(CustomPrompt).where(
            CustomPrompt.id == prompt_id,
            CustomPrompt.user_id == current_user.id,
        )
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Custom prompt not found")

    if request.name is not None:
        prompt.name = request.name
    if request.description is not None:
        prompt.description = request.description
    if request.system_content is not None:
        prompt.system_content = request.system_content
    if request.is_active is not None:
        prompt.is_active = request.is_active

    await db.flush()
    await db.refresh(prompt)
    return CustomPromptResponse(
        id=prompt.id,
        name=prompt.name,
        description=prompt.description,
        system_content=prompt.system_content,
        is_active=prompt.is_active,
        created_at=prompt.created_at.isoformat() if prompt.created_at else "",
        updated_at=prompt.updated_at.isoformat() if prompt.updated_at else "",
    )


@router.delete("/prompts/{prompt_id}")
async def delete_custom_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除自定义改写策略 — DELETE /api/v1/system/prompts/{id}
    """
    result = await db.execute(
        select(CustomPrompt).where(
            CustomPrompt.id == prompt_id,
            CustomPrompt.user_id == current_user.id,
        )
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Custom prompt not found")

    await db.delete(prompt)
    await db.flush()
    logger.info("Custom prompt deleted: id=%d, user_id=%d", prompt_id, current_user.id)
    return {"message": "deleted"}
