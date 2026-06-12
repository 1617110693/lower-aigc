"""
安全工具模块 (Security Utilities)

提供 JWT 令牌的创建/验证和密码哈希功能。

JWT 流程：
  1. 用户登录成功 → create_access_token(user.id) → 返回 JWT 字符串
  2. 前端将 JWT 存入 localStorage，每次请求通过 Authorization: Bearer <token> 携带
  3. 后端 decode_access_token(token) → 提取 user_id → 加载用户对象

密码安全：
  使用 bcrypt 算法对密码进行哈希存储，原密码永不落库。
  bcrypt.gensalt() 每次生成随机盐值，即使相同密码哈希结果也不同。
  bcrypt 内部限制密码最大为 72 字节，超出部分在调用前截断。

扩展指南：
  - 如需修改令牌过期时间，修改 .env 中的 ACCESS_TOKEN_EXPIRE_MINUTES
  - 如需切换签名算法（如 RS256），修改 ALGORITHM 并配置公私钥对
  - 如需调整 bcrypt 哈希轮次（work factor），修改 gensalt(rounds=12) 中的数字
    （轮次越高越安全，但验证越慢。12 是当前推荐值，约 0.3s/次）
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# JWT 签名算法: HMAC-SHA256 (对称密钥，适合单服务部署)
ALGORITHM = "HS256"

# bcrypt 哈希轮次（work factor），12 = 2^12 轮迭代
# 在此配置下，单次哈希约耗时 0.25-0.3 秒，兼顾安全性和用户体验
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """
    对明文密码进行 bcrypt 哈希

    bcrypt 内置随机盐值，每次调用生成的哈希值都不同，
    即使两个用户使用相同的密码，哈希结果也不一样。

    bcrypt 限制密码最大 72 字节 — 对于英语 ASCII 密码就是 72 个字符。
    如果传入更长的密码，这里自动截断到前 72 字节（按 UTF-8 编码计）。

    参数:
        password: 用户注册时的明文密码
    返回:
        bcrypt 哈希字符串 (例: $2b$12$...)
    """
    # bcrypt 密码上限 72 字节，超长密码截断处理
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    校验明文密码与存储的哈希值是否匹配

    参数:
        plain_password: 登录时用户输入的明文密码
        hashed_password: 数据库中存储的 bcrypt 哈希值
    返回:
        True 表示密码正确，False 表示不匹配
    """
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(subject: int | str) -> str:
    """
    创建 JWT 访问令牌

    令牌中包含:
      - sub: 用户 ID 或标识（subject，JWT 标准字段）
      - exp: 过期时间（UTC）

    参数:
        subject: 令牌主体（通常为 user.id）
    返回:
        编码后的 JWT 字符串，格式: header.payload.signature
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    解码并验证 JWT 访问令牌

    验证步骤:
      1. 检查签名是否正确（防篡改）
      2. 检查令牌是否过期
      3. 返回解码后的 payload

    参数:
        token: 前端传来的 JWT 字符串
    返回:
        解码后的 payload 字典，包含 sub 和 exp 字段
    异常:
        JWTError: 签名无效或令牌已过期
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
