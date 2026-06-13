"""
应用全局配置模块 (Application Configuration)

从环境变量和 `.env` 文件中加载所有可配置项。
使用 pydantic-settings 实现类型安全、自动校验的配置管理。

扩展指南：
  如需添加新配置项，只需在本文件的 Settings 类中新增一个字段，
  并在 .env.example 中添加对应的注释说明即可。
  支持的类型: str, int, bool, float, 以及嵌套模型。
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 自动定位 .env 文件: 优先当前工作目录，其次项目根目录
# 支持从 backend/ 子目录或项目根目录启动 uvicorn
_CWD_ENV = Path.cwd() / ".env"
_PROJECT_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"
_ENV_FILE = _CWD_ENV if _CWD_ENV.exists() else _PROJECT_ROOT_ENV


class Settings(BaseSettings):
    """
    应用设置类

    自动从 .env 文件加载环境变量。查找顺序:
      1. 当前工作目录的 .env 文件
      2. 项目根目录 (backend/../) 的 .env 文件

    所有字段名大小写不敏感 (case_sensitive=False)，
    所以 .env 中用 DEEPSEEK_API_KEY 和 deepseek_api_key 都可以。

    用法:
        from app.config import settings
        print(settings.DEEPSEEK_API_KEY)
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),   # 自动定位 .env 文件路径
        env_file_encoding="utf-8", # 使用 UTF-8 编码（支持中文注释）
        case_sensitive=False,      # 环境变量名不区分大小写
    )

    # ── 应用基础配置 ──
    ENVIRONMENT: str = "development"                # 运行环境: development / production
    SECRET_KEY: str = "change-me-to-a-random-secret-key"  # JWT 签名密钥，生产环境务必更换
    APP_NAME: str = "Lower-AIGC"                    # 应用名称（用于邮件标题等）
    APP_URL: str = "http://localhost:5173"          # 前端地址（用于生成邮件中的链接）

    # ── 数据库配置 ──
    # SQLite 数据库路径，格式: sqlite+aiosqlite:///<相对或绝对路径>
    # 默认存储在 backend/data/ 目录下
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/lower_aigc.db"

    # ── DeepSeek API 配置 ──
    DEEPSEEK_API_KEY: str = ""                      # DeepSeek API 密钥（必填，否则降重功能不可用）
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"  # DeepSeek API 基础 URL（不带 /v1）

    # ── 邮件 (SMTP) 配置 ──
    # 不配置 SMTP_PASSWORD 时，开发环境会自动使用控制台模式（打印到日志）
    SMTP_HOST: str = "smtp.example.com"             # SMTP 服务器地址
    SMTP_PORT: int = 587                            # SMTP 端口（587=TLS, 465=SSL）
    SMTP_USER: str = "noreply@example.com"          # SMTP 登录账号
    SMTP_PASSWORD: str = ""                         # SMTP 密码（为空=开发环境使用控制台模式）
    SMTP_FROM: str = "noreply@example.com"          # 发件人地址
    SMTP_USE_TLS: bool = True                       # 是否启用 TLS 加密

    # ── 认证配置 ──
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440         # JWT 令牌有效期（分钟），默认 1440 = 24 小时
    REQUIRE_EMAIL_VERIFICATION: bool = True         # 是否要求邮箱验证后才能登录（开发环境建议设为 false）

    # ── 上传限制 ──
    MAX_UPLOAD_SIZE_MB: int = 16                    # 单文件上传大小上限 (MB)
    MAX_PARAGRAPHS_PER_DOC: int = 500               # 单篇文档最大段落数（超过此数拒绝上传）


# 全局配置实例 — 在应用的任何地方导入此实例即可读取配置
settings = Settings()
