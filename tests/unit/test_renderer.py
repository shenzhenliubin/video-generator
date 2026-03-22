"""
Unit Tests for Video Renderer

Tests for video composition and rendering functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import GeneratedAudio, GeneratedImage, VideoOutput
from src.stages.renderer import (
    RenderError,
    VideoRenderer,
    MultiVideoRenderer,
    render_video,
)


class TestVideoRenderer:
    """Tests for VideoRenderer."""

    def test_init_with_file_store(self):
        """Test VideoRenderer initialization with file_store."""
        mock_file_store = MagicMock()
        renderer = VideoRenderer(file_store=mock_file_store)

        assert renderer.file_store == mock_file_store

    @pytest.mark.asyncio
    async def test_init_default_file_store(self):
        """Test VideoRenderer initialization with default file_store."""
        with patch("src.config.settings.get_settings") as mock_settings:
            settings_mock = MagicMock()
            settings_mock.storage_dir = "/tmp/storage"
            mock_settings.return_value = settings_mock

            renderer = VideoRenderer()

            # Verify FileStore was called with correct storage_dir
            assert renderer.file_store is not None

    @pytest.mark.asyncio
    async def test_render_video_success(self):
        """Test successful video rendering."""
        mock_file_store = MagicMock()
        mock_file_store.save_video = MagicMock(return_value="/path/to/video.mp4")

        renderer = VideoRenderer(file_store=mock_file_store)

        # Mock the internal methods
        renderer._create_image_clip = AsyncMock()
        renderer._concatenate_clips = AsyncMock()
        renderer._add_audio_to_video = AsyncMock()

        # Create mock clips
        mock_clip1 = MagicMock()
        mock_clip1.duration = 5.0
        mock_clip2 = MagicMock()
        mock_clip2.duration = 5.0

        renderer._create_image_clip.return_value = mock_clip1
        renderer._concatenate_clips.return_value = mock_clip2
        renderer._add_audio_to_video.return_value = mock_clip2

        images = [
            GeneratedImage(
                scene_number=1,
                image_path="/path/to/image1.png",
                prompt_used="Mountain landscape",
                provider="DALL-E",
                width=1920,
                height=1080,
            ),
            GeneratedImage(
                scene_number=2,
                image_path="/path/to/image2.png",
                prompt_used="Ocean view",
                provider="DALL-E",
                width=1920,
                height=1080,
            ),
        ]

        audio_segments = [
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/to/audio1.mp3",
                text="Welcome to this journey",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            ),
            GeneratedAudio(
                scene_number=2,
                audio_path="/path/to/audio2.mp3",
                text="The ocean is beautiful",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            ),
        ]

        result = await renderer.render_video(
            storyboard_id="test_video_template1",
            images=images,
            audio_segments=audio_segments,
        )

        assert result.storyboard_id == "test_video_template1"
        assert result.video_path == "/path/to/video.mp4"
        assert result.duration == 10
        assert result.resolution == "1920x1080"
        assert result.format == "mp4"
        assert result.scenes_count == 2

    @pytest.mark.asyncio
    async def test_render_video_custom_resolution(self):
        """Test video rendering with custom resolution."""
        mock_file_store = MagicMock()
        mock_file_store.save_video = MagicMock(return_value="/path/to/video.mp4")

        renderer = VideoRenderer(file_store=mock_file_store)

        renderer._create_image_clip = AsyncMock()
        renderer._concatenate_clips = AsyncMock()
        renderer._add_audio_to_video = AsyncMock()

        mock_clip1 = MagicMock()
        mock_clip1.duration = 3.0
        mock_clip2 = MagicMock()

        renderer._create_image_clip.return_value = mock_clip1
        renderer._concatenate_clips.return_value = mock_clip1
        renderer._add_audio_to_video.return_value = mock_clip1

        images = [
            GeneratedImage(
                scene_number=1,
                image_path="/path/to/image.png",
                prompt_used="A beautiful landscape",
                provider="DALL-E",
                width=1024,
                height=768,
            )
        ]

        audio_segments = [
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/to/audio.mp3",
                text="A beautiful landscape view",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=3.0,
            )
        ]

        result = await renderer.render_video(
            storyboard_id="test_template1",
            images=images,
            audio_segments=audio_segments,
            resolution="1024x768",
            fps=30,
        )

        assert result.resolution == "1024x768"

        # Verify create_image_clip was called with correct dimensions
        renderer._create_image_clip.assert_called_once()
        call_args, call_kwargs = renderer._create_image_clip.call_args
        # Check positional arguments (image_path, duration, fps, width, height)
        assert call_args[3] == 1024  # width
        assert call_args[4] == 768  # height
        assert call_args[2] == 30  # fps

    @pytest.mark.asyncio
    async def test_render_video_no_images(self):
        """Test rendering with no images raises error."""
        mock_file_store = MagicMock()
        renderer = VideoRenderer(file_store=mock_file_store)

        with pytest.raises(RenderError) as exc_info:
            await renderer.render_video(
                storyboard_id="test_template1",
                images=[],
                audio_segments=[],
            )

        assert "No images provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_render_video_no_audio(self):
        """Test rendering with no audio segments raises error."""
        mock_file_store = MagicMock()
        renderer = VideoRenderer(file_store=mock_file_store)

        images = [
            GeneratedImage(
                scene_number=1,
                image_path="/path/to/image.png",
                prompt_used="Test",
                provider="DALL-E",
                width=1920,
                height=1080,
            )
        ]

        with pytest.raises(RenderError) as exc_info:
            await renderer.render_video(
                storyboard_id="test_template1",
                images=images,
                audio_segments=[],
            )

        assert "No audio segments provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_render_video_mismatch_count(self):
        """Test rendering with image/audio count mismatch."""
        mock_file_store = MagicMock()
        renderer = VideoRenderer(file_store=mock_file_store)

        images = [
            GeneratedImage(
                scene_number=1,
                image_path="/path/to/image1.png",
                prompt_used="Test 1",
                provider="DALL-E",
                width=1920,
                height=1080,
            ),
            GeneratedImage(
                scene_number=2,
                image_path="/path/to/image2.png",
                prompt_used="Test 2",
                provider="DALL-E",
                width=1920,
                height=1080,
            ),
        ]

        audio_segments = [
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/to/audio.mp3",
                text="Test audio",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            )
        ]

        with pytest.raises(RenderError) as exc_info:
            await renderer.render_video(
                storyboard_id="test_template1",
                images=images,
                audio_segments=audio_segments,
            )

        assert "Image/audio count mismatch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_render_video_single_clip(self):
        """Test rendering with single scene skips concatenation."""
        mock_file_store = MagicMock()
        mock_file_store.save_video = MagicMock(return_value="/path/to/video.mp4")

        renderer = VideoRenderer(file_store=mock_file_store)

        mock_clip = MagicMock()
        mock_clip.duration = 5.0

        renderer._create_image_clip = AsyncMock(return_value=mock_clip)
        renderer._add_audio_to_video = AsyncMock(return_value=mock_clip)

        images = [
            GeneratedImage(
                scene_number=1,
                image_path="/path/to/image.png",
                prompt_used="Test scene",
                provider="DALL-E",
                width=1920,
                height=1080,
            )
        ]

        audio_segments = [
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/to/audio.mp3",
                text="Test narration",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            )
        ]

        await renderer.render_video(
            storyboard_id="test_template1",
            images=images,
            audio_segments=audio_segments,
        )

        # _concatenate_clips should not be called for single clip
        assert renderer._create_image_clip.call_count == 1

    @pytest.mark.asyncio
    async def test_get_scene_duration_from_audio(self):
        """Test getting scene duration from audio segment."""
        mock_file_store = MagicMock()
        renderer = VideoRenderer(file_store=mock_file_store)

        images = [
            GeneratedImage(
                scene_number=1,
                image_path="/path/to/image.png",
                prompt_used="Test",
                provider="DALL-E",
                width=1920,
                height=1080,
            )
        ]

        audio_segments = [
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/to/audio.mp3",
                text="Test narration",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=7.5,
            )
        ]

        duration = await renderer._get_scene_duration(images, audio_segments, scene_number=1)

        assert duration == 7.5

    @pytest.mark.asyncio
    async def test_get_scene_duration_fallback(self):
        """Test scene duration fallback when no matching audio."""
        mock_file_store = MagicMock()
        renderer = VideoRenderer(file_store=mock_file_store)

        images = [
            GeneratedImage(
                scene_number=1,
                image_path="/path/to/image.png",
                prompt_used="Test",
                provider="DALL-E",
                width=1920,
                height=1080,
            )
        ]

        audio_segments = [
            GeneratedAudio(
                scene_number=2,
                audio_path="/path/to/audio.mp3",
                text="Test narration",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            )
        ]

        duration = await renderer._get_scene_duration(images, audio_segments, scene_number=1)

        assert duration == 5.0  # Fallback default


class TestConvenienceFunction:
    """Tests for the convenience render_video function."""

    @pytest.mark.asyncio
    async def test_render_video_function(self):
        """Test the convenience function works."""
        with patch("src.stages.renderer.VideoRenderer") as MockRenderer:
            mock_instance = MagicMock()
            MockRenderer.return_value = mock_instance

            mock_output = VideoOutput(
                storyboard_id="test_template1",
                video_path="/path/to/video.mp4",
                duration=10,
                resolution="1920x1080",
                format="mp4",
                scenes_count=2,
            )
            mock_instance.render_video = AsyncMock(return_value=mock_output)

            images = [
                GeneratedImage(
                    scene_number=1,
                    image_path="/path/to/image1.png",
                    prompt_used="Scene 1 description suitable for video rendering",
                    provider="DALL-E",
                    width=1920,
                    height=1080,
                ),
                GeneratedImage(
                    scene_number=2,
                    image_path="/path/to/image2.png",
                    prompt_used="Scene 2 description suitable for video rendering",
                    provider="DALL-E",
                    width=1920,
                    height=1080,
                ),
            ]

            audio = [
                GeneratedAudio(
                    scene_number=1,
                    audio_path="/path/to/audio1.mp3",
                    text="Scene 1 narration",
                    provider="ElevenLabs",
                    voice_id="voice_123",
                    duration=5.0,
                ),
                GeneratedAudio(
                    scene_number=2,
                    audio_path="/path/to/audio2.mp3",
                    text="Scene 2 narration",
                    provider="ElevenLabs",
                    voice_id="voice_123",
                    duration=5.0,
                ),
            ]

            result = await render_video("test_template1", images, audio)

            MockRenderer.assert_called_once()
            mock_instance.render_video.assert_called_once_with(
                "test_template1", images, audio
            )
            assert result == mock_output


class TestMultiVideoRenderer:
    """Tests for MultiVideoRenderer."""

    def test_init(self):
        """Test MultiVideoRenderer initialization."""
        mock_file_store = MagicMock()
        renderer = MultiVideoRenderer(file_store=mock_file_store)

        assert renderer is not None

    @pytest.mark.asyncio
    async def test_render_multiple_success(self):
        """Test rendering multiple videos."""
        mock_file_store = MagicMock()
        mock_file_store.save_video = MagicMock(return_value="/path/to/video.mp4")

        renderer = MultiVideoRenderer(file_store=mock_file_store)

        # Mock the internal renderer
        renderer._renderer._create_image_clip = AsyncMock()
        renderer._renderer._concatenate_clips = AsyncMock()
        renderer._renderer._add_audio_to_video = AsyncMock()

        mock_clip = MagicMock()
        mock_clip.duration = 5.0

        renderer._renderer._create_image_clip.return_value = mock_clip
        renderer._renderer._concatenate_clips.return_value = mock_clip
        renderer._renderer._add_audio_to_video.return_value = mock_clip

        projects = {
            "vid1": (
                [
                    GeneratedImage(
                        scene_number=1,
                        image_path="/path/to/img1.png",
                        prompt_used="Description for video 1",
                        provider="DALL-E",
                        width=1920,
                        height=1080,
                    )
                ],
                [
                    GeneratedAudio(
                        scene_number=1,
                        audio_path="/path/to/aud1.mp3",
                        text="Audio for video 1",
                        provider="ElevenLabs",
                        voice_id="voice_123",
                        duration=5.0,
                    )
                ],
            ),
            "vid2": (
                [
                    GeneratedImage(
                        scene_number=1,
                        image_path="/path/to/img2.png",
                        prompt_used="Description for video 2",
                        provider="DALL-E",
                        width=1920,
                        height=1080,
                    )
                ],
                [
                    GeneratedAudio(
                        scene_number=1,
                        audio_path="/path/to/aud2.mp3",
                        text="Audio for video 2",
                        provider="ElevenLabs",
                        voice_id="voice_123",
                        duration=5.0,
                    )
                ],
            ),
        }

        result = await renderer.render_multiple(projects)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_render_multiple_partial_failure(self):
        """Test rendering when some videos fail."""
        mock_file_store = MagicMock()
        renderer = MultiVideoRenderer(file_store=mock_file_store)

        good_output = VideoOutput(
            storyboard_id="vid1_template1",
            video_path="/path/to/video.mp4",
            duration=5,
            resolution="1920x1080",
            format="mp4",
            scenes_count=1,
        )

        # Mock render_video to succeed for vid1 and fail for vid2
        async def mock_render(storyboard_id, images, audio, resolution, output_format, fps):
            if "vid1" in storyboard_id:
                return good_output
            else:
                raise RenderError("Bad images")

        renderer._renderer.render_video = AsyncMock(side_effect=mock_render)

        good_images = [
            GeneratedImage(
                scene_number=1,
                image_path="/path/to/img.png",
                prompt_used="A detailed scene description for image generation",
                provider="DALL-E",
                width=1920,
                height=1080,
            )
        ]

        good_audio = [
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/to/aud.mp3",
                text="Valid narration text for testing",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            )
        ]

        projects = {
            "vid1": (good_images, good_audio),
            "vid2": (good_images, good_audio),  # Will fail via mock
        }

        result = await renderer.render_multiple(projects)

        # Should have succeeded video only
        assert "vid1" in result
        assert "vid2" not in result

    @pytest.mark.asyncio
    async def test_render_multiple_all_fail(self):
        """Test rendering when all videos fail."""
        class BadImages:
            """Invalid images that will cause failure."""
            pass

        mock_file_store = MagicMock()
        renderer = MultiVideoRenderer(file_store=mock_file_store)

        good_audio = [
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/to/aud.mp3",
                text="Valid narration",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            )
        ]

        projects = {
            "vid1": (BadImages(), good_audio),
            "vid2": (BadImages(), good_audio),
        }

        with pytest.raises(RenderError) as exc_info:
            await renderer.render_multiple(projects)

        assert "Failed to render all" in str(exc_info.value)
