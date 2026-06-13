"""
管理员路由 (Admin Router)

提供管理员专用的系统管理端点:
  GET  /system/admin/env  — 读取 .env 配置（管理员）
  PUT  /system/admin/env  — 更新 .env 配置（管理员）

所有端点挂载在 /api/v1 前缀下，需要管理员权限。
"""

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.deps import get_current_admin_user
from app.models import User

router = APIRouter()

# 定位项目根目录的 .env 文件
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


# ── 请求/响应 Schema ────────────────────────────────────────────────────────────


class EnvSettingsResponse(BaseModel):
    """读取 .env 的响应：返回原始文本和解析后的键值对"""
    content: str = Field(..., description="原始 .env 文件内容")
    settings: dict[str, str] = Field(..., description="解析后的键值对")


class EnvSettingsUpdate(BaseModel):
    """更新 .env 的请求：提供要修改的键值对"""
    settings: dict[str, str] = Field(..., description="要更新的键值对")


def _parse_env(content: str) -> dict[str, str]:
    """解析 .env 文件内容为键值对字典"""
    result = {}
    for line in content.splitlines():
        line = line.strip()
        # 跳过空行和注释
        if not line or line.startswith("#"):
            continue
        # 匹配 KEY=VALUE 或 KEY="VALUE" 或 KEY='VALUE'
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$', line)
        if match:
            key = match.group(1)
            value = match.group(2).strip()
            # 去掉首尾引号
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            result[key] = value
    return result


def _update_env_file(updates: dict[str, str]) -> str:
    """
    更新 .env 文件中指定的键值，保留注释和空行

    返回更新后的完整文件内容。
    """
    if not _ENV_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=".env file not found",
        )

    original = _ENV_FILE.read_text(encoding="utf-8")
    new_lines = []

    for line in original.splitlines():
        stripped = line.strip()
        # 保留空行和注释
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        # 尝试匹配 KEY=VALUE 行
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$', stripped)
        if match:
            key = match.group(1)
            if key in updates:
                new_value = updates[key]
                # 保留注释（如果有行内注释）
                inline_comment = ""
                comment_match = re.search(r'(\s+#\s*.*)$', stripped)
                if comment_match:
                    inline_comment = comment_match.group(1)
                # 值包含空格或特殊字符时用引号包裹
                # JSON 数组（以 [ 开头）直接写入，不需要额外引号
                if not new_value.strip().startswith("["):
                    if any(c in new_value for c in [' ', '#']):
                        new_value = f'"{new_value}"'
                new_lines.append(f"{key}={new_value}{inline_comment}")
                continue

        # 未匹配或不需要更新的行，保持原样
        new_lines.append(line)

    new_content = "\n".join(new_lines) + "\n"
    _ENV_FILE.write_text(new_content, encoding="utf-8")
    return new_content


# ── 端点 ────────────────────────────────────────────────────────────────────────


@router.get("/admin/env", response_model=EnvSettingsResponse)
async def get_env_config(
    current_user: User = Depends(get_current_admin_user),
):
    """
    读取 .env 配置 — GET /api/v1/system/admin/env

    返回原始文件内容和解析后的键值对。
    需要管理员权限。
    """
    if not _ENV_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=".env file not found",
        )
    content = _ENV_FILE.read_text(encoding="utf-8")
    return EnvSettingsResponse(
        content=content,
        settings=_parse_env(content),
    )


@router.put("/admin/env", response_model=EnvSettingsResponse)
async def update_env_config(
    body: EnvSettingsUpdate,
    current_user: User = Depends(get_current_admin_user),
):
    """
    更新 .env 配置 — PUT /api/v1/system/admin/env

    只更新请求中指定的键，其他配置保持不变。
    注释和空行会被保留。
    需要管理员权限。

    请求体:
        {"settings": {"DEEPSEEK_API_KEY": "sk-xxx", "ACCESS_TOKEN_EXPIRE_MINUTES": "2880"}}
    """
    try:
        new_content = _update_env_file(body.settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update .env: {str(e)}",
        )

    return EnvSettingsResponse(
        content=new_content,
        settings=_parse_env(new_content),
    )
