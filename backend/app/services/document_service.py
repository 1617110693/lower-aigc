"""
文档服务模块 (Document Service)

核心业务逻辑层 — 所有文档相关功能的实现:
  - upload():          上传 DOCX → 解析段落 + 提取格式 → 存入数据库
  - list_documents():  分页查询用户的文档列表
  - get_document():    获取文档详情（含全部段落）
  - delete_document(): 删除文档（级联删除段落）
  - start_reduction(): 启动降重任务（异步后台执行）
  - get_reduction_status(): 查询降重进度
  - export_docx():     导出降重后的 DOCX（保留原始格式）

降重模式:
  全文模式 (full):
    将所有段落用 \n\n 拼接 → 一次 API 调用 → 尝试按 \n\n 拆分回段落
    优点: 上下文连贯，仅一次 API 调用；缺点: 可能丢失段落对应关系
  逐段模式 (paragraph):
    每个段落单独调用 API → 进度实时更新 → 失败不影响后续段落
    优点: 精确控制，单段失败不丢失全部结果；缺点: API 调用次数多

异步降重设计:
  降重任务通过 asyncio.create_task() 在后台运行，不阻塞 HTTP 响应。
  后台任务创建独立的数据库会话，避免与请求会话冲突。
  前端通过轮询 GET /{id}/status 获取实时进度。

扩展指南:
  - 如需添加新的降重模式（如按章节），在 _run_reduction() 中新增分支
  - 如需支持取消降重，可使用 asyncio.Event 作为取消信号
  - 如需支持批量导出，新增 export_multiple() 方法
"""

import asyncio
import logging
import tempfile
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
    """
    文档服务核心类

    每个 HTTP 请求创建独立的 DocumentService 实例，
    绑定一个数据库会话，所有操作在同一事务中完成。

    用法:
        service = DocumentService(db)
        docs = await service.list_documents(current_user)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 上传与解析 ────────────────────────────────────────────────────────────

    async def upload(self, user: User, file: UploadFile) -> dict:
        """
        上传并解析 DOCX 文件

        流程:
          1. 校验文件扩展名（仅允许 .docx）
          2. 校验文件大小（限制 MAX_UPLOAD_SIZE_MB）
          3. 保存到临时文件
          4. 调用 parse_docx() 提取段落文本和格式信息
          5. 提取文档标题
          6. 检查段落数量是否超过限制
          7. 创建 Document + Paragraph 记录入库

        参数:
            user: 当前登录用户
            file: 上传的 DOCX 文件（FastAPI UploadFile）
        返回:
            {"document_id": int, "paragraphs": [...]} 文档ID和段落列表
        """
        # 检查文件扩展名
        if not file.filename or not file.filename.lower().endswith(".docx"):
            raise ValueError("Only .docx files are supported")

        # 检查文件大小（内存中检查，确保不超过配置限制）
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValueError(
                f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit"
            )

        # 写入临时文件（python-docx 需要文件路径，不支持流式读取）
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # 解析 DOCX: 提取段落文本 + 格式信息
            paragraphs_data = parse_docx(tmp_path)
            # 提取文档标题: 优先用文档属性中的标题，其次用第一个标题样式段落
            title = extract_docx_title(tmp_path) or file.filename.replace(".docx", "")
        finally:
            # 立即清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

        # 检查段落数量限制
        if len(paragraphs_data) > settings.MAX_PARAGRAPHS_PER_DOC:
            raise ValueError(
                f"Document has {len(paragraphs_data)} paragraphs, "
                f"max {settings.MAX_PARAGRAPHS_PER_DOC} allowed"
            )

        # 创建文档记录
        doc = Document(
            user_id=user.id,
            original_filename=file.filename,
            title=title,
            status="parsed",  # 直接进入"已解析"状态
        )
        self.db.add(doc)
        await self.db.flush()  # flush 获取 doc.id

        # 批量创建段落记录
        for pdata in paragraphs_data:
            paragraph = Paragraph(
                document_id=doc.id,
                index=pdata["index"],
                original_text=pdata["text"],
                style_info=pdata.get("style_info"),
            )
            self.db.add(paragraph)

        await self.db.flush()

        # 重新加载文档（eager load 段落关系，避免异步延迟加载报错）
        result = await self.db.execute(
            select(Document)
            .where(Document.id == doc.id)
            .options(selectinload(Document.paragraphs))
        )
        doc = result.scalar_one()
        return {
            "document_id": doc.id,
            "paragraphs": [_paragraph_to_response(p) for p in doc.paragraphs],
        }

    # ── 文档 CRUD ─────────────────────────────────────────────────────────────

    async def list_documents(
        self, user: User, page: int = 1, size: int = 20
    ) -> dict:
        """
        分页查询用户的文档列表

        按更新时间倒序排列，最新上传/处理的文档在最前面。

        参数:
            user: 当前用户
            page: 页码（从 1 开始）
            size: 每页数量（默认 20，最大 100）
        返回:
            {"items": [...], "total": int, "page": int, "size": int}
        """
        # 查询当前用户的文档
        query = select(Document).where(Document.user_id == user.id)
        count_query = select(func.count(Document.id)).where(
            Document.user_id == user.id
        )

        # 获取总记录数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页查询
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
        """
        获取文档详情（含全部段落）

        参数:
            user: 当前用户
            document_id: 文档 ID
        返回:
            DocumentDetailResponse: 包含文档信息 + 段落列表
        异常:
            NotFoundError: 文档不存在或不属于当前用户
        """
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
        """
        删除文档

        ORM 级联设置 (cascade="all, delete-orphan") 会
        自动删除所有关联的段落，无需手动删除。

        参数:
            user: 当前用户
            document_id: 文档 ID
        返回:
            {"message": "删除成功提示"}
        异常:
            NotFoundError: 文档不存在或不属于当前用户
        """
        doc = await self._get_user_document(user, document_id)
        await self.db.delete(doc)
        await self.db.flush()
        return {"message": "Document deleted successfully"}

    # ── 降重 ─────────────────────────────────────────────────────────────────

    async def start_reduction(
        self, user: User, document_id: int, request: ReductionRequest
    ) -> dict:
        """
        启动降重任务

        验证请求参数后，将文档状态设为 "reducing"，
        然后通过 asyncio.create_task() 启动后台降重任务，
        立即返回响应，不等待任务完成。

        参数:
            user: 当前用户
            document_id: 文档 ID
            request: 降重请求（模式、策略ID、段落ID列表）
        返回:
            {"message": "任务已启动", "document_id": int}
        """
        doc = await self._get_user_document(user, document_id)

        # 防止重复启动降重
        if doc.status == "reducing":
            raise ValueError("Document is already being reduced")

        # 验证提示词 ID 有效性
        system_prompt = get_prompt_content(request.prompt_id)
        if not system_prompt:
            raise ValueError(f"Unknown prompt ID: {request.prompt_id}")

        # 更新状态为"降重中"
        doc.status = "reducing"
        doc.progress = 0
        await self.db.flush()

        # 创建后台异步任务 — 不阻塞响应
        # 注意: 后台任务需要自己管理数据库会话
        asyncio.create_task(
            self._run_reduction(
                doc, request.mode, system_prompt, request.paragraph_ids
            )
        )

        return {"message": "Reduction started", "document_id": document_id}

    async def get_reduction_status(
        self, user: User, document_id: int
    ) -> ReductionStatusResponse:
        """
        查询降重进度

        前端每 2 秒轮询一次此接口，获取最新进度。
        进度值 progress 仅在 reducing 状态时有意义。

        参数:
            user: 当前用户
            document_id: 文档 ID
        返回:
            ReductionStatusResponse: 包含状态和进度百分比
        """
        doc = await self._get_user_document(user, document_id)
        return ReductionStatusResponse(
            document_id=doc.id,
            status=doc.status,
            # 降重中返回实际进度，其他状态统一显示 100%
            progress=doc.progress if doc.status == "reducing" else 100,
        )

    # ── 导出 ─────────────────────────────────────────────────────────────────

    async def export_docx(self, user: User, document_id: int):
        """
        导出降重后的 DOCX 文件

        遍历文档所有段落，优先使用 reduced_text（降重结果），
        如果段落未降重或降重结果为空，则使用 original_text（原文）。
        通过 docx_builder 重建 DOCX 文件，保留原始格式。

        参数:
            user: 当前用户
            document_id: 文档 ID
        返回:
            (BytesIO buffer, filename): 文件流和下载文件名
        """
        doc = await self._get_user_document(user, document_id)

        # 收集导出数据: 按原始顺序，优先取降重文本
        paragraphs_data = []
        for para in sorted(doc.paragraphs, key=lambda p: p.index):
            text = (
                para.reduced_text
                if para.is_reduced and para.reduced_text
                else para.original_text
            )
            paragraphs_data.append(
                {"text": text, "style_info": para.style_info}
            )

        buf = build_docx(paragraphs_data)
        # 导出的文件名在原始名称后加 _reduced
        filename = doc.original_filename.replace(".docx", "_reduced.docx")
        return buf, filename

    # ═══════════════════════════════════════════════════════════════════════════
    # 内部方法 (Private)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _run_reduction(
        self,
        doc: Document,
        mode: str,
        system_prompt: str,
        paragraph_ids: list[int] | None,
    ):
        """
        后台降重任务 — 在 asyncio.create_task() 中运行

        创建独立的数据库会话，完成降重逻辑后更新文档状态。
        无论成功或失败，都会正确设置文档的最终状态。

        参数:
            doc: 文档对象（当前会话中的引用）
            mode: 降重模式 "full" | "paragraph"
            system_prompt: 系统提示词完整内容
            paragraph_ids: 逐段模式下指定的段落 ID 列表（可选）

        状态流转:
            成功: status → "completed"
            失败: status → "failed"
        """
        try:
            # 后台任务需要独立的数据库会话
            # 原因: 原请求会话可能在降重完成前就已关闭
            from app.database import async_session

            async with async_session() as db:
                # 在新会话中重新加载文档对象（级联加载段落，避免异步懒加载报错）
                result = await db.execute(
                    select(Document)
                    .where(Document.id == doc.id)
                    .options(selectinload(Document.paragraphs))
                )
                doc = result.scalar_one()

                # 获取目标段落列表
                paragraphs = sorted(doc.paragraphs, key=lambda p: p.index)
                if paragraph_ids:
                    # 逐段模式指定了段落 ID，只处理这些段落
                    paragraphs = [p for p in paragraphs if p.id in paragraph_ids]

                total = len(paragraphs)

                # 根据模式分发
                if mode == "full":
                    await self._reduce_full_text(
                        db, doc, paragraphs, system_prompt, total
                    )
                else:
                    await self._reduce_paragraph_by_paragraph(
                        db, doc, paragraphs, system_prompt, total
                    )

                # 降重成功
                doc.status = "completed"
                await db.commit()
                logger.info(f"Reduction completed for document {doc.id}")

        except Exception as e:
            logger.exception(f"Reduction failed for document {doc.id}: {e}")
            # 尝试标记文档为失败状态
            try:
                async with async_session() as db:
                    result = await db.execute(
                        select(Document).where(Document.id == doc.id)
                    )
                    doc = result.scalar_one()
                    doc.status = "failed"
                    await db.commit()
            except Exception:
                # 连状态更新都失败了，只能记录日志然后放弃
                pass

    async def _reduce_full_text(
        self, db, doc, paragraphs, system_prompt: str, total: int
    ):
        """
        全文降重模式

        1. 将所有段落用 \n\n 拼接为全文
        2. 一次 API 调用完成降重
        3. 尝试按 \n\n 拆分为段落
        4. 如果拆分数量匹配: 逐个写入 reduced_text
        5. 如果拆分数量不匹配: 全文结果存入第一段，其余段落用原文填充

        注意: 全文模式仅一次 API 调用，速度最快，但段落拆分可能不精确。
        """
        # 更新进度 — 开始调用 AI
        doc.progress = 20
        await db.flush()

        # 拼接全文（段落间用双换行分隔）
        full_text = "\n\n".join(p.original_text for p in paragraphs)
        reduced = await deepseek_client.reduce_text(full_text, system_prompt)

        # 更新进度 — AI 调用完成，开始处理结果
        doc.progress = 80
        await db.flush()

        # 尝试按双换行拆分回段落
        reduced_paragraphs = reduced.split("\n\n")

        if len(reduced_paragraphs) == len(paragraphs):
            # 拆分数量匹配 — 理想情况，精确对应
            for i, para in enumerate(paragraphs):
                para.reduced_text = reduced_paragraphs[i].strip()
                para.is_reduced = True
        else:
            # 拆分数量不匹配 — 降级处理
            # 将全部结果存入第一段，其余段落标记为"已处理（保留原文）"
            logger.warning(
                f"Full-text split mismatch: expected {len(paragraphs)}, "
                f"got {len(reduced_paragraphs)}. Storing as single result."
            )
            paragraphs[0].reduced_text = reduced
            paragraphs[0].is_reduced = True
            for para in paragraphs[1:]:
                para.reduced_text = para.original_text
                para.is_reduced = True

        await db.flush()

    async def _reduce_paragraph_by_paragraph(
        self, db, doc, paragraphs, system_prompt: str, total: int
    ):
        """
        逐段降重模式

        1. 逐个段落调用 DeepSeek API
        2. 每段成功后立即写入数据库并更新进度
        3. 单段失败不中止，记录错误信息后继续

        优势: 精确控制每段的降重结果，单段失败不影响后续
        劣势: API 调用次数多，耗时长（N 个段落 = N 次调用）

        进度更新: 每完成一个段落，更新 doc.progress 百分比，
        前端轮询接口读取此值显示进度条。
        """
        for i, para in enumerate(paragraphs):
            try:
                reduced = await deepseek_client.reduce_text(
                    para.original_text, system_prompt
                )
                para.reduced_text = reduced
                para.is_reduced = True
            except Exception as e:
                # 单段失败记录错误但不中断整体流程
                logger.error(f"Failed to reduce paragraph {para.id}: {e}")
                para.reduced_text = f"[Error: {e}]"
                para.is_reduced = True

            # 更新进度百分比
            doc.progress = int((i + 1) / total * 100)
            await db.flush()  # 每段都 flush 确保进度持久化

    # ── 权限校验 ──────────────────────────────────────────────────────────────

    async def _get_user_document(self, user: User, document_id: int) -> Document:
        """
        获取当前用户拥有的文档，或抛出异常

        安全: 查询条件同时包含 document_id 和 user_id，
        确保用户只能访问自己的文档（水平越权防护）。

        参数:
            user: 当前登录用户
            document_id: 文档 ID
        返回:
            Document ORM 对象
        异常:
            NotFoundError: 文档不存在或不属于当前用户
        """
        result = await self.db.execute(
            select(Document)
            .where(
                Document.id == document_id,
                Document.user_id == user.id,  # 关键: 限定查询到当前用户
            )
            .options(selectinload(Document.paragraphs))
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError("Document not found")
        return doc


def _paragraph_to_response(para: Paragraph) -> ParagraphResponse:
    """
    将段落 ORM 对象转换为 Pydantic 响应模型

    这是一个模块级工具函数，处理 style_info 的 JSON → StyleInfo 转换。
    如果 para.style_info 为 None（老数据或纯文本段落），
    则响应中 style_info 字段也为 None。
    """
    return ParagraphResponse(
        id=para.id,
        index=para.index,
        original_text=para.original_text,
        reduced_text=para.reduced_text,
        is_reduced=para.is_reduced,
        style_info=(
            StyleInfo.model_validate(para.style_info) if para.style_info else None
        ),
        created_at=para.created_at,
    )
