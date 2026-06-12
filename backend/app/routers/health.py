"""
健康检查路由 (Health Check Router)

提供系统健康检查端点，用于:
  - Docker 容器健康探测
  - 负载均衡器 / K8s 探活
  - 前端检查后端是否可用

扩展指南:
  如需深度健康检查（如检测数据库连接、DeepSeek API 可达性），
  在此添加更详细的检查逻辑。
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    健康检查端点 — GET /api/v1/health

    返回简单的状态信息，200 表示服务正常运行。
    如果服务无法响应此接口，说明后端崩溃或无法连接。
    """
    return {"status": "ok", "message": "Lower-AIGC API is running"}
