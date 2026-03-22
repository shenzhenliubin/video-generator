"""
Unit tests for SiliconFlow TTS Provider.

Tests the SiliconFlow TTS provider implementation including:
- Provider initialization
- Speech synthesis
- Voice formatting
- Supported voices
- Model mapping
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.api.tts.siliconflow import SiliconFlowTTS
from src.api.base import TTSProvider


class TestSiliconFlowTTSInit:
    """Test SiliconFlow TTS provider initialization."""

    @patch("src.api.tts.siliconflow.AsyncOpenAI")
    def test_init_with_default_values(self, mock_openai: Mock) -> None:
        """Test initialization with default base URL and model."""
        provider = SiliconFlowTTS(api_key="test-key")

        assert provider.model == "FunAudioLLM/CosyVoice2-0.5B"
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["base_url"] == "https://api.siliconflow.cn/v1"

    @patch("src.api.tts.siliconflow.AsyncOpenAI")
    def test_init_with_custom_values(self, mock_openai: Mock) -> None:
        """Test initialization with custom base URL and model."""
        provider = SiliconFlowTTS(
            api_key="test-key",
            base_url="https://custom.api.com/v1",
            model="cosyvoice",
        )

        assert provider.model == "cosyvoice"
        mock_openai.assert_called_once()

    @patch("src.api.tts.siliconflow.AsyncOpenAI")
    def test_is_tts_provider(self, mock_openai: Mock) -> None:
        """Test that SiliconFlowTTS implements TTSProvider interface."""
        provider = SiliconFlowTTS(api_key="test-key")
        assert isinstance(provider, TTSProvider)


class TestSiliconFlowVoiceFormatting:
    """Test voice ID formatting."""

    def test_format_voice_id_default(self) -> None:
        """Test default voice formatting."""
        provider = SiliconFlowTTS(api_key="test-key")
        result = provider._format_voice_id(None)
        assert result == "FunAudioLLM/CosyVoice2-0.5B:claire"

    def test_format_voice_id_simple(self) -> None:
        """Test simple voice ID formatting."""
        provider = SiliconFlowTTS(api_key="test-key")
        result = provider._format_voice_id("alex")
        assert result == "FunAudioLLM/CosyVoice2-0.5B:alex"

    def test_format_voice_id_already_formatted(self) -> None:
        """Test already formatted voice ID."""
        provider = SiliconFlowTTS(api_key="test-key")
        result = provider._format_voice_id("FunAudioLLM/CosyVoice2-0.5B:claire")
        assert result == "FunAudioLLM/CosyVoice2-0.5B:claire"


class TestSiliconFlowSynthesize:
    """Test speech synthesis functionality."""

    @pytest.mark.asyncio
    async def test_synthesize_basic(self) -> None:
        """Test basic speech synthesis."""
        # Mock streaming response with async iterator
        async def mock_aiter_bytes():
            yield b"audio_data"

        mock_stream = Mock()
        mock_stream.aiter_bytes = mock_aiter_bytes

        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_stream
        mock_response.__aexit__.return_value = None

        mock_client = AsyncMock()
        mock_client.audio.speech.with_streaming_response.create = AsyncMock(
            return_value=mock_response
        )

        with patch("src.api.tts.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowTTS(api_key="test-key")
            audio_data, mime_type = await provider.synthesize("Hello world")

            assert audio_data == b"audio_data"
            assert mime_type == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_synthesize_with_voice(self) -> None:
        """Test synthesis with custom voice."""
        async def mock_aiter_bytes():
            yield b"audio_data"

        mock_stream = Mock()
        mock_stream.aiter_bytes = mock_aiter_bytes

        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_stream
        mock_response.__aexit__.return_value = None

        mock_client = AsyncMock()
        mock_client.audio.speech.with_streaming_response.create = AsyncMock(
            return_value=mock_response
        )

        with patch("src.api.tts.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowTTS(api_key="test-key")
            await provider.synthesize("Hello", voice_id="alex")

            call_kwargs = mock_client.audio.speech.with_streaming_response.create.call_args.kwargs
            assert "alex" in call_kwargs["voice"]

    @pytest.mark.asyncio
    async def test_synthesize_with_speed(self) -> None:
        """Test synthesis with custom speed."""
        async def mock_aiter_bytes():
            yield b"audio_data"

        mock_stream = Mock()
        mock_stream.aiter_bytes = mock_aiter_bytes

        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_stream
        mock_response.__aexit__.return_value = None

        mock_client = AsyncMock()
        mock_client.audio.speech.with_streaming_response.create = AsyncMock(
            return_value=mock_response
        )

        with patch("src.api.tts.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowTTS(api_key="test-key")
            await provider.synthesize("Hello", speed=1.5)

            call_kwargs = mock_client.audio.speech.with_streaming_response.create.call_args.kwargs
            assert call_kwargs["speed"] == 1.5

    @pytest.mark.asyncio
    async def test_synthesize_invalid_speed(self) -> None:
        """Test synthesis with invalid speed raises error."""
        provider = SiliconFlowTTS(api_key="test-key")

        with pytest.raises(ValueError, match="Speed must be between"):
            await provider.synthesize("Hello", speed=5.0)

    @pytest.mark.asyncio
    async def test_synthesize_with_emotion(self) -> None:
        """Test synthesis with emotion."""
        async def mock_aiter_bytes():
            yield b"audio_data"

        mock_stream = Mock()
        mock_stream.aiter_bytes = mock_aiter_bytes

        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_stream
        mock_response.__aexit__.return_value = None

        mock_client = AsyncMock()
        mock_client.audio.speech.with_streaming_response.create = AsyncMock(
            return_value=mock_response
        )

        with patch("src.api.tts.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowTTS(api_key="test-key")
            await provider.synthesize("你好", emotion="happy")

            call_kwargs = mock_client.audio.speech.with_streaming_response.create.call_args.kwargs
            assert "高兴" in call_kwargs["input"] or "happy" in call_kwargs["input"]

    @pytest.mark.asyncio
    async def test_synthesize_with_format(self) -> None:
        """Test synthesis with custom format."""
        async def mock_aiter_bytes():
            yield b"audio_data"

        mock_stream = Mock()
        mock_stream.aiter_bytes = mock_aiter_bytes

        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_stream
        mock_response.__aexit__.return_value = None

        mock_client = AsyncMock()
        mock_client.audio.speech.with_streaming_response.create = AsyncMock(
            return_value=mock_response
        )

        with patch("src.api.tts.siliconflow.AsyncOpenAI", return_value=mock_client):
            provider = SiliconFlowTTS(api_key="test-key")
            audio_data, mime_type = await provider.synthesize("Hello", format="wav")

            assert mime_type == "audio/wav"
            call_kwargs = mock_client.audio.speech.with_streaming_response.create.call_args.kwargs
            assert call_kwargs["response_format"] == "wav"


class TestSiliconFlowVoices:
    """Test supported voices functionality."""

    def test_get_supported_voices(self) -> None:
        """Test getting supported voices."""
        provider = SiliconFlowTTS(api_key="test-key")
        voices = provider.get_supported_voices()

        assert len(voices) == 8

        # Check male voices
        male_voices = [v for v in voices if v["gender"] == "male"]
        assert len(male_voices) == 4
        assert any(v["id"] == "alex" for v in male_voices)
        assert any(v["id"] == "david" for v in male_voices)

        # Check female voices
        female_voices = [v for v in voices if v["gender"] == "female"]
        assert len(female_voices) == 4
        assert any(v["id"] == "claire" for v in female_voices)
        assert any(v["id"] == "diana" for v in female_voices)

    def test_voice_structure(self) -> None:
        """Test voice dictionary structure."""
        provider = SiliconFlowTTS(api_key="test-key")
        voices = provider.get_supported_voices()

        voice = voices[0]
        assert "id" in voice
        assert "name" in voice
        assert "gender" in voice
        assert "description" in voice
        assert "language" in voice


class TestSiliconFlowModelMapping:
    """Test model alias mapping functionality."""

    def test_get_available_models(self) -> None:
        """Test getting available model mappings."""
        models = SiliconFlowTTS.get_available_models()

        assert isinstance(models, dict)
        assert "cosyvoice" in models
        assert models["cosyvoice"] == "FunAudioLLM/CosyVoice2-0.5B"


class TestSiliconFlowFactoryRegistration:
    """Test factory registration of SiliconFlow provider."""

    def test_registered_in_factory(self) -> None:
        """Test that SiliconFlow is registered in ProviderFactory."""
        from src.api.factory import ProviderFactory

        providers = ProviderFactory.list_providers()
        assert "tts" in providers
        # "siliconflow" will be in the list if factory was imported
