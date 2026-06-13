"""
DeepSeek API 集成模块 (DeepSeek Service)

核心模块之一，负责:
  1. 管理内置的降 AIGC 系统提示词（3 套策略）
  2. 封装 DeepSeek Chat API 的异步调用
  3. 实现指数退避重试机制，处理限流和服务器错误

降重策略说明:
  - academic-paraphrase:  学术改写 — 变换句式结构，使用学科词汇，保持学术严谨性
  - style-diversification: 风格多样化 — 长短句交替，添加过渡语，融入领域术语
  - natural-human-voice:   自然人声 — 添加适度不完美，模拟真人写作风格

重试策略:
  - 429 (Rate Limit): 使用 API 返回的 Retry-After 等待时间
  - 5xx (Server Error): 指数退避 (2^attempt 秒)
  - Timeout: 同上指数退避
  - 最多重试 3 次，全部失败后抛出 RuntimeError

扩展指南:
  - 添加新的降重策略: 在 PROMPTS 列表中添加新的 dict 即可，
    无需修改其他代码，前端会自动通过 /prompts 接口获取
  - 切换模型: 修改 payload 中的 "model" 字段，
    如 deepseek-chat / deepseek-reasoner
  - 对接其他 LLM: 新建类继承相同的接口，在 document_service 中替换
"""

import asyncio
import logging
from typing import AsyncGenerator

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.document import PromptInfo

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 预置系统提示词 (System Prompts)
# 每套提示词包含 id、名称、描述和完整的 system message 内容
# ═══════════════════════════════════════════════════════════════════════════════

PROMPTS: list[dict] = [
    {
        "id": "academic-paraphrase",
        "name": "学术改写",
        "description": "变换句式结构，使用学科词汇，保持学术严谨性",
        "system_content": (
            "你是一位专业的学术编辑。请改写以下学术文本，在保留原意和学术严谨性的前提下降低AI检测率。"
            "使用多样化的句式结构、学科适当的词汇和自然的过渡。避免重复模式、过于均匀的句子长度"
            "以及AI生成文本特有的通用措辞。保持正式的学术语调。"
        ),
    },
    {
        "id": "style-diversification",
        "name": "风格多样化",
        "description": "长短句交替，添加过渡语，融入领域术语",
        "system_content": (
            "你是一位熟练的人类学术作者。请通过变化句子长度（混合简洁有力的短句和较长复杂的句子）、"
            "融入自然的过渡短语、在适当地方使用领域特定术语来改写提供的文本。引入微妙风格变化，"
            "使写作感觉真实人类化——偶尔使用插入语、有节制地使用被动语态、在有助于论证的地方使用修辞问句。"
            "保留所有事实内容和引用。"
        ),
    },
    {
        "id": "natural-human-voice",
        "name": "自然人声",
        "description": "增加适度不完美，模拟真人写作风格（第一人称、模糊限制语、修辞问句）",
        "system_content": (
            "你是一位经验丰富的研究者，正在为发表而写作。请修改以下文本，使其听起来像是深思熟虑的"
            "人类学者所写。添加人类写作特有的微妙不完美：段落结构的轻微变化、偶尔使用第一人称视角"
            "（“我们观察到”、“我们的分析表明”）、有节制地使用模糊限制语言"
            "（“可能表明”、“表明”、“似乎”）。"
            "不要引入事实错误或改变学术含义。保持所有参考文献和数据点不变。"
        ),
    },
]


async def get_prompts(
    db: AsyncSession | None = None,
    user_id: int | None = None,
) -> list[PromptInfo]:
    """
    获取可用的降重策略列表（不含完整提示词内容）

    返回内置策略 + 用户自定义策略的合并列表。
    - 游客（user_id=None）：仅返回内置策略
    - 登录用户：返回内置策略 + 该用户的自定义策略

    自定义策略的 ID 格式为 "custom-{db_id}"，避免与内置策略冲突。
    """
    # 内置策略（已登录用户可查看完整 system_content，游客仅看到名称和描述）
    builtin = [
        PromptInfo(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            system_default=True,
            system_content=p["system_content"] if user_id is not None else None,
        )
        for p in PROMPTS
    ]

    # 用户自定义策略
    if db is not None and user_id is not None:
        from app.models.custom_prompt import CustomPrompt

        result = await db.execute(
            select(CustomPrompt).where(
                CustomPrompt.user_id == user_id,
                CustomPrompt.is_active == True,
            ).order_by(CustomPrompt.created_at.asc())
        )
        customs = result.scalars().all()
        custom_list = [
            PromptInfo(
                id=f"custom-{c.id}",
                name=c.name,
                description=c.description,
                system_default=False,
            )
            for c in customs
        ]
        return builtin + custom_list

    return builtin


async def get_prompt_content(
    prompt_id: str,
    db: AsyncSession | None = None,
) -> str | None:
    """
    根据策略 ID 获取完整的 system message 内容

    查找顺序：
      1. 内置策略（PROMPTS 列表）
      2. 自定义策略（custom_prompts 表，ID 格式 "custom-{id}"）

    参数:
        prompt_id: 策略标识符，如 "academic-paraphrase" 或 "custom-7"
        db: 数据库会话（查找自定义策略时需要）
    返回:
        完整的 system message 文本，找不到则返回 None
    """
    # 先查内置策略
    for p in PROMPTS:
        if p["id"] == prompt_id:
            return p["system_content"]

    # 再查自定义策略（ID 格式："custom-{id}"）
    if prompt_id.startswith("custom-") and db is not None:
        from app.models.custom_prompt import CustomPrompt

        try:
            custom_id = int(prompt_id.split("-", 1)[1])
        except (ValueError, IndexError):
            return None

        result = await db.execute(
            select(CustomPrompt).where(
                CustomPrompt.id == custom_id,
                CustomPrompt.is_active == True,
            )
        )
        custom = result.scalar_one_or_none()
        if custom:
            return custom.system_content

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# DeepSeek API 客户端
# ═══════════════════════════════════════════════════════════════════════════════


class DeepSeekClient:
    """
    DeepSeek Chat API 异步客户端

    封装了 API 调用、重试逻辑和错误处理。

    配置:
      - base_url: API 基础 URL（默认 https://api.deepseek.com/v1）
      - api_key: API 密钥（从 .env 加载）
      - max_retries: 最大重试次数（默认 3 次）
      - timeout: 单次请求超时时间（默认 120 秒）

    API 参数说明:
      - model: deepseek-v4-flash (快速模型，默认) / deepseek-v4-pro (高质量模型，支持思考模式)
      - temperature: 0.7 (中等的创造性，兼顾多样化和稳定性)
      - max_tokens: 4096 (单次改写最多返回的 token 数)

    注意:
      deepseek-chat 与 deepseek-reasoner 将于 2026/07/24 弃用，已迁移至 v4 系列。
    """

    def __init__(self):
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.api_key = settings.DEEPSEEK_API_KEY
        self.max_retries = 3          # 最大重试次数
        self.timeout = 120.0          # 超时时间（秒），长文本可能需要较长时间

    async def reduce_text(
        self,
        text: str,
        system_prompt: str,
        model: str = "deepseek-v4-flash",
        preserve_word_count: bool = False,
    ) -> str:
        """
        调用 DeepSeek API 改写文本

        参数:
            text: 待改写的原始文本（单段落或全文拼接）
            system_prompt: 系统提示词（定义改写风格和约束）
            model: 模型名称，默认 deepseek-v4-flash，可选 deepseek-v4-pro
            preserve_word_count: 是否尽可能保持原文字数不变
        返回:
            API 返回的改写后文本
        异常:
            ValueError: API 密钥未配置
            RuntimeError: 重试耗尽后仍然失败
        """
        # 如果开启了字数保持，将约束追加到 system prompt
        if preserve_word_count:
            system_prompt = (
                f"{system_prompt}\n\n"
                "【重要约束】改写后的文本字数必须与原文尽可能接近，误差控制在±10%以内。"
                "不得大幅扩充或缩减内容，保持原文的信息密度和篇幅。"
            )
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.7,       # 0.7 = 中等创造性，兼顾多样化和原文忠实度
            "max_tokens": 4096,       # 单次最大输出 token 数
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                # 每次重试创建新的 AsyncClient（避免连接复用导致的潜在问题）
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()

                    # 诊断日志：记录 API 响应结构（仅首次成功时）
                    if attempt == 0:
                        choice = data.get("choices", [{}])[0] if "choices" in data else {}
                        msg = choice.get("message", {}) if "message" in choice else {}
                        content_preview = (
                            str(msg.get("content", ""))[:200]
                            if msg.get("content")
                            else "<EMPTY>"
                        )
                        logger.info(
                            "DeepSeek API response: model=%s, "
                            "choices_count=%s, "
                            "content_length=%s, "
                            "finish_reason=%s, "
                            "content_preview=%s",
                            model,
                            len(data.get("choices", [])),
                            len(msg.get("content") or ""),
                            choice.get("finish_reason", "N/A"),
                            content_preview,
                        )
                        # 检查是否为 reasoning 模型响应（content 在 reasoning_content 中）
                        if "reasoning_content" in msg:
                            logger.info(
                                "DeepSeek reasoning_content present, length=%s",
                                len(msg.get("reasoning_content", "")),
                            )

                    # v4 系列模型兼容：如果 content 为空但存在 reasoning_content，
                    # 使用 reasoning_content 作为最终输出
                    content = data["choices"][0]["message"].get("content", "")
                    if not content and "reasoning_content" in data["choices"][0]["message"]:
                        logger.info("Using reasoning_content as fallback for empty content")
                        content = data["choices"][0]["message"].get("reasoning_content", "")

                    return content

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # 429 Too Many Requests — 按 API 返回的 Retry-After 等待
                    retry_after = e.response.headers.get("Retry-After", "5")
                    wait = int(retry_after) if retry_after.isdigit() else 5
                    logger.warning(
                        f"Rate limited. Retrying after {wait}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait)
                elif e.response.status_code >= 500:
                    # 5xx 服务器错误 — 指数退避: 1s, 2s, 4s...
                    wait = 2 ** attempt
                    logger.warning(
                        f"Server error. Retrying in {wait}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait)
                else:
                    # 4xx 客户端错误（非 429）— 不重试，直接抛出
                    raise

            except httpx.TimeoutException as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(
                    f"Timeout. Retrying in {wait}s (attempt {attempt + 1})"
                )
                await asyncio.sleep(wait)

        # 全部重试耗尽
        raise RuntimeError(
            f"DeepSeek API call failed after {self.max_retries} retries: {last_error}"
        )


# 全局 DeepSeek 客户端实例 — 在应用的任何地方导入此实例即可使用
deepseek_client = DeepSeekClient()
