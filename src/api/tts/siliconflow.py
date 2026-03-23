"""
SiliconFlow Text-to-Speech Provider

SiliconFlow (硅基流动) 提供 CosyVoice2-0.5B 文字转语音模型，
支持跨语言合成、情感控制和音色克隆。

支持的模型:
- CosyVoice2-0.5B: 跨语言语音合成，支持中英日韩粤语等

API Documentation: https://docs.siliconflow.cn/cn/userguide/capabilities/text-to-speech
Base URL: https://api.siliconflow.cn/v1
"""

import os
from typing import Any

import httpx
from openai import AsyncOpenAI

from src.api.base import TTSProvider


def _create_httpx_client() -> httpx.AsyncClient:
    """
    Create an httpx client with proxy disabled.

    This avoids SOCKS proxy errors when proxy is configured in environment.
    """
    # Temporarily clear proxy environment variables
    proxy_vars = [
        "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
        "all_proxy", "ALL_PROXY", "socks_proxy", "socks5_proxy"
    ]
    original_env = {}
    for var in proxy_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]

    try:
        # Create client without proxy
        return httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    finally:
        # Restore original environment
        for var, value in original_env.items():
            os.environ[var] = value


class SiliconFlowTTS(TTSProvider):
    """
    SiliconFlow TTS provider implementation.

    Uses OpenAI-compatible interface with SiliconFlow's base URL.
    Supports CosyVoice2-0.5B model with multiple voices and emotions.
    """

    DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "FunAudioLLM/CosyVoice2-0.5B"

    # Supported models
    POPULAR_MODELS = {
        "cosyvoice": "FunAudioLLM/CosyVoice2-0.5B",
    }

    # System preset voices
    # Format: voice_id -> (name, gender, description)
    SYSTEM_VOICES = {
        # Male voices
        "alex": ("Alex", "male", "沉稳男声"),
        "benjamin": ("Benjamin", "male", "低沉男声"),
        "charles": ("Charles", "male", "磁性男声"),
        "david": ("David", "male", "欢快男声"),
        # Female voices
        "anna": ("Anna", "female", "沉稳女声"),
        "bella": ("Bella", "female", "激情女声"),
        "claire": ("Claire", "female", "温柔女声"),
        "diana": ("Diana", "female", "欢快女声"),
    }

    # Supported output formats
    SUPPORTED_FORMATS = ["mp3", "opus", "wav", "pcm"]

    # Format to MIME type mapping
    FORMAT_MIME_TYPES = {
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "wav": "audio/wav",
        "pcm": "audio/pcm",
    }

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        http_client: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize SiliconFlow TTS provider.

        Args:
            api_key: SiliconFlow API key from https://cloud.siliconflow.cn
            base_url: API base URL (default: https://api.siliconflow.cn/v1)
            model: Model identifier (default: FunAudioLLM/CosyVoice2-0.5B)
            http_client: Custom httpx client (optional)
            **kwargs: Additional OpenAI client parameters
        """
        self._api_key = api_key
        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._model = model or self.DEFAULT_MODEL

        # Create httpx client without proxy if not provided
        if http_client is None:
            http_client = _create_httpx_client()

        # Initialize AsyncOpenAI client with SiliconFlow endpoint
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            http_client=http_client,
            **kwargs,
        )

    @property
    def model(self) -> str:
        """Get the current model identifier."""
        return self._model

    def _format_voice_id(self, voice_id: str | None) -> str:
        """
        Format voice ID for API request.

        Args:
            voice_id: Voice identifier (e.g., "claire")

        Returns:
            Formatted voice ID (e.g., "FunAudioLLM/CosyVoice2-0.5B:claire")
        """
        if voice_id is None:
            voice_id = "claire"  # Default to温柔女声

        # Check if already formatted
        if ":" in voice_id:
            return voice_id

        # Format as model:voice_id
        return f"{self._model}:{voice_id}"

    async def synthesize(
        self,
        text: str,
        voice_id: str | None = None,
        speed: float = 1.0,
        **kwargs: Any,
    ) -> tuple[bytes, str]:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            voice_id: Voice identifier (alex, anna, claire, etc.)
            speed: Speech speed multiplier (0.25 - 4.0)
            **kwargs: Provider-specific parameters (format, gain, sample_rate, emotion)

        Returns:
            Tuple of (audio_data, format_mime_type)
        """
        # Get parameters
        response_format = kwargs.get("format", "mp3")
        gain = kwargs.get("gain", 0.0)
        sample_rate = kwargs.get("sample_rate", None)
        emotion = kwargs.get("emotion", None)

        # Validate parameters
        if response_format not in self.SUPPORTED_FORMATS:
            response_format = "mp3"

        if speed < 0.25 or speed > 4.0:
            raise ValueError(f"Speed must be between 0.25 and 4.0, got {speed}")

        # Format voice ID
        formatted_voice_id = self._format_voice_id(voice_id)

        # Apply emotion to text if specified
        if emotion:
            emotion_prompts = {
                "happy": "你能用高兴的情感说吗？<|endofprompt|>",
                "sad": "你能用悲伤的情感说吗？<|endofprompt|>",
                "excited": "你能用兴奋的情感说吗？<|endofprompt|>",
                "angry": "你能用愤怒的情感说吗？<|endofprompt|>",
                "neutral": "",
            }
            emotion_prompt = emotion_prompts.get(emotion, "")
            if emotion_prompt:
                text = f"{emotion_prompt}{text}"

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": self._model,
            "voice": formatted_voice_id,
            "input": text,
            "response_format": response_format,
            "speed": speed,
        }

        # Add optional parameters
        extra_body: dict[str, Any] = {}
        if gain != 0.0:
            extra_body["gain"] = gain
        if sample_rate is not None:
            extra_body["sample_rate"] = sample_rate

        if extra_body:
            request_params["extra_body"] = extra_body

        # Generate speech - use non-streaming API for simplicity
        response = await self._client.audio.speech.create(
            **request_params
        )

        # Get audio data from response
        audio_data = response.content
        if not audio_data:
            raise ValueError("No audio data returned from API")

        # Get MIME type
        mime_type = self.FORMAT_MIME_TYPES.get(response_format, "audio/mpeg")

        return audio_data, mime_type

    def get_supported_voices(self) -> list[dict[str, Any]]:
        """
        Get list of available voices.

        Returns:
            List of voice dictionaries with id, name, gender, description
        """
        voices = []
        for voice_id, (name, gender, description) in self.SYSTEM_VOICES.items():
            voices.append({
                "id": voice_id,
                "name": name,
                "gender": gender,
                "description": description,
                "language": "zh-CN",  # CosyVoice2 supports multiple languages
            })
        return voices

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
        return f"SiliconFlowTTS(model={self._model!r}, base_url={self._base_url!r})"
