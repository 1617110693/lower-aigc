"""
通用 Pydantic 模型 (Common Schemas)

各模块公用的请求/响应数据结构。

扩展指南:
  添加新的通用模型时放在此文件中，各路由模块可直接引用。
"""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """
    通用消息响应

    用于返回简单的操作反馈，如注册成功、删除成功等。
    格式: {"message": "..."}
    """
    message: str


class PaginatedResponse(BaseModel):
    """
    分页响应包装器

    用于列表接口的标准化分页响应。
    字段: items(当前页数据), total(总记录数), page(当前页码), size(每页大小)
    """
    items: list
    total: int
    page: int
    size: int
