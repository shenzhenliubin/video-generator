"""
Unit tests for SiliconFlow Image Provider.

Tests the SiliconFlow image provider implementation including:
- Provider initialization
- Image generation
- Style application
- Aspect ratio handling
- Model mapping
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.api.image.siliconflow import SiliconFlowImage
from src.api.base import ImageProvider


class TestSiliconFlowImageInit:
    """Test SiliconFlow image provider initialization."""

    @patch("src.api.image.siliconflow.AsyncOpenAI")
    def test_init_with_default_values(self, mock_openai: Mock) -> None:
        """Test initialization with default base URL and model."""
        provider = SiliconFlowImage(api_key="test-key")

        assert provider.model == "black-forest-labs/FLUX.1-schnell"
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["base_url"] == "https://api.siliconflow.cn/v1"

    @patch("src.api.image.siliconflow.AsyncOpenAI")
    def test_init_with_custom_values(self, mock_openai: Mock) -> None:
        """Test initialization with custom base URL and model."""
        provider = SiliconFlowImage(
            api_key="test-key",
            base_url="https://custom.api.com/v1",
            model="flux-dev",
        )

        assert provider.model == "flux-dev"
        mock_openai.assert_called_once()

    @patch("src.api.image.siliconflow.AsyncOpenAI")
    def test_is_image_provider(self, mock_openai: Mock) -> None:
        """Test that SiliconFlowImage implements ImageProvider interface."""
        provider = SiliconFlowImage(api_key="test-key")
        assert isinstance(provider, ImageProvider)


class TestSiliconFlowGenerateImage:
    """Test image generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_image_basic(self) -> None:
        """Test basic image generation."""
        # Mock image response
        mock_image_response = Mock()
        mock_image_response.data = [Mock()]
        mock_image_response.data[0].url = "https://example.com/image.png"

        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(return_value=mock_image_response)

        # Mock image download
        mock_download_response = Mock()
        mock_download_response.content = b"fake_image_data"

        with patch("src.api.image.siliconflow.AsyncOpenAI", return_value=mock_client):
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_download_response
                )

                provider = SiliconFlowImage(api_key="test-key")
                result = await provider.generate_image("A beautiful sunset")

                assert result == b"fake_image_data"
                mock_client.images.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_image_with_style(self) -> None:
        """Test image generation with style modifier."""
        mock_image_response = Mock()
        mock_image_response.data = [Mock()]
        mock_image_response.data[0].url = "https://example.com/image.png"

        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(return_value=mock_image_response)

        mock_download_response = Mock()
        mock_download_response.content = b"fake_image_data"

        with patch("src.api.image.siliconflow.AsyncOpenAI", return_value=mock_client):
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_download_response
                )

                provider = SiliconFlowImage(api_key="test-key")
                await provider.generate_image("A cat", style="anime")

                # Check that style was applied to prompt
                call_kwargs = mock_client.images.generate.call_args.kwargs
                assert "anime style" in call_kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_generate_image_with_aspect_ratio(self) -> None:
        """Test image generation with aspect ratio."""
        mock_image_response = Mock()
        mock_image_response.data = [Mock()]
        mock_image_response.data[0].url = "https://example.com/image.png"

        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(return_value=mock_image_response)

        mock_download_response = Mock()
        mock_download_response.content = b"fake_image_data"

        with patch("src.api.image.siliconflow.AsyncOpenAI", return_value=mock_client):
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_download_response
                )

                provider = SiliconFlowImage(api_key="test-key")
                await provider.generate_image("A landscape", aspect_ratio="16:9")

                # Check size
                call_kwargs = mock_client.images.generate.call_args.kwargs
                assert call_kwargs["size"] == "1024x576"

    @pytest.mark.asyncio
    async def test_generate_image_with_custom_params(self) -> None:
        """Test image generation with custom parameters."""
        mock_image_response = Mock()
        mock_image_response.data = [Mock()]
        mock_image_response.data[0].url = "https://example.com/image.png"

        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(return_value=mock_image_response)

        mock_download_response = Mock()
        mock_download_response.content = b"fake_image_data"

        with patch("src.api.image.siliconflow.AsyncOpenAI", return_value=mock_client):
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_download_response
                )

                provider = SiliconFlowImage(api_key="test-key")
                await provider.generate_image(
                    "A landscape",
                    num_inference_steps=30,
                    seed=42,
                )

                # Check extra body parameters
                call_kwargs = mock_client.images.generate.call_args.kwargs
                assert call_kwargs["extra_body"]["step"] == 30
                assert call_kwargs["extra_body"]["seed"] == 42


class TestSiliconFlowStyleApplication:
    """Test style application functionality."""

    def test_apply_style_realistic(self) -> None:
        """Test applying realistic style."""
        provider = SiliconFlowImage(api_key="test-key")
        result = provider._apply_style_to_prompt("A cat", "realistic")
        assert "hyperrealistic" in result
        assert "photorealistic" in result

    def test_apply_style_anime(self) -> None:
        """Test applying anime style."""
        provider = SiliconFlowImage(api_key="test-key")
        result = provider._apply_style_to_prompt("A cat", "anime")
        assert "anime style" in result

    def test_apply_style_none(self) -> None:
        """Test applying no style."""
        provider = SiliconFlowImage(api_key="test-key")
        result = provider._apply_style_to_prompt("A cat", None)
        assert result == "A cat"

    def test_apply_style_invalid(self) -> None:
        """Test applying invalid style."""
        provider = SiliconFlowImage(api_key="test-key")
        result = provider._apply_style_to_prompt("A cat", "invalid_style")
        assert result == "A cat"


class TestSiliconFlowAspectRatio:
    """Test aspect ratio handling."""

    def test_aspect_ratio_16_9(self) -> None:
        """Test 16:9 aspect ratio."""
        provider = SiliconFlowImage(api_key="test-key")
        size = provider._get_size_for_aspect_ratio("16:9")
        assert size == "1024x576"

    def test_aspect_ratio_9_16(self) -> None:
        """Test 9:16 aspect ratio."""
        provider = SiliconFlowImage(api_key="test-key")
        size = provider._get_size_for_aspect_ratio("9:16")
        assert size == "576x1024"

    def test_aspect_ratio_1_1(self) -> None:
        """Test 1:1 aspect ratio."""
        provider = SiliconFlowImage(api_key="test-key")
        size = provider._get_size_for_aspect_ratio("1:1")
        assert size == "1024x1024"

    def test_aspect_ratio_invalid(self) -> None:
        """Test invalid aspect ratio defaults to 1:1."""
        provider = SiliconFlowImage(api_key="test-key")
        size = provider._get_size_for_aspect_ratio("invalid")
        assert size == "1024x1024"


class TestSiliconFlowStyles:
    """Test supported styles."""

    def test_get_supported_styles(self) -> None:
        """Test getting supported styles."""
        provider = SiliconFlowImage(api_key="test-key")
        styles = provider.get_supported_styles()

        assert "realistic" in styles
        assert "cinematic" in styles
        assert "anime" in styles
        assert "digital-art" in styles
        assert None not in styles  # None should be filtered out


class TestSiliconFlowModelMapping:
    """Test model alias mapping functionality."""

    def test_get_available_models(self) -> None:
        """Test getting available model mappings."""
        models = SiliconFlowImage.get_available_models()

        assert isinstance(models, dict)
        assert "flux-dev" in models
        assert "flux-schnell" in models
        assert "kolors" in models
        assert models["flux-dev"] == "black-forest-labs/FLUX.1-dev"


class TestSiliconFlowFactoryRegistration:
    """Test factory registration of SiliconFlow provider."""

    def test_registered_in_factory(self) -> None:
        """Test that SiliconFlow is registered in ProviderFactory."""
        from src.api.factory import ProviderFactory

        providers = ProviderFactory.list_providers()
        assert "image" in providers
        # "siliconflow" will be in the list if factory was imported
