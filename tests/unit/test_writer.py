"""
Unit Tests for Content Writer

Tests for style-based content rewriting functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import ContentAnalysis, RewrittenScript, StyleTemplate, TemplateCategory
from src.stages.writer import (
    ContentWriter,
    MultiVideoWriter,
    WritingError,
    rewrite_content,
)


class TestContentWriter:
    """Tests for ContentWriter."""

    def test_init_with_provider(self):
        """Test ContentWriter initialization with provider."""
        mock_provider = MagicMock()
        writer = ContentWriter(provider=mock_provider)

        assert writer.provider == mock_provider

    @pytest.mark.asyncio
    async def test_init_default_provider(self):
        """Test ContentWriter initialization with default provider."""
        with patch("src.stages.writer.ProviderFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_factory.create_llm.return_value = mock_provider

            writer = ContentWriter()

            assert writer.provider == mock_provider

    @pytest.mark.asyncio
    async def test_rewrite_success(self):
        """Test successful content rewriting."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"title": "Amazing Discovery", "script": "This is the full script content that meets the minimum length requirement.", "style_notes": "Applied dramatic tone"}'
        )

        writer = ContentWriter(provider=mock_provider)

        analysis = ContentAnalysis(
            video_id="test_video",
            main_points=["Point 1", "Point 2"],
            summary="A test summary of the content.",
            topics=["science", "discovery"],
            sentiment="positive",
        )

        template = StyleTemplate(
            id="test_template",
            name="Test Template",
            category=TemplateCategory.DRAMATIC,
            description="A test template",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        result = await writer.rewrite(analysis, template)

        assert isinstance(result, RewrittenScript)
        assert result.original_video_id == "test_video"
        assert result.template_id == "test_template"
        assert result.title == "Amazing Discovery"
        assert "full script content" in result.script
        assert result.style_notes == "Applied dramatic tone"

    @pytest.mark.asyncio
    async def test_rewrite_with_custom_system_prompt(self):
        """Test rewriting with custom system prompt in template."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"title": "Test Title Here", "script": "This is a script that is long enough to pass validation.", "style_notes": "Custom style"}'
        )

        writer = ContentWriter(provider=mock_provider)

        analysis = ContentAnalysis(
            video_id="test",
            main_points=["Point"],
            summary="A valid summary for testing.",
            topics=["topic"],
        )

        template = StyleTemplate(
            id="custom",
            name="Custom",
            category=TemplateCategory.EDUCATIONAL,
            description="Custom template with system prompt",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
            system_prompt="You are a custom writer. Be creative.",
        )

        result = await writer.rewrite(analysis, template)

        assert result.title == "Test Title Here"

    @pytest.mark.asyncio
    async def test_rewrite_with_markdown_json(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='''```json
{
  "title": "Epic Story",
  "script": "Once upon a time there was a journey that changed everything...",
  "style_notes": "Cinematic style applied"
}
```'''
        )

        writer = ContentWriter(provider=mock_provider)

        analysis = ContentAnalysis(
            video_id="test",
            main_points=["Point"],
            summary="A valid summary for the test.",
            topics=["topic"],
        )

        template = StyleTemplate(
            id="test",
            name="Test",
            category=TemplateCategory.CINEMATIC,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        result = await writer.rewrite(analysis, template)

        assert result.title == "Epic Story"
        assert "journey that changed" in result.script

    @pytest.mark.asyncio
    async def test_rewrite_plain_text_fallback(self):
        """Test fallback extraction from plain text response."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value="Epic Discovery\n\nThis is the full script content extracted from plain text and it is long enough."
        )

        writer = ContentWriter(provider=mock_provider)

        analysis = ContentAnalysis(
            video_id="test",
            main_points=["Point"],
            summary="A valid summary for testing.",
            topics=["topic"],
        )

        template = StyleTemplate(
            id="test",
            name="Test",
            category=TemplateCategory.DOCUMENTARY,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        result = await writer.rewrite(analysis, template)

        assert result.title == "Epic Discovery"
        assert "script content extracted from plain text" in result.script

    @pytest.mark.asyncio
    async def test_rewrite_llm_error(self):
        """Test handling LLM provider error."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(side_effect=Exception("LLM error"))

        writer = ContentWriter(provider=mock_provider)

        analysis = ContentAnalysis(
            video_id="test",
            main_points=["Point"],
            summary="A valid summary for test.",
            topics=["topic"],
        )

        template = StyleTemplate(
            id="test",
            name="Test",
            category=TemplateCategory.EDUCATIONAL,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        with pytest.raises(WritingError) as exc_info:
            await writer.rewrite(analysis, template)

        assert "Failed to rewrite content" in str(exc_info.value)

    def test_get_style_prompt_predefined(self):
        """Test getting predefined style prompts."""
        mock_provider = MagicMock()
        writer = ContentWriter(provider=mock_provider)

        template = StyleTemplate(
            id="test",
            name="Dramatic",
            category=TemplateCategory.DRAMATIC,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        prompt = writer._get_style_prompt(template)

        assert "dramatic storyteller" in prompt.lower()

    def test_get_style_prompt_custom(self):
        """Test custom system prompt takes precedence."""
        mock_provider = MagicMock()
        writer = ContentWriter(provider=mock_provider)

        template = StyleTemplate(
            id="test",
            name="Custom",
            category=TemplateCategory.DRAMATIC,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
            system_prompt="Custom system prompt here.",
        )

        prompt = writer._get_style_prompt(template)

        assert prompt == "Custom system prompt here."

    def test_get_style_prompt_unknown_category(self):
        """Test unknown category falls back to documentary."""
        mock_provider = MagicMock()
        writer = ContentWriter(provider=mock_provider)

        # Create template with a valid category, then modify to invalid value
        # This tests the fallback logic when an unknown category is passed
        template = StyleTemplate(
            id="test",
            name="Unknown",
            category=TemplateCategory.DOCUMENTARY,  # Valid enum value
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        # Manually set category to an invalid string to test fallback
        template.category = "unknown_category"  # type: ignore

        prompt = writer._get_style_prompt(template)

        # Should fall back to documentary
        assert "documentary" in prompt.lower()


class TestConvenienceFunction:
    """Tests for the convenience rewrite_content function."""

    @pytest.mark.asyncio
    async def test_rewrite_content_function(self):
        """Test the convenience function works."""
        with patch("src.stages.writer.ContentWriter") as MockWriter:
            mock_instance = MagicMock()
            MockWriter.return_value = mock_instance

            mock_script = RewrittenScript(
                original_video_id="test",
                template_id="template1",
                title="Test Title Here",
                script="A valid script content that meets minimum length requirements.",
                style_notes="Style notes",
            )
            mock_instance.rewrite = AsyncMock(return_value=mock_script)

            analysis = ContentAnalysis(
                video_id="test",
                main_points=["Point"],
                summary="A valid summary for testing purposes.",
                topics=["topic"],
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

            result = await rewrite_content(analysis, template)

            MockWriter.assert_called_once()
            mock_instance.rewrite.assert_called_once_with(analysis, template)
            assert result == mock_script


class TestMultiVideoWriter:
    """Tests for MultiVideoWriter."""

    def test_init(self):
        """Test MultiVideoWriter initialization."""
        mock_provider = MagicMock()
        writer = MultiVideoWriter(provider=mock_provider)

        assert writer is not None

    @pytest.mark.asyncio
    async def test_rewrite_multiple_success(self):
        """Test rewriting multiple analyses."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"title": "T", "script": "Script content here that is long enough for validation.", "style_notes": "Notes"}'
        )

        writer = MultiVideoWriter(provider=mock_provider)

        analyses = {
            "vid1": ContentAnalysis(
                video_id="vid1",
                main_points=["P1"],
                summary="Summary for video 1 is valid.",
                topics=["t1"],
            ),
            "vid2": ContentAnalysis(
                video_id="vid2",
                main_points=["P2"],
                summary="Summary for video 2 is valid.",
                topics=["t2"],
            ),
        }

        template = StyleTemplate(
            id="template1",
            name="Test",
            category=TemplateCategory.NEWS,
            description="Test",
            llm_provider="openai",
            image_provider="openai",
            tts_provider="elevenlabs",
        )

        result = await writer.rewrite_multiple(analyses, template)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_rewrite_multiple_with_different_templates(self):
        """Test rewriting with different templates per video."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"title": "T", "script": "Script content that is definitely long enough for this test.", "style_notes": "Notes"}'
        )

        writer = MultiVideoWriter(provider=mock_provider)

        analyses = {
            "vid1": ContentAnalysis(
                video_id="vid1",
                main_points=["P1"],
                summary="Valid summary for video 1.",
                topics=["t1"],
            ),
            "vid2": ContentAnalysis(
                video_id="vid2",
                main_points=["P2"],
                summary="Valid summary for video 2.",
                topics=["t2"],
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

        result = await writer.rewrite_multiple_with_templates(analyses, templates)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_rewrite_multiple_partial_failure(self):
        """Test rewriting when some analyses fail."""
        class BadAnalysis:
            video_id = "bad"

        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"title": "T", "script": "Script content that is long enough for this test case.", "style_notes": "Notes"}'
        )

        writer = MultiVideoWriter(provider=mock_provider)

        analyses = {
            "vid1": ContentAnalysis(
                video_id="vid1",
                main_points=["P1"],
                summary="Valid summary for testing.",
                topics=["t1"],
            ),
            "vid2": BadAnalysis(),  # This will fail
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

        result = await writer.rewrite_multiple(analyses, template)

        # Should have succeeded analysis only
        assert "vid1" in result
        assert "vid2" not in result

    @pytest.mark.asyncio
    async def test_rewrite_multiple_all_fail(self):
        """Test rewriting when all analyses fail."""
        class BadAnalysis:
            video_id = "bad"

        mock_provider = MagicMock()
        writer = MultiVideoWriter(provider=mock_provider)

        analyses = {
            "vid1": BadAnalysis(),
            "vid2": BadAnalysis(),
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

        with pytest.raises(WritingError) as exc_info:
            await writer.rewrite_multiple(analyses, template)

        assert "Failed to rewrite all" in str(exc_info.value)
