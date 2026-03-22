"""
Unit Tests for Video Pipeline

Tests for the pipeline orchestrator that coordinates all 9 stages.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datetime import datetime

from src.core.models import (
    ContentAnalysis,
    GeneratedAudio,
    GeneratedImage,
    PipelineStage,
    RewrittenScript,
    Scene,
    Storyboard,
    StyleTemplate,
    TemplateCategory,
    Transcript,
    TranscriptSegment,
    VideoMetadata,
    VideoOutput,
)
from src.core.pipeline import (
    MultiVideoPipeline,
    PipelineError,
    VideoPipeline,
    process_multiple_videos,
    process_video,
)


class TestVideoPipeline:
    """Tests for VideoPipeline."""

    def test_init_with_template(self):
        """Test VideoPipeline initialization with template."""
        mock_template = MagicMock(spec=StyleTemplate)
        mock_file_store = MagicMock()
        mock_checkpoint_store = MagicMock()

        with patch("src.core.pipeline.FileStore", return_value=mock_file_store):
            with patch("src.core.pipeline.CheckpointStore", return_value=mock_checkpoint_store):
                pipeline = VideoPipeline(template=mock_template)

        assert pipeline.template == mock_template

    @pytest.mark.asyncio
    async def test_init_default_template(self):
        """Test VideoPipeline initialization with default template."""
        mock_file_store = MagicMock()
        mock_checkpoint_store = MagicMock()

        with patch("src.core.pipeline.get_settings") as mock_settings:
            settings_mock = MagicMock()
            settings_mock.storage_dir = "./storage"
            mock_settings.return_value = settings_mock

        with patch("src.core.pipeline.FileStore", return_value=mock_file_store):
            with patch("src.core.pipeline.CheckpointStore", return_value=mock_checkpoint_store):
                pipeline = VideoPipeline()

        assert pipeline.template is None

    @pytest.mark.asyncio
    async def test_process_video_success(self):
        """Test successful video processing through all stages."""
        mock_template = MagicMock(spec=StyleTemplate)
        mock_template.category = TemplateCategory.DRAMATIC

        mock_file_store = MagicMock()
        mock_checkpoint_store = MagicMock()

        with patch("src.core.pipeline.FileStore", return_value=mock_file_store):
            with patch("src.core.pipeline.CheckpointStore", return_value=mock_checkpoint_store):
                pipeline = VideoPipeline(template=mock_template)

        # Mock all stage methods
        pipeline._run_watcher = AsyncMock(return_value=VideoMetadata(
            video_id="test_vid",
            channel_id="test_channel",
            channel_name="Test Channel",
            title="Test Video",
            description="Test Description",
            published_at=datetime.now(),
            duration=300,
            thumbnail_url="https://example.com/thumb.jpg",
            url="https://youtube.com/watch?v=test_vid",
        ))

        pipeline._run_fetcher = AsyncMock(return_value=Transcript(
            video_id="test_vid",
            raw_text="Hello world",
            language="en",
            segments=[
                TranscriptSegment(
                    text="Hello world",
                    start=0.0,
                    duration=5.0,
                )
            ],
        ))

        pipeline._run_parser = AsyncMock()
        pipeline._run_analyzer = AsyncMock(return_value=ContentAnalysis(
            video_id="test_vid",
            summary="A test video about hello world",
            main_points=["Point 1", "Point 2"],
            topics=["test", "hello"],
            sentiment="neutral",
        ))

        pipeline._run_writer = AsyncMock(return_value=RewrittenScript(
            original_video_id="test_vid",
            template_id="dramatic",
            title="Test Video",
            script="Rewritten content with enough detail to pass validation",
            style_notes="Dramatic style applied",
        ))

        pipeline._run_director = AsyncMock(return_value=Storyboard(
            script_id="test_vid_dramatic",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Scene 1 narration that is long enough",
                    visual_description="Scene description",
                    duration=5,
                )
            ],
            total_duration=5,
        ))

        pipeline._run_artist = AsyncMock(return_value=[
            GeneratedImage(
                scene_number=1,
                image_path="/path/to/image.png",
                prompt_used="Scene description",
                provider="DALL-E",
                width=1920,
                height=1080,
            )
        ])

        pipeline._run_voice = AsyncMock(return_value=[
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/to/audio.mp3",
                text="Scene 1 narration",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            )
        ])

        pipeline._run_renderer = AsyncMock(return_value=VideoOutput(
            storyboard_id="test_vid_dramatic",
            video_path="/path/to/video.mp4",
            duration=5,
            resolution="1920x1080",
            scenes_count=1,
        ))

        # Mock checkpoint save
        mock_checkpoint_store.save = MagicMock()

        result = await pipeline.process_video("test_vid")

        assert result.video_path == "/path/to/video.mp4"
        assert result.scenes_count == 1

    @pytest.mark.asyncio
    async def test_process_video_with_resume(self):
        """Test processing with resume from checkpoint."""
        mock_template = MagicMock(spec=StyleTemplate)

        mock_file_store = MagicMock()
        mock_checkpoint_store = MagicMock()

        # Simulate having a checkpoint at PARSER stage
        mock_checkpoint_store.get_latest_stage = MagicMock(return_value=PipelineStage.PARSER)

        with patch("src.core.pipeline.FileStore", return_value=mock_file_store):
            with patch("src.core.pipeline.CheckpointStore", return_value=mock_checkpoint_store):
                pipeline = VideoPipeline(template=mock_template)

        # Mock methods from PARSER onward
        pipeline._run_watcher = AsyncMock()
        pipeline._run_fetcher = AsyncMock()
        pipeline._run_parser = AsyncMock()
        pipeline._run_analyzer = AsyncMock(return_value=ContentAnalysis(
            video_id="test_vid",
            summary="Summary of the video",
            main_points=["Point"],
            topics=["test"],
            sentiment="neutral",
        ))

        pipeline._run_writer = AsyncMock(return_value=RewrittenScript(
            original_video_id="test_vid",
            template_id="dramatic",
            title="Test Video",
            script="Content that is long enough to pass validation with more detail",
            style_notes="Dramatic style",
        ))

        pipeline._run_director = AsyncMock(return_value=Storyboard(
            script_id="test_vid_dramatic",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Long narration text for scene one",
                    visual_description="Description",
                    duration=5,
                )
            ],
            total_duration=5,
        ))

        pipeline._run_artist = AsyncMock(return_value=[
            GeneratedImage(
                scene_number=1,
                image_path="/path/image.png",
                prompt_used="Description",
                provider="DALL-E",
                width=1920,
                height=1080,
            )
        ])

        pipeline._run_voice = AsyncMock(return_value=[
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/audio.mp3",
                text="Narration",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            )
        ])

        pipeline._run_renderer = AsyncMock(return_value=VideoOutput(
            storyboard_id="test_vid_dramatic",
            video_path="/path/video.mp4",
            duration=5,
            resolution="1920x1080",
            scenes_count=1,
        ))

        mock_checkpoint_store.save = MagicMock()

        result = await pipeline.process_video("test_vid", resume=True)

        assert result.video_path == "/path/video.mp4"
        # Should skip WATCHER and FETCHER stages
        pipeline._run_watcher.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_video_start_from_stage(self):
        """Test processing starting from a specific stage."""
        mock_template = MagicMock(spec=StyleTemplate)

        mock_file_store = MagicMock()
        mock_checkpoint_store = MagicMock()

        with patch("src.core.pipeline.FileStore", return_value=mock_file_store):
            with patch("src.core.pipeline.CheckpointStore", return_value=mock_checkpoint_store):
                pipeline = VideoPipeline(template=mock_template)

        # Mock from DIRECTOR onward
        pipeline._run_director = AsyncMock(return_value=Storyboard(
            script_id="test_vid_dramatic",
            scenes=[
                Scene(
                    scene_number=1,
                    narration="Long narration text for testing",
                    visual_description="Description",
                    duration=5,
                )
            ],
            total_duration=5,
        ))

        pipeline._run_artist = AsyncMock(return_value=[
            GeneratedImage(
                scene_number=1,
                image_path="/path/image.png",
                prompt_used="Description",
                provider="DALL-E",
                width=1920,
                height=1080,
            )
        ])

        pipeline._run_voice = AsyncMock(return_value=[
            GeneratedAudio(
                scene_number=1,
                audio_path="/path/audio.mp3",
                text="Narration",
                provider="ElevenLabs",
                voice_id="voice_123",
                duration=5.0,
            )
        ])

        pipeline._run_renderer = AsyncMock(return_value=VideoOutput(
            storyboard_id="test_vid_dramatic",
            video_path="/path/video.mp4",
            duration=5,
            resolution="1920x1080",
            scenes_count=1,
        ))

        mock_checkpoint_store.save = MagicMock()

        result = await pipeline.process_video(
            "test_vid", start_from=PipelineStage.DIRECTOR
        )

        assert result.video_path == "/path/video.mp4"

    @pytest.mark.asyncio
    async def test_process_video_stage_failure(self):
        """Test pipeline handling of stage failure."""
        mock_template = MagicMock(spec=StyleTemplate)

        mock_file_store = MagicMock()
        mock_checkpoint_store = MagicMock()

        with patch("src.core.pipeline.FileStore", return_value=mock_file_store):
            with patch("src.core.pipeline.CheckpointStore", return_value=mock_checkpoint_store):
                pipeline = VideoPipeline(template=mock_template)

        # Mock watcher to succeed
        pipeline._run_watcher = AsyncMock(return_value=VideoMetadata(
            video_id="test_vid",
            channel_id="test",
            channel_name="Test",
            title="Test",
            description="Test",
            published_at=datetime.now(),
            duration=100,
            thumbnail_url="https://example.com/thumb.jpg",
            url="https://youtube.com/watch?v=test_vid",
        ))

        # Mock fetcher to fail
        pipeline._run_fetcher = AsyncMock(side_effect=PipelineError("Fetcher failed: Network error"))

        with pytest.raises(PipelineError) as exc_info:
            await pipeline.process_video("test_vid")

        assert "Fetcher failed" in str(exc_info.value)

    def test_get_next_stage(self):
        """Test getting next stage in pipeline."""
        pipeline = VideoPipeline()

        # Test middle stages
        assert pipeline._get_next_stage(PipelineStage.WATCHER) == PipelineStage.FETCHER
        assert pipeline._get_next_stage(PipelineStage.ANALYZER) == PipelineStage.WRITER

        # Test last stage stays at last
        assert pipeline._get_next_stage(PipelineStage.RENDERER) == PipelineStage.RENDERER

    def test_get_progress(self):
        """Test getting progress information."""
        mock_template = MagicMock(spec=StyleTemplate)
        mock_file_store = MagicMock()
        mock_checkpoint_store = MagicMock()

        with patch("src.core.pipeline.FileStore", return_value=mock_file_store):
            with patch("src.core.pipeline.CheckpointStore", return_value=mock_checkpoint_store):
                pipeline = VideoPipeline(template=mock_template)

        # Progress doesn't exist yet
        assert pipeline.get_progress("nonexistent") is None

        # Add some progress
        pipeline._progress["test_vid"] = {
            "video_id": "test_vid",
            "current_stage": "analyzer",
            "stages_completed": ["watcher", "fetcher"],
        }

        result = pipeline.get_progress("test_vid")
        assert result["video_id"] == "test_vid"
        assert result["current_stage"] == "analyzer"
        assert result["stages_completed"] == ["watcher", "fetcher"]


class TestMultiVideoPipeline:
    """Tests for MultiVideoPipeline."""

    def test_init(self):
        """Test MultiVideoPipeline initialization."""
        mock_template = MagicMock(spec=StyleTemplate)
        pipeline = MultiVideoPipeline(template=mock_template, max_concurrent=5)

        assert pipeline.template == mock_template
        assert pipeline.max_concurrent == 5

    @pytest.mark.asyncio
    async def test_init_default_concurrency(self):
        """Test MultiVideoPipeline with default concurrency."""
        with patch("src.core.pipeline.get_settings") as mock_settings:
            settings_mock = MagicMock()
            settings_mock.storage_dir = "./storage"
            settings_mock.max_concurrent_videos = 3
            mock_settings.return_value = settings_mock

        pipeline = MultiVideoPipeline()

        assert pipeline.max_concurrent == 3

    @pytest.mark.asyncio
    async def test_process_multiple_success(self):
        """Test processing multiple videos successfully."""
        mock_template = MagicMock(spec=StyleTemplate)
        pipeline = MultiVideoPipeline(template=mock_template, max_concurrent=2)

        # Mock VideoPipeline
        with patch("src.core.pipeline.VideoPipeline") as MockPipeline:
            mock_instance = MagicMock()
            MockPipeline.return_value = mock_instance

            mock_instance.process_video = AsyncMock(return_value=VideoOutput(
                storyboard_id="vid1_dramatic",
                video_path="/path/vid1.mp4",
                duration=10,
                resolution="1920x1080",
                scenes_count=2,
            ))

            results = await pipeline.process_multiple(["vid1", "vid2"])

            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_process_multiple_partial_failure(self):
        """Test processing when some videos fail."""
        mock_template = MagicMock(spec=StyleTemplate)
        pipeline = MultiVideoPipeline(template=mock_template, max_concurrent=2)

        # Mock VideoPipeline to fail for vid2
        with patch("src.core.pipeline.VideoPipeline") as MockPipeline:
            mock_instance = MagicMock()
            MockPipeline.return_value = mock_instance

            async def mock_process(vid, *args, **kwargs):
                if vid == "vid1":
                    return VideoOutput(
                        storyboard_id="vid1_dramatic",
                        video_path="/path/vid1.mp4",
                        duration=10,
                        resolution="1920x1080",
                        scenes_count=2,
                    )
                else:
                    raise PipelineError("Processing failed")

            mock_instance.process_video = AsyncMock(side_effect=mock_process)

            results = await pipeline.process_multiple(["vid1", "vid2"])

            # Should have succeeded video
            assert "vid1" in results
            assert "vid2" not in results
            assert len(pipeline._errors) == 1

    @pytest.mark.asyncio
    async def test_process_multiple_all_fail(self):
        """Test processing when all videos fail."""
        mock_template = MagicMock(spec=StyleTemplate)
        pipeline = MultiVideoPipeline(template=mock_template)

        with patch("src.core.pipeline.VideoPipeline") as MockPipeline:
            mock_instance = MagicMock()
            MockPipeline.return_value = mock_instance

            mock_instance.process_video = AsyncMock(
                side_effect=PipelineError("All failed")
            )

            with pytest.raises(PipelineError) as exc_info:
                await pipeline.process_multiple(["vid1", "vid2"])

            assert "Failed to process all" in str(exc_info.value)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_process_video_function(self):
        """Test the convenience process_video function."""
        with patch("src.core.pipeline.VideoPipeline") as MockPipeline:
            mock_instance = MagicMock()
            MockPipeline.return_value = mock_instance

            mock_output = VideoOutput(
                storyboard_id="test_dramatic",
                video_path="/path/test.mp4",
                duration=10,
                resolution="1920x1080",
                scenes_count=2,
            )
            mock_instance.process_video = AsyncMock(return_value=mock_output)

            result = await process_video("test_vid")

            MockPipeline.assert_called_once()
            mock_instance.process_video.assert_called_once_with("test_vid", resume=False)
            assert result == mock_output

    @pytest.mark.asyncio
    async def test_process_multiple_videos_function(self):
        """Test the convenience process_multiple_videos function."""
        with patch("src.core.pipeline.MultiVideoPipeline") as MockPipeline:
            mock_instance = MagicMock()
            MockPipeline.return_value = mock_instance

            mock_results = {
                "vid1": VideoOutput(
                    storyboard_id="vid1_dramatic",
                    video_path="/path/vid1.mp4",
                    duration=10,
                    resolution="1920x1080",
                    scenes_count=2,
                )
            }
            mock_instance.process_multiple = AsyncMock(return_value=mock_results)

            result = await process_multiple_videos(["vid1", "vid2"])

            MockPipeline.assert_called_once()
            assert result == mock_results
