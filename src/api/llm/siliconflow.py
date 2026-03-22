"""
SiliconFlow LLM Provider

SiliconFlow (硅基流动) 是一个国产 AI API 服务商，
提供 100+ 大语言模型，完全兼容 OpenAI 接口格式。

API Documentation: https://docs.siliconflow.cn/cn/userguide/quickstart
Base URL: https://api.siliconflow.cn/v1
"""

from typing import Any

from openai import AsyncOpenAI

from src.api.base import LLMProvider


class SiliconFlowLLM(LLMProvider):
    """
    SiliconFlow LLM provider implementation.

    Uses OpenAI-compatible interface with SiliconFlow's base URL.
    Supports 100+ models including DeepSeek, Qwen, etc.
    """

    DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "Qwen/Qwen2.5-72B-Instruct"

    # Popular models available on SiliconFlow
    POPULAR_MODELS = {
        # DeepSeek series
        "deepseek-r1": "Pro/deepseek-ai/DeepSeek-R1",
        "deepseek-v3": "deepseek-ai/DeepSeek-V3",
        # Qwen series
        "qwen-2.5-72b": "Qwen/Qwen2.5-72B-Instruct",
        "qwen-2.5-7b": "Qwen/Qwen2.5-7B-Instruct",
        # Other models
        "glm-4-9b": "THUDM/glm-4-9b-chat",
        "internlm": "internlm/internlm2_5-20b-chat",
    }

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize SiliconFlow LLM provider.

        Args:
            api_key: SiliconFlow API key from https://cloud.siliconflow.cn
            base_url: API base URL (default: https://api.siliconflow.cn/v1)
            model: Model identifier (default: Qwen/Qwen2.5-72B-Instruct)
            **kwargs: Additional OpenAI client parameters
        """
        self._api_key = api_key
        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._model = model or self.DEFAULT_MODEL

        # Initialize AsyncOpenAI client with SiliconFlow endpoint
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            **kwargs,
        )

    @property
    def model(self) -> str:
        """Get the current model identifier."""
        return self._model

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 - 2.0)
            **kwargs: Additional parameters (top_p, stream, etc.)

        Returns:
            Generated text string
        """
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        return response.choices[0].message.content or ""

    async def analyze_content(self, text: str, **kwargs: Any) -> dict[str, Any]:
        """
        Analyze content and extract structured information.

        Args:
            text: Content to analyze
            **kwargs: Provider-specific parameters

        Returns:
            Dictionary with analysis results including:
            - main_points: List of key points extracted
            - summary: Content summary
            - topics: List of topics
            - sentiment: Sentiment analysis (optional)
        """
        # Build analysis prompt
        analysis_prompt = f"""Analyze the following content and provide a structured response in JSON format:

Content:
{text}

Please extract:
1. main_points: 3-5 key points from the content
2. summary: a concise summary (2-3 sentences)
3. topics: relevant topics/tags
4. sentiment: overall sentiment (positive/neutral/negative)

Respond with valid JSON only."""

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": analysis_prompt}],
            response_format={"type": "json_object"},
            temperature=kwargs.get("temperature", 0.3),
            **{k: v for k, v in kwargs.items() if k != "temperature"},
        )

        import json

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            # Fallback if model doesn't return valid JSON
            return {
                "main_points": [],
                "summary": response.choices[0].message.content or "",
                "topics": [],
                "sentiment": "neutral",
            }

    @classmethod
    def get_available_models(cls) -> dict[str, str]:
        """
        Get mapping of model aliases to full model identifiers.

        Returns:
            Dictionary mapping short names to full model paths
        """
        return cls.POPULAR_MODELS.copy()

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"SiliconFlowLLM(model={self._model!r}, base_url={self._base_url!r})"
