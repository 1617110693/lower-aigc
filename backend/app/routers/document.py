"""Document router: upload, list, get, reduce, export, delete."""

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
    """Get available reduction prompts."""
    return get_prompts()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a DOCX file and parse its content."""
    service = DocumentService(db)
    return await service.upload(current_user, file)


@router.get("/")
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List current user's documents."""
    service = DocumentService(db)
    return await service.list_documents(current_user, page, size)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a document with its paragraphs."""
    service = DocumentService(db)
    return await service.get_document(current_user, document_id)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document."""
    service = DocumentService(db)
    return await service.delete_document(current_user, document_id)


@router.post("/{document_id}/reduce")
async def reduce_document(
    document_id: int,
    request: ReductionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start AIGC reduction for a document."""
    service = DocumentService(db)
    return await service.start_reduction(current_user, document_id, request)


@router.get("/{document_id}/status", response_model=ReductionStatusResponse)
async def get_reduction_status(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get reduction progress for a document."""
    service = DocumentService(db)
    return await service.get_reduction_status(current_user, document_id)


@router.get("/{document_id}/export")
async def export_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export document as DOCX."""
    service = DocumentService(db)
    buf, filename = await service.export_docx(current_user, document_id)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
