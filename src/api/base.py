"""
Provider Abstraction Layer - Abstract Base Classes

This module defines the interfaces for all external service providers.
All providers must implement these interfaces to ensure compatibility
with the pipeline orchestration.

Design Pattern: Strategy Pattern
- Each provider type has an abstract base class
- Concrete implementations are interchangeable
- Factory pattern handles instantiation
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Abstract base class for Large Language Model providers.

    Implementations: OpenAI, Anthropic, etc.
    """

    @abstractmethod
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
            temperature: Sampling temperature (0.0 - 1.0)
            **kwargs: Provider-specific parameters

        Returns:
            Generated text string
        """
        pass

    @abstractmethod
    async def analyze_content(self, text: str, **kwargs: Any) -> dict[str, Any]:
        """
        Analyze content and extract structured information.

        Args:
            text: Content to analyze
            **kwargs: Provider-specific parameters

        Returns:
            Dictionary with analysis results
        """
        pass


class ImageProvider(ABC):
    """
    Abstract base class for Image Generation providers.

    Implementations: DALL-E, Stability AI, etc.
    """

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        style: str | None = None,
        aspect_ratio: str = "16:9",
        **kwargs: Any,
    ) -> bytes:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image
            style: Optional style modifier
            aspect_ratio: Image aspect ratio (e.g., "16:9", "1:1")
            **kwargs: Provider-specific parameters

        Returns:
            Image data as bytes
        """
        pass

    @abstractmethod
    def get_supported_styles(self) -> list[str]:
        """
        Get list of supported style names.

        Returns:
            List of style identifiers
        """
        pass


class TTSProvider(ABC):
    """
    Abstract base class for Text-to-Speech providers.

    Implementations: ElevenLabs, Local TTS, etc.
    """

    @abstractmethod
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
            voice_id: Voice identifier (provider-specific)
            speed: Speech speed multiplier
            **kwargs: Provider-specific parameters

        Returns:
            Tuple of (audio_data, format_mime_type)
        """
        pass

    @abstractmethod
    def get_supported_voices(self) -> list[dict[str, Any]]:
        """
        Get list of available voices.

        Returns:
            List of voice dictionaries with id, name, language, etc.
        """
        pass
