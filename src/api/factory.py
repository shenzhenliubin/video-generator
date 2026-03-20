"""
Provider Factory - Factory Pattern Implementation

This module provides factory methods for creating provider instances.
Providers are registered by type and instantiated with configuration.

Design Pattern: Factory Pattern + Registry
- Providers register themselves on import
- Factory creates instances by type identifier
- Configuration is passed through from settings

Usage:
    llm = ProviderFactory.create_llm("openai", api_key="...")
    image = ProviderFactory.create_image("stability", ...)
    tts = ProviderFactory.create_tts("elevenlabs", ...)
"""

from typing import Any, Type

from src.api.base import ImageProvider, LLMProvider, TTSProvider


class ProviderFactory:
    """
    Factory for creating provider instances.

    Providers are registered in class-level registries.
    Use register_provider() to add new implementations.
    """

    # LLM Providers
    _llm_registry: dict[str, Type[LLMProvider]] = {}

    # Image Providers
    _image_registry: dict[str, Type[ImageProvider]] = {}

    # TTS Providers
    _tts_registry: dict[str, Type[TTSProvider]] = {}

    @classmethod
    def register_llm(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """Register an LLM provider implementation."""
        cls._llm_registry[name] = provider_class

    @classmethod
    def register_image(cls, name: str, provider_class: Type[ImageProvider]) -> None:
        """Register an image provider implementation."""
        cls._image_registry[name] = provider_class

    @classmethod
    def register_tts(cls, name: str, provider_class: Type[TTSProvider]) -> None:
        """Register a TTS provider implementation."""
        cls._tts_registry[name] = provider_class

    @classmethod
    def create_llm(cls, provider: str, **config: Any) -> LLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider: Provider identifier (e.g., "openai", "anthropic")
            **config: Provider configuration (api_key, model, etc.)

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider is not registered
        """
        provider_class = cls._llm_registry.get(provider)
        if provider_class is None:
            available = ", ".join(cls._llm_registry.keys())
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                f"Available: {available}"
            )
        return provider_class(**config)

    @classmethod
    def create_image(cls, provider: str, **config: Any) -> ImageProvider:
        """
        Create an image provider instance.

        Args:
            provider: Provider identifier (e.g., "openai", "stability")
            **config: Provider configuration

        Returns:
            ImageProvider instance

        Raises:
            ValueError: If provider is not registered
        """
        provider_class = cls._image_registry.get(provider)
        if provider_class is None:
            available = ", ".join(cls._image_registry.keys())
            raise ValueError(
                f"Unknown image provider: {provider}. "
                f"Available: {available}"
            )
        return provider_class(**config)

    @classmethod
    def create_tts(cls, provider: str, **config: Any) -> TTSProvider:
        """
        Create a TTS provider instance.

        Args:
            provider: Provider identifier (e.g., "elevenlabs", "local")
            **config: Provider configuration

        Returns:
            TTSProvider instance

        Raises:
            ValueError: If provider is not registered
        """
        provider_class = cls._tts_registry.get(provider)
        if provider_class is None:
            available = ", ".join(cls._tts_registry.keys())
            raise ValueError(
                f"Unknown TTS provider: {provider}. "
                f"Available: {available}"
            )
        return provider_class(**config)

    @classmethod
    def list_providers(cls) -> dict[str, list[str]]:
        """
        List all registered providers.

        Returns:
            Dictionary with provider types and their registered names
        """
        return {
            "llm": list(cls._llm_registry.keys()),
            "image": list(cls._image_registry.keys()),
            "tts": list(cls._tts_registry.keys()),
        }


# Auto-register available providers on import
# This will be implemented when concrete classes are created
def _register_builtin_providers() -> None:
    """Register built-in provider implementations."""
    # LLM providers
    try:
        from src.api.llm.openai import OpenAILLM
        ProviderFactory.register_llm("openai", OpenAILLM)
    except ImportError:
        pass

    try:
        from src.api.llm.anthropic import AnthropicLLM
        ProviderFactory.register_llm("anthropic", AnthropicLLM)
    except ImportError:
        pass

    # Image providers
    try:
        from src.api.image.openai import OpenAIImage
        ProviderFactory.register_image("openai", OpenAIImage)
    except ImportError:
        pass

    try:
        from src.api.image.stability import StabilityAI
        ProviderFactory.register_image("stability", StabilityAI)
    except ImportError:
        pass

    # TTS providers
    try:
        from src.api.tts.elevenlabs import ElevenLabsTTS
        ProviderFactory.register_tts("elevenlabs", ElevenLabsTTS)
    except ImportError:
        pass

    try:
        from src.api.tts.local import LocalTTS
        ProviderFactory.register_tts("local", LocalTTS)
    except ImportError:
        pass


# Registration happens on module import
_register_builtin_providers()
