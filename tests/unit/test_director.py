"""
Unit Tests for Video Director

Tests for storyboard creation functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import RewrittenScript, Scene, Storyboard, StyleTemplate, TemplateCategory
from src.stages.director import (
    DirectorError,
    VideoDirector,
    MultiVideoDirector,
    create_storyboard,
)


class TestVideoDirector:
    """Tests for VideoDirector."""

    def test_init_with_provider(self):
        """Test VideoDirector initialization with provider."""
        mock_provider = MagicMock()
        director = VideoDirector(provider=mock_provider)

        assert director.provider == mock_provider

    @pytest.mark.asyncio
    async def test_init_default_provider(self):
        """Test VideoDirector initialization with default provider."""
        with patch("src.stages.director.ProviderFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_factory.create_llm.return_value = mock_provider

            director = VideoDirector()

            assert director.provider == mock_provider

    @pytest.mark.asyncio
    async def test_create_storyboard_success(self):
        """Test successful storyboard creation."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='''{"scenes": [{"scene_number": 1, "narration": "Welcome to this journey", "visual_description": "A peaceful mountain landscape at sunrise", "duration": 5, "camera_movement": "wide shot", "mood": "peaceful"}], "total_duration": 45}'''
        )

        director = VideoDirector(provider=mock_provider)

        script = RewrittenScript(
            original_video_id="test_video",
            template_id="template1",
            title="Mountain Sunrise",
            script="This is a valid script content that is long enough to pass validation.",
            style_notes="Cinematic style",
        )

        result = await director.create_storyboard(script)

        assert result.script_id == "test_video_template1"
        assert len(result.scenes) == 1
        assert result.scenes[0].scene_number == 1
        assert result.scenes[0].narration == "Welcome to this journey"
        assert result.scenes[0].visual_description == "A peaceful mountain landscape at sunrise"
        assert result.scenes[0].duration == 5
        assert result.scenes[0].camera_movement == "wide shot"
        assert result.scenes[0].mood == "peaceful"
        assert result.total_duration == 45

    @pytest.mark.asyncio
    async def test_create_storyboard_with_template(self):
        """Test storyboard creation with style template."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"scenes": [{"scene_number": 1, "narration": "Text here", "visual_description": "Scene description here", "duration": 3, "camera_movement": "close-up", "mood": "neutral"}], "total_duration": 30}'
        )

        director = VideoDirector(provider=mock_provider)

        script = RewrittenScript(
            original_video_id="test",
            template_id="template1",
            title="Test Title Here",
            script="This is a valid script content that is long enough for this test case.",
            style_notes="Style notes",
        )

        template = StyleTemplate(
            id="template1",
            name="Test Template",
            category=TemplateCategory.CINEMATIC,
            description="Test template",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
            scene_duration=3.0,
        )

        result = await director.create_storyboard(script, template)

        assert result.script_id == "test_template1"
        # Verify the prompt includes the template's scene duration
        call_args = mock_provider.generate_text.call_args
        prompt = call_args[1]["prompt"]
        assert "~3 seconds per scene" in prompt

    @pytest.mark.asyncio
    async def test_create_storyboard_with_markdown_json(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='''```json
{
  "scenes": [
    {
      "scene_number": 1,
      "narration": "The hero stands tall",
      "visual_description": "A dramatic scene of a hero standing alone",
      "duration": 7,
      "camera_movement": "low angle",
      "mood": "dramatic"
    }
  ],
  "total_duration": 60
}
```'''
        )

        director = VideoDirector(provider=mock_provider)

        script = RewrittenScript(
            original_video_id="test",
            template_id="template1",
            title="Dramatic Scene",
            script="This is a valid script content that is long enough for this test case.",
            style_notes="Dramatic style",
        )

        result = await director.create_storyboard(script)

        assert len(result.scenes) == 1
        assert result.scenes[0].narration == "The hero stands tall"
        assert result.scenes[0].visual_description == "A dramatic scene of a hero standing alone"
        assert result.scenes[0].camera_movement == "low angle"
        assert result.scenes[0].mood == "dramatic"

    @pytest.mark.asyncio
    async def test_create_storyboard_multiple_scenes(self):
        """Test storyboard with multiple scenes."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='''{"scenes": [
                {"scene_number": 1, "narration": "Opening", "visual_description": "Opening shot of city skyline", "duration": 5, "camera_movement": "wide shot", "mood": "neutral"},
                {"scene_number": 2, "narration": "Focus", "visual_description": "Close up of main character", "duration": 4, "camera_movement": "close-up", "mood": "intense"},
                {"scene_number": 3, "narration": "Action", "visual_description": "Action sequence with fast cuts", "duration": 6, "camera_movement": "handheld", "mood": "exciting"}
            ], "total_duration": 45}'''
        )

        director = VideoDirector(provider=mock_provider)

        script = RewrittenScript(
            original_video_id="test",
            template_id="template1",
            title="City Action",
            script="This is a valid script content that is long enough for this test case.",
            style_notes="Action style",
        )

        result = await director.create_storyboard(script)

        assert len(result.scenes) == 3
        assert result.scenes[0].visual_description == "Opening shot of city skyline"
        assert result.scenes[1].camera_movement == "close-up"
        assert result.scenes[2].mood == "exciting"
        assert result.total_duration == 45

    @pytest.mark.asyncio
    async def test_create_storyboard_llm_error(self):
        """Test handling LLM provider error."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(side_effect=Exception("LLM error"))

        director = VideoDirector(provider=mock_provider)

        script = RewrittenScript(
            original_video_id="test",
            template_id="template1",
            title="Test Title",
            script="This is a valid script content that is long enough for this test case.",
            style_notes="Style",
        )

        template = StyleTemplate(
            id="template1",
            name="Test",
            category=TemplateCategory.EDUCATIONAL,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        with pytest.raises(DirectorError) as exc_info:
            await director.create_storyboard(script, template)

        assert "Failed to create storyboard" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_storyboard_invalid_json(self):
        """Test handling invalid JSON response."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(return_value="This is not valid JSON")

        director = VideoDirector(provider=mock_provider)

        script = RewrittenScript(
            original_video_id="test",
            template_id="template1",
            title="Test Title Here",
            script="This is a valid script content that is long enough for this test case.",
            style_notes="Style notes",
        )

        template = StyleTemplate(
            id="template1",
            name="Test",
            category=TemplateCategory.DOCUMENTARY,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        with pytest.raises(DirectorError) as exc_info:
            await director.create_storyboard(script, template)

        assert "Failed to parse" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_storyboard_extract_json_from_text(self):
        """Test extracting JSON from mixed text response."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='Here is the storyboard:\n{"scenes": [{"scene_number": 1, "narration": "Text", "visual_description": "Test scene description that is detailed enough", "duration": 5, "camera_movement": "static", "mood": "neutral"}], "total_duration": 30}\n\nHope this helps!'
        )

        director = VideoDirector(provider=mock_provider)

        script = RewrittenScript(
            original_video_id="test",
            template_id="template1",
            title="Test Title",
            script="This is a valid script content that is long enough for this test case.",
            style_notes="Style notes",
        )

        result = await director.create_storyboard(script)

        assert len(result.scenes) == 1
        assert result.scenes[0].visual_description == "Test scene description that is detailed enough"

    @pytest.mark.asyncio
    async def test_create_storyboard_auto_scene_number(self):
        """Test auto-assigning scene numbers when missing from response."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"scenes": [{"narration": "Text", "visual_description": "Description", "duration": 5, "camera_movement": "static", "mood": "neutral"}], "total_duration": 30}'
        )

        director = VideoDirector(provider=mock_provider)

        script = RewrittenScript(
            original_video_id="test",
            template_id="template1",
            title="Test Title",
            script="This is a valid script content that is long enough for this test case.",
            style_notes="Style notes",
        )

        result = await director.create_storyboard(script)

        assert len(result.scenes) == 1
        assert result.scenes[0].scene_number == 1  # Auto-assigned


class TestConvenienceFunction:
    """Tests for the convenience create_storyboard function."""

    @pytest.mark.asyncio
    async def test_create_storyboard_function(self):
        """Test the convenience function works."""
        with patch("src.stages.director.VideoDirector") as MockDirector:
            mock_instance = MagicMock()
            MockDirector.return_value = mock_instance

            mock_storyboard = Storyboard(
                script_id="test_template1",
                scenes=[
                    Scene(
                        scene_number=1,
                        narration="Narration text here",
                        visual_description="A detailed scene description suitable for image generation",
                        duration=5,
                        camera_movement="wide shot",
                        mood="peaceful",
                    )
                ],
                total_duration=30,
            )
            mock_instance.create_storyboard = AsyncMock(return_value=mock_storyboard)

            script = RewrittenScript(
                original_video_id="test",
                template_id="template1",
                title="Test Title Here",
                script="This is a valid script content that is long enough for this test case.",
                style_notes="Style notes",
            )

            result = await create_storyboard(script)

            MockDirector.assert_called_once()
            mock_instance.create_storyboard.assert_called_once_with(script, None)
            assert result == mock_storyboard


class TestMultiVideoDirector:
    """Tests for MultiVideoDirector."""

    def test_init(self):
        """Test MultiVideoDirector initialization."""
        mock_provider = MagicMock()
        director = MultiVideoDirector(provider=mock_provider)

        assert director is not None

    @pytest.mark.asyncio
    async def test_create_multiple_success(self):
        """Test creating storyboards for multiple scripts."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"scenes": [{"scene_number": 1, "narration": "Text", "visual_description": "A detailed scene description that works for image generation", "duration": 5, "camera_movement": "static", "mood": "neutral"}], "total_duration": 30}'
        )

        director = MultiVideoDirector(provider=mock_provider)

        scripts = {
            "vid1": RewrittenScript(
                original_video_id="vid1",
                template_id="template1",
                title="Video 1",
                script="This is a valid script content for video 1 that meets minimum length.",
                style_notes="Style",
            ),
            "vid2": RewrittenScript(
                original_video_id="vid2",
                template_id="template1",
                title="Video 2",
                script="This is a valid script content for video 2 that meets minimum length.",
                style_notes="Style",
            ),
        }

        result = await director.create_multiple(scripts)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_create_multiple_with_different_templates(self):
        """Test creating storyboards with different templates per video."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"scenes": [{"scene_number": 1, "narration": "Text", "visual_description": "A detailed scene description for image generation purposes", "duration": 5, "camera_movement": "static", "mood": "neutral"}], "total_duration": 30}'
        )

        director = MultiVideoDirector(provider=mock_provider)

        scripts = {
            "vid1": RewrittenScript(
                original_video_id="vid1",
                template_id="template1",
                title="Video 1",
                script="This is a valid script content for video 1 that meets minimum length.",
                style_notes="Style",
            ),
            "vid2": RewrittenScript(
                original_video_id="vid2",
                template_id="template2",
                title="Video 2",
                script="This is a valid script content for video 2 that meets minimum length.",
                style_notes="Style",
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

        result = await director.create_multiple_with_templates(scripts, templates)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_create_multiple_partial_failure(self):
        """Test creating storyboards when some scripts fail."""
        class BadScript:
            original_video_id = "bad"

        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"scenes": [{"scene_number": 1, "narration": "Text", "visual_description": "A detailed scene description that is long enough for this test case", "duration": 5, "camera_movement": "static", "mood": "neutral"}], "total_duration": 30}'
        )

        director = MultiVideoDirector(provider=mock_provider)

        scripts = {
            "vid1": RewrittenScript(
                original_video_id="vid1",
                template_id="template1",
                title="Video 1",
                script="This is a valid script content for testing that meets minimum length.",
                style_notes="Style",
            ),
            "vid2": BadScript(),  # This will fail
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

        result = await director.create_multiple(scripts, template)

        # Should have succeeded storyboard only
        assert "vid1" in result
        assert "vid2" not in result

    @pytest.mark.asyncio
    async def test_create_multiple_all_fail(self):
        """Test creating storyboards when all scripts fail."""
        class BadScript:
            original_video_id = "bad"

        mock_provider = MagicMock()
        director = MultiVideoDirector(provider=mock_provider)

        scripts = {
            "vid1": BadScript(),
            "vid2": BadScript(),
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

        with pytest.raises(DirectorError) as exc_info:
            await director.create_multiple(scripts, template)

        assert "Failed to create all" in str(exc_info.value)
