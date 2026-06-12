"""
文档路由 (Document Router)

提供文档管理相关的 REST API 端点:
  GET  /prompts              — 获取可用降重策略列表
  POST /upload               — 上传 DOCX 文件
  GET  /                     — 文档列表（分页）
  GET  /{document_id}        — 文档详情（含段落）
  DELETE /{document_id}      — 删除文档
  POST /{document_id}/reduce — 启动降重
  GET  /{document_id}/status — 查询降重进度
  GET  /{document_id}/export — 导出 DOCX

所有端点挂载在 /api/v1/documents 前缀下（在 main.py 中配置）。
除 /prompts 外，所有端点都需要认证（JWT Bearer token）。

扩展指南:
  - 如需添加批量导出，新增 POST /batch-export 端点
  - 如需降重历史记录，新增 GET /{id}/history 端点
"""

import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentResponse,
    ReductionRequest,
    ReductionStatusResponse,
)
from app.services.document_service import DocumentService
from app.services.deepseek_service import get_prompts
from app.schemas.document import PromptInfo

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/prompts", response_model=list[PromptInfo])
async def list_prompts():
    """
    获取可用的降重策略列表 — GET /api/v1/documents/prompts

    无需认证即可访问。
    返回策略的 ID、中文名称和描述，用于前端下拉选择。

    注意: 返回的 PromptInfo 不包含完整的系统提示词内容，
    完整提示词在启动降重时才通过 prompt_id 查找。

    响应:
        [{"id": "academic-paraphrase", "name": "学术改写", "description": "..."}, ...]
    """
    return get_prompts()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传 DOCX 文件 — POST /api/v1/documents/upload

    上传一个 .docx 文件，后端自动解析段落并提取格式信息。
    解析成功后返回文档 ID 和段落列表。

    请求格式: multipart/form-data
      - file: .docx 文件（必填）

    响应:
        {"document_id": int, "paragraphs": [...]}
    错误:
        400: 文件格式错误、文件过大或段落数超限
        401: 未登录
    """
    service = DocumentService(db)
    return await service.upload(current_user, file)


@router.get("/")
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    文档列表 — GET /api/v1/documents

    获取当前用户的文档列表，按更新时间倒序排列。

    查询参数:
        page: 页码（从 1 开始，默认 1）
        size: 每页数量（1-100，默认 20）

    响应:
        {"items": [...], "total": int, "page": int, "size": int}
    错误:
        401: 未登录
    """
    service = DocumentService(db)
    return await service.list_documents(current_user, page, size)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    文档详情 — GET /api/v1/documents/{document_id}

    获取文档基本信息及全部段落（含原文、降重结果、格式信息）。

    路径参数:
        document_id: 文档 ID

    响应:
        DocumentDetailResponse: 文档信息 + 段落列表
    错误:
        404: 文档不存在或不属于当前用户
        401: 未登录
    """
    service = DocumentService(db)
    return await service.get_document(current_user, document_id)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除文档 — DELETE /api/v1/documents/{document_id}

    删除文档及其所有关联段落（ORM 级联删除）。

    响应:
        {"message": "删除成功提示"}
    错误:
        404: 文档不存在或不属于当前用户
        401: 未登录
    """
    service = DocumentService(db)
    return await service.delete_document(current_user, document_id)


@router.post("/{document_id}/reduce")
async def reduce_document(
    document_id: int,
    request: ReductionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    启动降重 — POST /api/v1/documents/{document_id}/reduce

    启动 AIGC 降重后台任务。任务异步执行，立即返回。
    前端应通过轮询 GET /{id}/status 获取进度。

    请求体:
        {
            "mode": "full" | "paragraph",
            "prompt_id": "academic-paraphrase",
            "paragraph_ids": [1, 2, 3]  // 逐段模式可选，指定要降重的段落
        }

    响应:
        {"message": "任务已启动", "document_id": int}
    错误:
        400: 提示词 ID 无效或文档已在降重中
        404: 文档不存在
        401: 未登录
    """
    service = DocumentService(db)
    return await service.start_reduction(current_user, document_id, request)


@router.get("/{document_id}/status", response_model=ReductionStatusResponse)
async def get_reduction_status(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    查询降重进度 — GET /api/v1/documents/{document_id}/status

    前端每 2 秒轮询一次此接口获取实时进度。
    进度值 0-100，仅在 reducing 状态时有意义。

    响应:
        {
            "document_id": int,
            "status": "reducing" | "completed" | "failed",
            "progress": 0-100
        }
    错误:
        404: 文档不存在
        401: 未登录
    """
    service = DocumentService(db)
    return await service.get_reduction_status(current_user, document_id)


@router.get("/{document_id}/export")
async def export_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    导出 DOCX — GET /api/v1/documents/{document_id}/export

    将降重后的文档导出为 .docx 文件下载。
    优先使用 reduced_text（降重结果），未降重的段落保留原文。
    导出文件保留原始格式（字体、字号、对齐等）。

    响应:
        StreamingResponse: .docx 文件流，Content-Disposition 设为附件下载
    错误:
        404: 文档不存在
        401: 未登录
    """
    service = DocumentService(db)
    buf, filename = await service.export_docx(current_user, document_id)

    # StreamingResponse 流式返回文件，不会一次性加载全部内容到内存
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
