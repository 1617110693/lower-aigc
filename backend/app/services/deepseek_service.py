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


def get_prompts() -> list[PromptInfo]:
    """
    获取可用的降重策略列表（不含完整提示词内容）

    此函数供 /api/v1/documents/prompts 端点调用，
    向前端返回策略的 id、名称和描述，供用户选择。
    完整提示词内容在降重时才通过 get_prompt_content() 获取。
    """
    return [
        PromptInfo(id=p["id"], name=p["name"], description=p["description"])
        for p in PROMPTS
    ]


def get_prompt_content(prompt_id: str) -> str | None:
    """
    根据策略 ID 获取完整的 system message 内容

    参数:
        prompt_id: 策略标识符，如 "academic-paraphrase"
    返回:
        完整的 system message 文本，找不到则返回 None
    """
    for p in PROMPTS:
        if p["id"] == prompt_id:
            return p["system_content"]
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
      - model: deepseek-chat (标准对话模型)
      - temperature: 0.7 (中等的创造性，兼顾多样化和稳定性)
      - max_tokens: 4096 (单次改写最多返回的 token 数)
    """

    def __init__(self):
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.api_key = settings.DEEPSEEK_API_KEY
        self.max_retries = 3          # 最大重试次数
        self.timeout = 120.0          # 超时时间（秒），长文本可能需要较长时间

    async def reduce_text(self, text: str, system_prompt: str) -> str:
        """
        调用 DeepSeek API 改写文本

        参数:
            text: 待改写的原始文本（单段落或全文拼接）
            system_prompt: 系统提示词（定义改写风格和约束）
        返回:
            API 返回的改写后文本
        异常:
            ValueError: API 密钥未配置
            RuntimeError: 重试耗尽后仍然失败
        """
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
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
                    return data["choices"][0]["message"]["content"]

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
