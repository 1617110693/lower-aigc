"""DeepSeek API integration for AIGC reduction."""

import asyncio
import logging
from typing import AsyncGenerator

import httpx

from app.config import settings
from app.schemas.document import PromptInfo

logger = logging.getLogger(__name__)

# ─── Pre-configured system prompts ───────────────────────────────────────────

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
    """Return available system prompts (without the full system content)."""
    return [
        PromptInfo(id=p["id"], name=p["name"], description=p["description"])
        for p in PROMPTS
    ]


def get_prompt_content(prompt_id: str) -> str | None:
    """Get the full system content for a given prompt ID."""
    for p in PROMPTS:
        if p["id"] == prompt_id:
            return p["system_content"]
    return None


# ─── DeepSeek API client ────────────────────────────────────────────────────


class DeepSeekClient:
    """Async client for the DeepSeek chat completions API."""

    def __init__(self):
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.api_key = settings.DEEPSEEK_API_KEY
        self.max_retries = 3
        self.timeout = 120.0  # seconds

    async def reduce_text(self, text: str, system_prompt: str) -> str:
        """Send text to DeepSeek API and return the rewritten result."""
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
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After", "5")
                    wait = int(retry_after) if retry_after.isdigit() else 5
                    logger.warning(f"Rate limited. Retrying after {wait}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait)
                elif e.response.status_code >= 500:
                    wait = 2 ** attempt
                    logger.warning(f"Server error. Retrying in {wait}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait)
                else:
                    raise
            except httpx.TimeoutException as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(f"Timeout. Retrying in {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)

        raise RuntimeError(f"DeepSeek API call failed after {self.max_retries} retries: {last_error}")


deepseek_client = DeepSeekClient()
