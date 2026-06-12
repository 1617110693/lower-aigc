"""Document service: upload, parse, reduce, export."""

import asyncio
import logging
import tempfile
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import User
from app.models.document import Document, Paragraph
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentResponse,
    ParagraphResponse,
    ReductionRequest,
    ReductionStatusResponse,
    StyleInfo,
)
from app.services.deepseek_service import deepseek_client, get_prompt_content
from app.utils.docx_builder import build_docx
from app.utils.docx_parser import extract_docx_title, parse_docx

logger = logging.getLogger(__name__)


class DocumentService:
    """Handles document CRUD, parsing, reduction, and export."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload(self, user: User, file: UploadFile) -> dict:
        """Upload a DOCX file, parse it, and store paragraphs."""
        # Validate file extension
        if not file.filename or not file.filename.lower().endswith(".docx"):
            raise ValueError("Only .docx files are supported")

        # Validate size
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValueError(f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

        # Save to temp file and parse
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            paragraphs_data = parse_docx(tmp_path)
            title = extract_docx_title(tmp_path) or file.filename.replace(".docx", "")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if len(paragraphs_data) > settings.MAX_PARAGRAPHS_PER_DOC:
            raise ValueError(
                f"Document has {len(paragraphs_data)} paragraphs, "
                f"max {settings.MAX_PARAGRAPHS_PER_DOC} allowed"
            )

        # Create document record
        doc = Document(
            user_id=user.id,
            original_filename=file.filename,
            title=title,
            status="parsed",
        )
        self.db.add(doc)
        await self.db.flush()

        # Create paragraph records
        for pdata in paragraphs_data:
            paragraph = Paragraph(
                document_id=doc.id,
                index=pdata["index"],
                original_text=pdata["text"],
                style_info=pdata.get("style_info"),
            )
            self.db.add(paragraph)

        await self.db.flush()

        # Reload with paragraphs
        result = await self.db.execute(
            select(Document).where(Document.id == doc.id)
        )
        doc = result.scalar_one()
        return {
            "document_id": doc.id,
            "paragraphs": [_paragraph_to_response(p) for p in doc.paragraphs],
        }

    async def list_documents(
        self, user: User, page: int = 1, size: int = 20
    ) -> dict:
        """List user's documents, paginated."""
        query = select(Document).where(Document.user_id == user.id)
        count_query = select(func.count(Document.id)).where(Document.user_id == user.id)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.db.execute(
            query.order_by(Document.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        documents = result.scalars().all()

        return {
            "items": [DocumentResponse.model_validate(d) for d in documents],
            "total": total,
            "page": page,
            "size": size,
        }

    async def get_document(self, user: User, document_id: int) -> DocumentDetailResponse:
        """Get a document with its paragraphs."""
        doc = await self._get_user_document(user, document_id)
        return DocumentDetailResponse(
            id=doc.id,
            original_filename=doc.original_filename,
            title=doc.title,
            status=doc.status,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            paragraphs=[_paragraph_to_response(p) for p in doc.paragraphs],
        )

    async def delete_document(self, user: User, document_id: int) -> dict:
        """Delete a document and its paragraphs."""
        doc = await self._get_user_document(user, document_id)
        await self.db.delete(doc)
        await self.db.flush()
        return {"message": "Document deleted successfully"}

    async def start_reduction(
        self, user: User, document_id: int, request: ReductionRequest
    ) -> dict:
        """Start AIGC reduction for a document."""
        doc = await self._get_user_document(user, document_id)
        if doc.status == "reducing":
            raise ValueError("Document is already being reduced")

        system_prompt = get_prompt_content(request.prompt_id)
        if not system_prompt:
            raise ValueError(f"Unknown prompt ID: {request.prompt_id}")

        doc.status = "reducing"
        doc.progress = 0
        await self.db.flush()

        # Launch reduction as background task
        asyncio.create_task(
            self._run_reduction(doc, request.mode, system_prompt, request.paragraph_ids)
        )

        return {"message": "Reduction started", "document_id": document_id}

    async def get_reduction_status(
        self, user: User, document_id: int
    ) -> ReductionStatusResponse:
        """Get the current reduction status for a document."""
        doc = await self._get_user_document(user, document_id)
        return ReductionStatusResponse(
            document_id=doc.id,
            status=doc.status,
            progress=doc.progress if doc.status == "reducing" else 100,
        )

    async def export_docx(self, user: User, document_id: int):
        """Export a document as a .docx file."""
        doc = await self._get_user_document(user, document_id)

        paragraphs_data = []
        for para in sorted(doc.paragraphs, key=lambda p: p.index):
            text = para.reduced_text if para.is_reduced and para.reduced_text else para.original_text
            paragraphs_data.append({
                "text": text,
                "style_info": para.style_info,
            })

        buf = build_docx(paragraphs_data)
        filename = doc.original_filename.replace(".docx", "_reduced.docx")
        return buf, filename

    async def _run_reduction(
        self,
        doc: Document,
        mode: str,
        system_prompt: str,
        paragraph_ids: list[int] | None,
    ):
        """Background task: perform reduction and update paragraphs."""
        try:
            # Re-acquire a DB session for the background task
            from app.database import async_session

            async with async_session() as db:
                # Re-fetch the document
                result = await db.execute(select(Document).where(Document.id == doc.id))
                doc = result.scalar_one()

                # Get target paragraphs
                paragraphs = sorted(doc.paragraphs, key=lambda p: p.index)
                if paragraph_ids:
                    paragraphs = [p for p in paragraphs if p.id in paragraph_ids]

                total = len(paragraphs)

                if mode == "full":
                    await self._reduce_full_text(db, doc, paragraphs, system_prompt, total)
                else:
                    await self._reduce_paragraph_by_paragraph(db, doc, paragraphs, system_prompt, total)

                doc.status = "completed"
                await db.commit()
                logger.info(f"Reduction completed for document {doc.id}")

        except Exception as e:
            logger.exception(f"Reduction failed for document {doc.id}: {e}")
            try:
                async with async_session() as db:
                    result = await db.execute(select(Document).where(Document.id == doc.id))
                    doc = result.scalar_one()
                    doc.status = "failed"
                    await db.commit()
            except Exception:
                pass

    async def _reduce_full_text(
        self, db, doc, paragraphs, system_prompt: str, total: int
    ):
        """Full-text reduction: combine all paragraphs, reduce, then split."""
        full_text = "\n\n".join(p.original_text for p in paragraphs)
        reduced = await deepseek_client.reduce_text(full_text, system_prompt)

        # Try to split reduced text back into paragraphs
        reduced_paragraphs = reduced.split("\n\n")

        if len(reduced_paragraphs) == len(paragraphs):
            for i, para in enumerate(paragraphs):
                para.reduced_text = reduced_paragraphs[i].strip()
                para.is_reduced = True
        else:
            # If split count doesn't match, store full result on first paragraph
            # and mark others with their original text
            paragraphs[0].reduced_text = reduced
            paragraphs[0].is_reduced = True
            for para in paragraphs[1:]:
                para.reduced_text = para.original_text
                para.is_reduced = True

        await db.flush()

    async def _reduce_paragraph_by_paragraph(
        self, db, doc, paragraphs, system_prompt: str, total: int
    ):
        """Paragraph-by-paragraph reduction with progress tracking."""
        for i, para in enumerate(paragraphs):
            try:
                reduced = await deepseek_client.reduce_text(
                    para.original_text, system_prompt
                )
                para.reduced_text = reduced
                para.is_reduced = True
            except Exception as e:
                logger.error(f"Failed to reduce paragraph {para.id}: {e}")
                para.reduced_text = f"[Error: {e}]"
                para.is_reduced = True

            doc.progress = int((i + 1) / total * 100)
            await db.flush()

    async def _get_user_document(self, user: User, document_id: int) -> Document:
        """Get a document owned by the current user, or raise an error."""
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id, Document.user_id == user.id
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError("Document not found")
        return doc


def _paragraph_to_response(para: Paragraph) -> ParagraphResponse:
    """Convert a Paragraph model to a ParagraphResponse schema."""
    return ParagraphResponse(
        id=para.id,
        index=para.index,
        original_text=para.original_text,
        reduced_text=para.reduced_text,
        is_reduced=para.is_reduced,
        style_info=StyleInfo.model_validate(para.style_info) if para.style_info else None,
        created_at=para.created_at,
    )
