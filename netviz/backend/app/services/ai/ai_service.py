"""
NetViz AI 服务模块
支持 OpenAI、Anthropic、Ollama 多个提供商
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

import httpx

from app.core.config import settings
from app.core.provider_urls import normalize_ai_base_url

logger = logging.getLogger(__name__)


class AIService(ABC):
    """AI 服务基类"""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """
        发送聊天请求

        Args:
            messages: 消息列表，每条消息包含 role 和 content

        Returns:
            包含 content, prompt_tokens, completion_tokens 的字典
        """
        pass


class OpenAIService(AIService):
    """OpenAI 服务"""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        super().__init__(model)
        self.api_key = api_key
        self.base_url = normalize_ai_base_url(
            "openai",
            base_url,
            allow_unsafe_cloud_urls=settings.allow_unsafe_ai_base_urls,
        )

    async def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                },
            )

            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"OpenAI API error: {error_msg}")
                raise Exception(f"OpenAI API 错误: {response.status_code}")

            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})

            return {
                "content": choice["message"]["content"],
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            }


class AnthropicService(AIService):
    """Anthropic (Claude) 服务"""

    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"

    async def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        # 分离 system 消息
        system_message = ""
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message += msg["content"] + "\n"
            else:
                chat_messages.append(msg)

        async with httpx.AsyncClient(timeout=120.0) as client:
            request_body = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": chat_messages,
            }

            if system_message:
                request_body["system"] = system_message.strip()

            response = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json=request_body,
            )

            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"Anthropic API error: {error_msg}")
                raise Exception(f"Anthropic API 错误: {response.status_code}")

            data = response.json()
            usage = data.get("usage", {})

            return {
                "content": data["content"][0]["text"],
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
            }


class DeepSeekService(AIService):
    """DeepSeek 服务 (OpenAI 兼容)"""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        super().__init__(model)
        self.api_key = api_key
        self.base_url = normalize_ai_base_url(
            "deepseek",
            base_url,
            allow_unsafe_cloud_urls=settings.allow_unsafe_ai_base_urls,
        )

    async def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                },
            )

            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"DeepSeek API error: {error_msg}")
                raise Exception(f"DeepSeek API 错误: {response.status_code}")

            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})

            return {
                "content": choice["message"]["content"],
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            }


class OllamaService(AIService):
    """Ollama 本地服务"""

    def __init__(self, base_url: str, model: str):
        super().__init__(model)
        self.base_url = normalize_ai_base_url("ollama", base_url)

    async def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                    },
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Ollama API error: {error_msg}")
                    raise Exception(f"Ollama API 错误: {response.status_code}")

                data = response.json()

                return {
                    "content": data["message"]["content"],
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                }

            except httpx.ConnectError:
                raise Exception("无法连接到 Ollama 服务，请确保 Ollama 正在运行")


def _setting_value(
    overrides: Mapping[str, str | None] | None,
    key: str,
    fallback: str | None,
) -> str | None:
    if overrides is None:
        return fallback

    value = overrides.get(key)
    return fallback if value in (None, "") else value


def get_ai_service(
    provider: str,
    overrides: Mapping[str, str | None] | None = None,
) -> AIService:
    """
    获取 AI 服务实例

    Args:
        provider: 提供商名称 (openai, anthropic, ollama)

    Returns:
        AIService 实例

    Raises:
        ValueError: 如果提供商无效或未配置
    """
    if provider == "openai":
        api_key = _setting_value(overrides, "openai_api_key", settings.openai_api_key)
        if not api_key:
            raise ValueError("未配置 OpenAI API Key")
        return OpenAIService(
            api_key=api_key,
            model=_setting_value(overrides, "openai_model", settings.openai_model)
            or settings.openai_model,
            base_url=_setting_value(overrides, "openai_base_url", settings.openai_base_url),
        )

    elif provider == "anthropic":
        api_key = _setting_value(
            overrides,
            "anthropic_api_key",
            settings.anthropic_api_key,
        )
        if not api_key:
            raise ValueError("未配置 Anthropic API Key")
        return AnthropicService(
            api_key=api_key,
            model=_setting_value(overrides, "anthropic_model", settings.anthropic_model)
            or settings.anthropic_model,
        )

    elif provider == "ollama":
        return OllamaService(
            base_url=_setting_value(overrides, "ollama_base_url", settings.ollama_base_url)
            or settings.ollama_base_url,
            model=_setting_value(overrides, "ollama_model", settings.ollama_model)
            or settings.ollama_model,
        )

    elif provider == "deepseek":
        api_key = _setting_value(overrides, "deepseek_api_key", settings.deepseek_api_key)
        if not api_key:
            raise ValueError("未配置 DeepSeek API Key")
        return DeepSeekService(
            api_key=api_key,
            model=_setting_value(overrides, "deepseek_model", settings.deepseek_model)
            or settings.deepseek_model,
            base_url=_setting_value(overrides, "deepseek_base_url", settings.deepseek_base_url)
            or settings.deepseek_base_url,
        )

    else:
        raise ValueError(f"不支持的 AI 提供商: {provider}")
