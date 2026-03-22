"""
Unit Tests for Video Artist

Tests for image generation functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import GeneratedImage, Scene, Storyboard, StyleTemplate, TemplateCategory
from src.stages.artist import (
    ArtistError,
    VideoArtist,
    MultiVideoArtist,
    generate_images,
)


class TestVideoArtist:
    """Tests for VideoArtist."""

    def test_init_with_provider(self):
        """Test VideoArtist initialization with provider."""
        mock_provider = MagicMock()
        mock_file_store = MagicMock()
        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        assert artist.provider == mock_provider
        assert artist.file_store == mock_file_store

    @pytest.mark.asyncio
    async def test_init_default_provider(self):
        """Test VideoArtist initialization with default provider."""
        with patch("src.stages.artist.ProviderFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_factory.create_image.return_value = mock_provider

            with patch("src.stages.artist.get_settings") as mock_settings:
                settings_mock = MagicMock()
                settings_mock.storage_dir = "/tmp/storage"
                mock_settings.return_value = settings_mock

                with patch("src.stages.artist.FileStore") as mock_store_class:
                    mock_store = MagicMock()
                    mock_store_class.return_value = mock_store

                    artist = VideoArtist()

                    assert artist.provider == mock_provider
                    assert artist.file_store == mock_store

    @pytest.mark.asyncio
    async def test_generate_images_success(self):
        """Test successful image generation."""
        mock_provider = MagicMock()
        mock_provider.generate_image = AsyncMock(return_value=b"fake_image_data")
        mock_provider.__class__.__name__ = "MockProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_image = MagicMock(return_value="/path/to/image.png")

        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_video_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Test narration",
                    visual_description="A beautiful mountain landscape",
                    duration=5,
                    camera_movement="static",
                    mood="peaceful",
                )
            ],
            total_duration=5,
        )

        result = await artist.generate_images(storyboard)

        assert len(result) == 1
        assert result[0].scene_number == 1
        assert result[0].image_path == "/path/to/image.png"
        assert result[0].provider == "MockProvider"
        assert result[0].width == 1920
        assert result[0].height == 1080
        assert "mountain landscape" in result[0].prompt_used

    @pytest.mark.asyncio
    async def test_generate_images_with_template(self):
        """Test image generation with style template."""
        mock_provider = MagicMock()
        mock_provider.generate_image = AsyncMock(return_value=b"image_data")
        mock_provider.__class__.__name__ = "MockProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_image = MagicMock(return_value="/path/image.png")

        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Narration",
                    visual_description="Scene description here",
                    duration=5,
                    camera_movement="wide shot",
                    mood="dramatic",
                )
            ],
            total_duration=5,
        )

        template = StyleTemplate(
            id="template1",
            name="Cinematic",
            category=TemplateCategory.CINEMATIC,
            description="Cinematic template",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
            image_style_prompt="photorealistic, cinematic lighting",
        )

        result = await artist.generate_images(storyboard, template)

        assert len(result) == 1
        # Verify the style was passed to the provider
        call_args = mock_provider.generate_image.call_args
        assert call_args[1]["style"] == "photorealistic, cinematic lighting"

    @pytest.mark.asyncio
    async def test_generate_images_multiple_scenes(self):
        """Test generating images for multiple scenes."""
        mock_provider = MagicMock()
        mock_provider.generate_image = AsyncMock(return_value=b"image_data")
        mock_provider.__class__.__name__ = "MockProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_image = MagicMock(return_value="/path/scene_001.png")

        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Opening",
                    visual_description="Opening scene",
                    duration=5,
                    camera_movement="wide shot",
                    mood="neutral",
                ),
                Scene(
                    scene_number=2,
                    narration="Middle",
                    visual_description="Middle scene",
                    duration=5,
                    camera_movement="close-up",
                    mood="intense",
                ),
                Scene(
                    scene_number=3,
                    narration="End",
                    visual_description="Ending scene",
                    duration=5,
                    camera_movement="static",
                    mood="peaceful",
                ),
            ],
            total_duration=15,
        )

        result = await artist.generate_images(storyboard)

        assert len(result) == 3
        assert result[0].scene_number == 1
        assert result[1].scene_number == 2
        assert result[2].scene_number == 3
        assert mock_file_store.save_image.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_images_custom_dimensions(self):
        """Test image generation with custom dimensions."""
        mock_provider = MagicMock()
        mock_provider.generate_image = AsyncMock(return_value=b"image_data")
        mock_provider.__class__.__name__ = "MockProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_image = MagicMock(return_value="/path/image.png")

        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Text",
                    visual_description="Scene description",
                    duration=5,
                )
            ],
            total_duration=5,
        )

        result = await artist.generate_images(storyboard, width=1024, height=768)

        assert result[0].width == 1024
        assert result[0].height == 768

    @pytest.mark.asyncio
    async def test_generate_images_provider_error(self):
        """Test handling image provider error."""
        mock_provider = MagicMock()
        mock_provider.generate_image = AsyncMock(side_effect=Exception("API error"))

        mock_file_store = MagicMock()

        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        storyboard = Storyboard(
            script_id="test_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Text",
                    visual_description="Scene description that is detailed enough",
                    duration=5,
                )
            ],
            total_duration=5,
        )

        with pytest.raises(ArtistError) as exc_info:
            await artist.generate_images(storyboard)

        assert "Failed to generate images" in str(exc_info.value)

    def test_build_prompt_with_scene_details(self):
        """Test building prompt from scene data."""
        mock_provider = MagicMock()
        mock_file_store = MagicMock()
        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        scene = Scene(
            scene_number=1,
            narration="Test narration here",
            visual_description="A dramatic sunset over the ocean",
            duration=5,
            camera_movement="low angle",
            mood="dramatic",
        )

        prompt = artist._build_prompt(scene)

        assert "sunset over the ocean" in prompt
        assert "dramatic" in prompt.lower()

    def test_camera_to_composition_mapping(self):
        """Test camera movement to composition hint mapping."""
        mock_provider = MagicMock()
        mock_file_store = MagicMock()
        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        # Test various camera movements
        assert "centered" in artist._camera_to_composition("static")
        assert "panoramic" in artist._camera_to_composition("panning")
        assert "shallow" in artist._camera_to_composition("close-up")
        assert "expansive" in artist._camera_to_composition("wide shot")

    def test_get_category_style(self):
        """Test category-based style hints."""
        mock_provider = MagicMock()
        mock_file_store = MagicMock()
        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        assert "dramatic" in artist._get_category_style("dramatic").lower()
        assert "cinematic" in artist._get_category_style("cinematic").lower()
        assert "bright" in artist._get_category_style("humorous").lower()

    def test_get_aspect_ratio(self):
        """Test aspect ratio calculation."""
        mock_provider = MagicMock()
        mock_file_store = MagicMock()
        artist = VideoArtist(provider=mock_provider, file_store=mock_file_store)

        assert artist._get_aspect_ratio(1920, 1080) == "16:9"
        assert artist._get_aspect_ratio(1024, 768) == "4:3"
        assert artist._get_aspect_ratio(1080, 1080) == "1:1"


class TestConvenienceFunction:
    """Tests for the convenience generate_images function."""

    @pytest.mark.asyncio
    async def test_generate_images_function(self):
        """Test the convenience function works."""
        with patch("src.stages.artist.VideoArtist") as MockArtist:
            mock_instance = MagicMock()
            MockArtist.return_value = mock_instance

            mock_images = [
                GeneratedImage(
                    scene_number=1,
                    image_path="/path/to/image.png",
                    prompt_used="Test prompt here",
                    provider="MockProvider",
                    width=1920,
                    height=1080,
                )
            ]
            mock_instance.generate_images = AsyncMock(return_value=mock_images)

            storyboard = Storyboard(
                script_id="test_template1",
                scenes=[
                    Scene(
                        scene_number=1,
                        narration="Narration",
                        visual_description="A detailed scene description suitable for image generation",
                        duration=5,
                    )
                ],
                total_duration=5,
            )

            result = await generate_images(storyboard)

            MockArtist.assert_called_once()
            mock_instance.generate_images.assert_called_once_with(storyboard, None)
            assert result == mock_images


class TestMultiVideoArtist:
    """Tests for MultiVideoArtist."""

    def test_init(self):
        """Test MultiVideoArtist initialization."""
        mock_provider = MagicMock()
        mock_file_store = MagicMock()
        artist = MultiVideoArtist(provider=mock_provider, file_store=mock_file_store)

        assert artist is not None

    @pytest.mark.asyncio
    async def test_generate_multiple_success(self):
        """Test generating images for multiple storyboards."""
        mock_provider = MagicMock()
        mock_provider.generate_image = AsyncMock(return_value=b"data")
        mock_provider.__class__.__name__ = "MockProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_image = MagicMock(return_value="/path/img.png")

        artist = MultiVideoArtist(provider=mock_provider, file_store=mock_file_store)

        storyboards = {
            "vid1": Storyboard(
                script_id="vid1_template1",
                scenes=[
                    Scene(
                        scene_number=1,
                        narration="Text",
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
                        narration="Text",
                        visual_description="Description for video 2",
                        duration=5,
                    )
                ],
                total_duration=5,
            ),
        }

        result = await artist.generate_multiple(storyboards)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_generate_multiple_with_different_templates(self):
        """Test generating images with different templates per video."""
        mock_provider = MagicMock()
        mock_provider.generate_image = AsyncMock(return_value=b"data")
        mock_provider.__class__.__name__ = "MockProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_image = MagicMock(return_value="/path/img.png")

        artist = MultiVideoArtist(provider=mock_provider, file_store=mock_file_store)

        storyboards = {
            "vid1": Storyboard(
                script_id="vid1_template1",
                scenes=[
                    Scene(
                        scene_number=1,
                        narration="Text",
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
                        narration="Text",
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
            ),
            "vid2": StyleTemplate(
                id="template2",
                name="Humorous",
                category=TemplateCategory.HUMOROUS,
                description="Test",
                llm_provider="openai",
                image_provider="openai",
                tts_provider="elevenlabs",
            ),
        }

        result = await artist.generate_multiple_with_templates(storyboards, templates)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_generate_multiple_partial_failure(self):
        """Test generating images when some storyboards fail."""
        class BadStoryboard:
            script_id = "bad"  # Will fail when processed

        mock_provider = MagicMock()
        mock_provider.generate_image = AsyncMock(return_value=b"data")
        mock_provider.__class__.__name__ = "MockProvider"

        mock_file_store = MagicMock()
        mock_file_store.save_image = MagicMock(return_value="/path/img.png")

        artist = MultiVideoArtist(provider=mock_provider, file_store=mock_file_store)

        good_storyboard = Storyboard(
            script_id="vid1_template1",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Text",
                    visual_description="A detailed scene description for image generation purposes",
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

        result = await artist.generate_multiple(storyboards, template)

        # Should have succeeded images only
        assert "vid1" in result
        assert "vid2" not in result

    @pytest.mark.asyncio
    async def test_generate_multiple_all_fail(self):
        """Test generating images when all storyboards fail."""
        class BadStoryboard:
            script_id = "bad"

        mock_provider = MagicMock()
        mock_file_store = MagicMock()

        artist = MultiVideoArtist(provider=mock_provider, file_store=mock_file_store)

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

        with pytest.raises(ArtistError) as exc_info:
            await artist.generate_multiple(storyboards, template)

        assert "Failed to generate images for all" in str(exc_info.value)
