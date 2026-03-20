"""
Unit Tests for Provider Factory

Tests for the factory pattern implementation.
"""

import pytest

from src.api.base import LLMProvider
from src.api.factory import ProviderFactory


class TestProviderFactory:
    """Tests for ProviderFactory."""

    def test_list_providers(self):
        """Test listing registered providers."""
        providers = ProviderFactory.list_providers()
        assert "llm" in providers
        assert "image" in providers
        assert "tts" in providers

    def test_create_unknown_llm_provider(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            ProviderFactory.create_llm("nonexistent_provider")

    def test_create_unknown_image_provider(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown image provider"):
            ProviderFactory.create_image("nonexistent_provider")

    def test_create_unknown_tts_provider(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown TTS provider"):
            ProviderFactory.create_tts("nonexistent_provider")

    def test_register_custom_provider(self):
        """Test registering a custom provider."""

        class CustomLLM(LLMProvider):
            async def generate_text(self, prompt: str, **kwargs):
                return "custom response"

            async def analyze_content(self, text: str, **kwargs):
                return {}

        # Register
        ProviderFactory.register_llm("custom", CustomLLM)

        # Create
        provider = ProviderFactory.create_llm("custom")
        assert isinstance(provider, CustomLLM)

        # Cleanup
        del ProviderFactory._llm_registry["custom"]
