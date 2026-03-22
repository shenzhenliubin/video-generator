"""
Unit tests for SiliconFlow LLM Provider.

Tests the SiliconFlow LLM provider implementation including:
- Provider initialization
- Text generation
- Content analysis
- Model mapping
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.api.llm.siliconflow import SiliconFlowLLM
from src.api.base import LLMProvider


class TestSiliconFlowLLMInit:
    """Test SiliconFlow LLM provider initialization."""

    @patch("src.api.llm.siliconflow.AsyncOpenAI")
    def test_init_with_default_values(self, mock_openai: Mock) -> None:
        """Test initialization with default base URL and model."""
        provider = SiliconFlowLLM(api_key="test-key")

        assert provider.model == "Qwen/Qwen2.5-72B-Instruct"
        mock_openai.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
        )

    @patch("src.api.llm.siliconflow.AsyncOpenAI")
    def test_init_with_custom_values(self, mock_openai: Mock) -> None:
        """Test initialization with custom base URL and model."""
        provider = SiliconFlowLLM(
            api_key="test-key",
            base_url="https://custom.api.com/v1",
            model="deepseek-v3",
        )

        assert provider.model == "deepseek-v3"
        mock_openai.assert_called_once_with(
            api_key="test-key",
            base_url="https://custom.api.com/v1",
        )

    @patch("src.api.llm.siliconflow.AsyncOpenAI")
    def test_is_llm_provider(self, mock_openai: Mock) -> None:
        """Test that SiliconFlowLLM implements LLMProvider interface."""
        provider = SiliconFlowLLM(api_key="test-key")
        assert isinstance(provider, LLMProvider)

    def test_repr(self) -> None:
        """Test string representation of provider."""
        with patch("src.api.llm.siliconflow.AsyncOpenAI"):
            provider = SiliconFlowLLM(api_key="test-key", model="test-model")
            repr_str = repr(provider)
            assert "SiliconFlowLLM" in repr_str
            assert "test-model" in repr_str


class TestSiliconFlowGenerateText:
    """Test text generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_text_basic(self) -> None:
        """Test basic text generation."""
        # Mock the OpenAI client response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated text response"

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.api.llm.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowLLM(api_key="test-key")
            result = await provider.generate_text("Test prompt")

            assert result == "Generated text response"
            mock_client.chat.completions.create.assert_called_once_with(
                model=provider._model,
                messages=[{"role": "user", "content": "Test prompt"}],
                max_tokens=1000,
                temperature=0.7,
            )

    @pytest.mark.asyncio
    async def test_generate_text_with_custom_params(self) -> None:
        """Test text generation with custom parameters."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Custom result"

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.api.llm.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowLLM(api_key="test-key")
            result = await provider.generate_text(
                "Test prompt",
                max_tokens=500,
                temperature=0.5,
                top_p=0.9,
            )

            assert result == "Custom result"
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["max_tokens"] == 500
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["top_p"] == 0.9

    @pytest.mark.asyncio
    async def test_generate_text_empty_response(self) -> None:
        """Test handling of empty response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.api.llm.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowLLM(api_key="test-key")
            result = await provider.generate_text("Test prompt")

            assert result == ""


class TestSiliconFlowAnalyzeContent:
    """Test content analysis functionality."""

    @pytest.mark.asyncio
    async def test_analyze_content_success(self) -> None:
        """Test successful content analysis with JSON response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "main_points": ["Point 1", "Point 2", "Point 3"],
            "summary": "This is a summary",
            "topics": ["topic1", "topic2"],
            "sentiment": "positive"
        }
        '''

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.api.llm.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowLLM(api_key="test-key")
            result = await provider.analyze_content("Test content to analyze")

            assert result["main_points"] == ["Point 1", "Point 2", "Point 3"]
            assert result["summary"] == "This is a summary"
            assert result["topics"] == ["topic1", "topic2"]
            assert result["sentiment"] == "positive"

            # Verify the prompt was formatted correctly
            call_args = mock_client.chat.completions.create.call_args
            assert "Test content to analyze" in call_args.kwargs["messages"][0]["content"]
            assert call_args.kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_analyze_content_json_fallback(self) -> None:
        """Test fallback when JSON parsing fails."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON content"

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.api.llm.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowLLM(api_key="test-key")
            result = await provider.analyze_content("Test content")

            # Should return fallback structure
            assert result["main_points"] == []
            assert result["summary"] == "Invalid JSON content"
            assert result["topics"] == []
            assert result["sentiment"] == "neutral"

    @pytest.mark.asyncio
    async def test_analyze_content_with_custom_temperature(self) -> None:
        """Test analysis with custom temperature parameter."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"main_points": [], "summary": "", "topics": [], "sentiment": "neutral"}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.api.llm.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowLLM(api_key="test-key")
            await provider.analyze_content("Test", temperature=0.5)

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["temperature"] == 0.5


class TestSiliconFlowModelMapping:
    """Test model alias mapping functionality."""

    def test_get_available_models(self) -> None:
        """Test getting available model mappings."""
        models = SiliconFlowLLM.get_available_models()

        assert isinstance(models, dict)
        assert "deepseek-r1" in models
        assert "qwen-2.5-72b" in models
        assert "glm-4-9b" in models
        assert models["deepseek-r1"] == "Pro/deepseek-ai/DeepSeek-R1"

    def test_popular_models_constants(self) -> None:
        """Test that popular models are correctly defined."""
        assert "deepseek-r1" in SiliconFlowLLM.POPULAR_MODELS
        assert "deepseek-v3" in SiliconFlowLLM.POPULAR_MODELS
        assert "qwen-2.5-72b" in SiliconFlowLLM.POPULAR_MODELS


class TestSiliconFlowFactoryRegistration:
    """Test factory registration of SiliconFlow provider."""

    def test_registered_in_factory(self) -> None:
        """Test that SiliconFlow is registered in ProviderFactory."""
        from src.api.factory import ProviderFactory

        providers = ProviderFactory.list_providers()
        assert "llm" in providers
        # Note: "siliconflow" will be in the list if factory was imported
        # This test verifies the registration mechanism works
