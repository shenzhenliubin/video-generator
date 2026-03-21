"""
Unit Tests for Data Models

Tests for Pydantic model validation.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.core.models import (
    ContentAnalysis,
    StyleTemplate,
    TemplateCategory,
    TranscriptSegment,
    VideoMetadata,
)


class TestVideoMetadata:
    """Tests for VideoMetadata model."""

    def test_create_valid_metadata(self, sample_video_id, sample_channel_id):
        """Test creating valid video metadata."""
        metadata = VideoMetadata(
            video_id=sample_video_id,
            channel_id=sample_channel_id,
            channel_name="Test Channel",
            title="Test Video",
            description="A test video",
            published_at=datetime.now(),
            duration=600,
            thumbnail_url="https://example.com/thumb.jpg",
            url="https://youtube.com/watch?v=test",
        )
        assert metadata.video_id == sample_video_id
        assert metadata.duration == 600

    def test_invalid_duration(self, sample_video_id, sample_channel_id):
        """Test that invalid duration raises validation error."""
        with pytest.raises(ValidationError):
            VideoMetadata(
                video_id=sample_video_id,
                channel_id=sample_channel_id,
                channel_name="Test Channel",
                title="Test Video",
                description="A test video",
                published_at=datetime.now(),
                duration=-1,  # Invalid
                thumbnail_url="https://example.com/thumb.jpg",
                url="https://youtube.com/watch?v=test",
            )


class TestContentAnalysis:
    """Tests for ContentAnalysis model."""

    def test_create_valid_analysis(self, sample_video_id):
        """Test creating valid content analysis."""
        analysis = ContentAnalysis(
            video_id=sample_video_id,
            main_points=["Point 1", "Point 2", "Point 3"],
            summary="A summary of the content",
            topics=["AI", "Technology"],
        )
        assert len(analysis.main_points) == 3
        assert analysis.topics == ["AI", "Technology"]

    def test_main_points_out_of_range(self, sample_video_id):
        """Test that too many main points raises validation error."""
        with pytest.raises(ValidationError):
            ContentAnalysis(
                video_id=sample_video_id,
                main_points=[f"Point {i}" for i in range(10)],  # Too many
                summary="A summary",
            )


class TestStyleTemplate:
    """Tests for StyleTemplate model."""

    def test_create_valid_template(self):
        """Test creating valid style template."""
        template = StyleTemplate(
            id="test-template",
            name="Test Template",
            category=TemplateCategory.DRAMATIC,
            description="A test template",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )
        assert template.id == "test-template"
        assert template.category == TemplateCategory.DRAMATIC

    def test_invalid_scene_duration(self):
        """Test that invalid scene duration raises validation error."""
        with pytest.raises(ValidationError):
            StyleTemplate(
                id="test-template",
                name="Test Template",
                category=TemplateCategory.DRAMATIC,
                description="A test template",
                llm_provider="openai",
                image_provider="openai",
                tts_provider="elevenlabs",
                scene_duration=0,  # Invalid (must be >= 1)
            )
