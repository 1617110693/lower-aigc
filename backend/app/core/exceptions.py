"""
自定义异常类 (Custom Exceptions)

定义了应用层的异常体系，与 FastAPI 的异常处理器配合使用。
所有业务异常继承自 AppException，在 main.py 中通过统一处理器
转换为 JSON 响应。

异常层次:
  AppException (基类, 默认 400)
  ├── NotFoundError (404)  — 资源不存在
  ├── ForbiddenError (403) — 无权限访问
  └── ConflictError (409)  — 资源冲突（如重复注册）

用法:
    raise NotFoundError("文档未找到")
    # → 前端收到 {"detail": "文档未找到"} 状态码 404

扩展指南:
  如需新增异常类型，只需继承 AppException 并设置合适的 status_code。
  例如: BadRequestError(400), TooManyRequestsError(429) 等。
"""


class AppException(Exception):
    """
    应用层基础异常

    包含 status_code 和 message 两个属性，
    在 main.py 中由统一异常处理器捕获并转换为 HTTP 响应。

    参数:
        message: 错误描述（会显示给前端用户）
        status_code: HTTP 状态码，默认 400
    """

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    """
    资源未找到异常 (404)

    使用场景:
      - 文档 ID 不存在
      - 用户 ID 不存在
      - 验证 token 无效或已过期
    """

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ForbiddenError(AppException):
    """
    访问禁止异常 (403)

    使用场景:
      - 登录密码错误
      - 邮箱未验证试图登录
      - 尝试访问其他用户的文档
    """

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, status_code=403)


class ConflictError(AppException):
    """
    资源冲突异常 (409)

    使用场景:
      - 邮箱已注册
      - 重复创建同名资源
    """

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)
