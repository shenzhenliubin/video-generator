"""
Unit Tests for Voice Actor

Tests for audio generation functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import GeneratedAudio, Scene, Storyboard, StyleTemplate, TemplateCategory
from src.stages.voice import (
    VoiceActor,
    VoiceError,
    MultiVideoVoiceActor,
    generate_audio,
)


class TestVoiceActor:
    """Tests for VoiceActor."""

    def test_init_with_provider(self):
        """Test VoiceActor initialization with provider."""
        mock_provider = MagicMock()
        mock_file_store = MagicMock()
        actor = VoiceActor(provider=mock_provider, file_store=mock_file_store)

        assert actor.provider == mock_provider
        assert actor.file_store == mock_file_store

    @pytest.mark.asyncio
    async def test_init_default_provider(self):
        """Test VoiceActor initialization with default provider."""
        with patch("src.stages.voice.ProviderFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_factory.create_tts.return_value = mock_provider

            with patch("src.stages.voice.get_settings") as mock_settings:
                settings_mock = MagicMock()
                settings_mock.storage_dir = "/tmp/storage"
                mock_settings.return_value = settings_mock

                with patch("src.stages.voice.FileStore") as mock_store_class:
                    mock_store = MagicMock()
                    mock_store_class.return_value = mock_store

                    actor = VoiceActor()

                    assert actor.provider == mock_provider
                    assert actor.file_store == mock_store

    @pytest.mark.asyncio
    async def test_generate_audio_success(self):
        """Test successful audio generation."""
        mock_provider = MagicMock()
        mock_provider.synthesize = AsyncMock(return_value=(b"fake_audio_data", "audio/mpeg"))
        mock_provider.__class__.__name__ = "MockTTSProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_audio = MagicMock(return_value="/path/to/audio.mp3")

        actor = VoiceActor(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_video_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Welcome to this amazing journey",
                    visual_description="Mountain landscape",
                    duration=5,
                )
            ],
            total_duration=5,
        )

        result = await actor.generate_audio(storyboard)

        assert len(result) == 1
        assert result[0].scene_number == 1
        assert result[0].audio_path == "/path/to/audio.mp3"
        assert result[0].text == "Welcome to this amazing journey"
        assert result[0].provider == "MockTTSProvider"
        assert result[0].voice_id is None

    @pytest.mark.asyncio
    async def test_generate_audio_with_template_voice(self):
        """Test audio generation with template voice selection."""
        mock_provider = MagicMock()
        mock_provider.synthesize = AsyncMock(return_value=(b"audio_data", "audio/mpeg"))
        mock_provider.__class__.__name__ = "MockTTSProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_audio = MagicMock(return_value="/path/audio.mp3")

        actor = VoiceActor(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Test narration here",
                    visual_description="Scene description",
                    duration=5,
                )
            ],
            total_duration=5,
        )

        template = StyleTemplate(
            id="template1",
            name="Test",
            category=TemplateCategory.EDUCATIONAL,
            description="Test template",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
            voice_id="voice_123",
        )

        result = await actor.generate_audio(storyboard, template)

        assert len(result) == 1
        # Verify the voice_id was passed to the provider
        call_args = mock_provider.synthesize.call_args
        assert call_args[1]["voice_id"] == "voice_123"
        assert result[0].voice_id == "voice_123"

    @pytest.mark.asyncio
    async def test_generate_audio_multiple_scenes(self):
        """Test generating audio for multiple scenes."""
        mock_provider = MagicMock()
        mock_provider.synthesize = AsyncMock(return_value=(b"audio_data", "audio/mpeg"))
        mock_provider.__class__.__name__ = "MockTTSProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_audio = MagicMock(return_value="/path/scene_001.mp3")

        actor = VoiceActor(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Opening scene",
                    visual_description="Opening",
                    duration=5,
                ),
                Scene(
                    scene_number=2,
                    narration="Middle scene",
                    visual_description="Middle",
                    duration=5,
                ),
                Scene(
                    scene_number=3,
                    narration="Closing scene",
                    visual_description="Closing",
                    duration=5,
                ),
            ],
            total_duration=15,
        )

        result = await actor.generate_audio(storyboard)

        assert len(result) == 3
        assert result[0].scene_number == 1
        assert result[1].scene_number == 2
        assert result[2].scene_number == 3
        assert mock_file_store.save_audio.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_audio_custom_speed(self):
        """Test audio generation with custom speed."""
        mock_provider = MagicMock()
        mock_provider.synthesize = AsyncMock(return_value=(b"audio_data", "audio/mpeg"))
        mock_provider.__class__.__name__ = "MockTTSProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_audio = MagicMock(return_value="/path/audio.mp3")

        actor = VoiceActor(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Test narration text",
                    visual_description="Scene description",
                    duration=5,
                )
            ],
            total_duration=5,
        )

        result = await actor.generate_audio(storyboard, speed=1.5)

        assert len(result) == 1
        # Verify the speed was passed to the provider
        call_args = mock_provider.synthesize.call_args
        assert call_args[1]["speed"] == 1.5

    @pytest.mark.asyncio
    async def test_generate_audio_provider_error(self):
        """Test handling TTS provider error."""
        mock_provider = MagicMock()
        mock_provider.synthesize = AsyncMock(side_effect=Exception("API error"))

        mock_file_store = MagicMock()

        actor = VoiceActor(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Test narration",
                    visual_description="Scene description that is detailed enough",
                    duration=5,
                )
            ],
            total_duration=5,
        )

        with pytest.raises(VoiceError) as exc_info:
            await actor.generate_audio(storyboard)

        assert "Failed to generate audio" in str(exc_info.value)


class TestConvenienceFunction:
    """Tests for the convenience generate_audio function."""

    @pytest.mark.asyncio
    async def test_generate_audio_function(self):
        """Test the convenience function works."""
        with patch("src.stages.voice.VoiceActor") as MockActor:
            mock_instance = MagicMock()
            MockActor.return_value = mock_instance

            mock_audio = [
                GeneratedAudio(
                    scene_number=1,
                    audio_path="/path/to/audio.mp3",
                    text="Test narration here",
                    provider="MockTTSProvider",
                    voice_id=None,
                    duration=3.5,
                )
            ]
            mock_instance.generate_audio = AsyncMock(return_value=mock_audio)

            storyboard = Storyboard(
                script_id="test_template1",
                scenes=[
                    Scene(
                        scene_number=1,
                        narration="Narration",
                        visual_description="A detailed scene description suitable for audio generation",
                        duration=5,
                    )
                ],
                total_duration=5,
            )

            result = await generate_audio(storyboard)

            MockActor.assert_called_once()
            mock_instance.generate_audio.assert_called_once_with(storyboard, None)
            assert result == mock_audio


class TestMultiVideoVoiceActor:
    """Tests for MultiVideoVoiceActor."""

    def test_init(self):
        """Test MultiVideoVoiceActor initialization."""
        mock_provider = MagicMock()
        mock_file_store = MagicMock()
        actor = MultiVideoVoiceActor(provider=mock_provider, file_store=mock_file_store)

        assert actor is not None

    @pytest.mark.asyncio
    async def test_generate_multiple_success(self):
        """Test generating audio for multiple storyboards."""
        mock_provider = MagicMock()
        mock_provider.synthesize = AsyncMock(return_value=(b"data", "audio/mpeg"))
        mock_provider.__class__.__name__ = "MockTTSProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_audio = MagicMock(return_value="/path/audio.mp3")

        actor = MultiVideoVoiceActor(provider=mock_provider, file_store=mock_file_store)

        storyboards = {
            "vid1": Storyboard(
                script_id="vid1_template1",
                scenes=[
                    Scene(
                        scene_number=1,
                        narration="Narration for video 1",
                        visual_description="Description for video 1",
                        duration=5,
                    )
                ],
                total_duration=5,
            ),
            "vid2": Storyboard(
                script_id="vid2_template1",
                scenes=[
                    Scene(
                        scene_number=1,
                        narration="Narration for video 2",
                        visual_description="Description for video 2",
                        duration=5,
                    )
                ],
                total_duration=5,
            ),
        }

        result = await actor.generate_multiple(storyboards)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_generate_multiple_with_different_templates(self):
        """Test generating audio with different templates per video."""
        mock_provider = MagicMock()
        mock_provider.synthesize = AsyncMock(return_value=(b"data", "audio/mpeg"))
        mock_provider.__class__.__name__ = "MockTTSProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_audio = MagicMock(return_value="/path/audio.mp3")

        actor = MultiVideoVoiceActor(provider=mock_provider, file_store=mock_file_store)

        storyboards = {
            "vid1": Storyboard(
                script_id="vid1_template1",
                scenes=[
                    Scene(
                        scene_number=1,
                        narration="Narration for video 1",
                        visual_description="Description for video 1",
                        duration=5,
                    )
                ],
                total_duration=5,
            ),
            "vid2": Storyboard(
                script_id="vid2_template2",
                scenes=[
                    Scene(
                        scene_number=1,
                        narration="Narration for video 2",
                        visual_description="Description for video 2",
                        duration=5,
                    )
                ],
                total_duration=5,
            ),
        }

        templates = {
            "vid1": StyleTemplate(
                id="template1",
                name="Dramatic",
                category=TemplateCategory.DRAMATIC,
                description="Test",
                llm_provider="openai",
                image_provider="openai",
                tts_provider="elevenlabs",
                voice_id="voice_1",
            ),
            "vid2": StyleTemplate(
                id="template2",
                name="Humorous",
                category=TemplateCategory.HUMOROUS,
                description="Test",
                llm_provider="openai",
                image_provider="openai",
                tts_provider="elevenlabs",
                voice_id="voice_2",
            ),
        }

        result = await actor.generate_multiple_with_templates(storyboards, templates)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_generate_multiple_partial_failure(self):
        """Test generating audio when some storyboards fail."""
        class BadStoryboard:
            script_id = "bad"  # Has the attribute but will fail on scenes

        mock_provider = MagicMock()
        mock_provider.synthesize = AsyncMock(return_value=(b"data", "audio/mpeg"))
        mock_provider.__class__.__name__ = "MockTTSProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_audio = MagicMock(return_value="/path/audio.mp3")

        actor = MultiVideoVoiceActor(provider=mock_provider, file_store=mock_file_store)

        good_storyboard = Storyboard(
            script_id="vid1_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Valid narration text for testing",
                    visual_description="A detailed scene description for audio generation purposes",
                    duration=5,
                )
            ],
            total_duration=5,
        )

        storyboards = {
            "vid1": good_storyboard,
            "vid2": BadStoryboard(),  # This will fail
        }

        template = StyleTemplate(
            id="template1",
            name="Test",
            category=TemplateCategory.EDUCATIONAL,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        result = await actor.generate_multiple(storyboards, template)

        # Should have succeeded audio only
        assert "vid1" in result
        assert "vid2" not in result

    @pytest.mark.asyncio
    async def test_generate_multiple_all_fail(self):
        """Test generating audio when all storyboards fail."""
        class BadStoryboard:
            script_id = "bad"  # Has the attribute but will fail on scenes

        mock_provider = MagicMock()
        mock_file_store = MagicMock()

        actor = MultiVideoVoiceActor(provider=mock_provider, file_store=mock_file_store)

        storyboards = {
            "vid1": BadStoryboard(),
            "vid2": BadStoryboard(),
        }

        template = StyleTemplate(
            id="template1",
            name="Test",
            category=TemplateCategory.EDUCATIONAL,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        with pytest.raises(VoiceError) as exc_info:
            await actor.generate_multiple(storyboards, template)

        assert "Failed to generate audio for all" in str(exc_info.value)
