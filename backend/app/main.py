"""
Application Entry Point

FastAPI 应用的主入口文件，负责:
  1. 创建 FastAPI 应用实例
  2. 配置生命周期事件（启动时初始化数据库、关闭时清理）
  3. 注册 CORS 中间件（允许前端跨域访问）
  4. 注册全局异常处理器（统一错误响应格式）
  5. 挂载各模块的路由器

启动命令:
    uvicorn app.main:app --reload --port 8000
    或使用 UV: uv run uvicorn app.main:app --reload --port 8000

扩展指南:
  - 新增路由模块时，在此文件的 # 注册路由器 区域追加一行 include_router
  - 新增中间件（如请求日志、限流），在 CORS 之后添加
  - 新增异常类型时，在异常处理器区域添加对应的 @app.exception_handler
"""

import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import AppException
from app.database import init_db
from app.routers import admin, auth, document, health, system

# ── 运行时日志配置 ───────────────────────────────────────────────────────────
# 同时输出到控制台 (StreamHandler) 和文件 (RotatingFileHandler)
# 日志文件: backend/logs/app.log, 单文件最大 5MB, 保留 3 个旧文件

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            os.path.join(LOG_DIR, "app.log"),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)

# 抑制 watchfiles 文件变更日志（每次检测到变更都输出 INFO，太吵）
logging.getLogger("watchfiles").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理器

    startup: 应用启动时初始化数据库表结构
    shutdown: 应用关闭时的清理工作（当前无需特殊处理）

    用法:
        app = FastAPI(lifespan=lifespan)
    """
    # ── 启动阶段 ──
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode")
    await init_db()
    logger.info("Database tables initialized")

    yield  # 应用运行期间

    # ── 关闭阶段 ──
    logger.info("Shutting down")


# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 请求日志中间件 — 记录每个请求的方法、路径和响应状态码
# ═══════════════════════════════════════════════════════════════════════════════


@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time

    start = time.time()
    response = await call_next(request)
    if response.status_code >= 400:
        elapsed = (time.time() - start) * 1000
        logger.warning(
            "%s %s → %d (%.0fms)",
            request.method,
            request.url.path + ("?" + request.url.query if request.url.query else ""),
            response.status_code,
            elapsed,
        )
    return response


# ═══════════════════════════════════════════════════════════════════════════════
# CORS 中间件 — 允许前端跨域访问
# ═══════════════════════════════════════════════════════════════════════════════
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite 开发服务器
        "http://localhost:4173",   # Vite 预览服务器
        "http://localhost",         # Docker Nginx 生产
        "http://127.0.0.1",
        settings.APP_URL,          # 自定义前端地址（从 .env 读取）
    ],
    allow_credentials=True,        # 允许携带 Cookie（JWT 不使用 Cookie，但保留以备扩展）
    allow_methods=["*"],           # 允许所有 HTTP 方法
    allow_headers=["*"],           # 允许所有请求头
)

# ═══════════════════════════════════════════════════════════════════════════════
# 全局异常处理器
# ═══════════════════════════════════════════════════════════════════════════════


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pydantic 请求验证异常处理 — 422 Unprocessable Entity

    重写 FastAPI 默认处理器，记录详细的验证错误信息到日志文件，
    便于调试前后端字段名不匹配等问题。
    """
    body = exc.body if hasattr(exc, "body") else None
    errors = exc.errors()
    logger.warning(
        "422 Validation Error: %s %s — body=%s — errors=%s",
        request.method, request.url.path, body, errors,
    )
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    应用层异常统一处理

    捕获所有 AppException 子类（NotFoundError, ForbiddenError, ConflictError 等），
    转换为 JSON 响应，格式: {"detail": "错误消息"}
    HTTP 状态码由异常的 status_code 属性决定。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    未预期异常兜底处理

    捕获未被上层处理的所有异常，返回 500 错误。
    详细错误信息仅输出到日志，不暴露给前端（安全考虑）。
    """
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 注册路由器
# ═══════════════════════════════════════════════════════════════════════════════

# 健康检查
app.include_router(health.router, prefix="/api/v1", tags=["Health"])

# 认证相关: /api/v1/auth/*
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

# 文档相关: /api/v1/documents/*
app.include_router(document.router, prefix="/api/v1/documents", tags=["Documents"])

# 系统相关: /api/v1/system/*
app.include_router(system.router, prefix="/api/v1/system", tags=["System"])
app.include_router(admin.router, prefix="/api/v1/system", tags=["Admin"])


@app.get("/")
async def root():
    """
    根路径 — GET /

    返回应用名称和版本号，可用于快速验证服务是否正常运行。
    """
    return {"name": settings.APP_NAME, "version": "1.0.0"}
