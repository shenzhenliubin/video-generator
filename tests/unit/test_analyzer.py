"""
Unit Tests for Content Analyzer

Tests for LLM-based content analysis functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import ContentAnalysis, ParsedContent
from src.stages.analyzer import (
    AnalysisError,
    ContentAnalyzer,
    MultiVideoAnalyzer,
    analyze_content,
)


class TestContentAnalyzer:
    """Tests for ContentAnalyzer."""

    def test_init_with_provider(self):
        """Test ContentAnalyzer initialization with provider."""
        mock_provider = MagicMock()
        analyzer = ContentAnalyzer(provider=mock_provider)

        assert analyzer.provider == mock_provider

    @pytest.mark.asyncio
    async def test_init_default_provider(self):
        """Test ContentAnalyzer initialization with default provider."""
        with patch("src.stages.analyzer.ProviderFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_factory.create_llm.return_value = mock_provider

            analyzer = ContentAnalyzer()

            assert analyzer.provider == mock_provider

    @pytest.mark.asyncio
    async def test_analyze_success(self):
        """Test successful content analysis."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(return_value='{"main_points": ["Point 1", "Point 2"], "summary": "Test summary.", "topics": ["test"], "sentiment": "neutral"}')

        analyzer = ContentAnalyzer(provider=mock_provider)

        content = ParsedContent(
            video_id="test_video",
            original_text="Original text.",
            clean_text="Clean text for testing.",
            segments=[],
            sections=[],
            language="en",
            word_count=10,
        )

        result = await analyzer.analyze(content)

        assert isinstance(result, ContentAnalysis)
        assert result.video_id == "test_video"
        assert len(result.main_points) == 2
        assert result.summary == "Test summary."
        assert result.topics == ["test"]
        assert result.sentiment == "neutral"

    @pytest.mark.asyncio
    async def test_analyze_with_markdown_json(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='''```json
{
  "main_points": ["Key point"],
  "summary": "A summary.",
  "topics": ["topic"],
  "sentiment": "positive"
}
```'''
        )

        analyzer = ContentAnalyzer(provider=mock_provider)

        content = ParsedContent(
            video_id="test",
            original_text="Text",
            clean_text="Content",
            segments=[],
            sections=[],
            language="en",
            word_count=5,
        )

        result = await analyzer.analyze(content)

        assert result.main_points == ["Key point"]
        assert result.summary == "A summary."
        assert result.sentiment == "positive"

    @pytest.mark.asyncio
    async def test_analyze_extract_json_from_text(self):
        """Test extracting JSON from mixed text response."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='Here is the analysis:\n{"main_points": ["Point"], "summary": "This is a valid summary.", "topics": ["t"], "sentiment": "neutral"}\n\nHope this helps!'
        )

        analyzer = ContentAnalyzer(provider=mock_provider)

        content = ParsedContent(
            video_id="test",
            original_text="Text",
            clean_text="Content",
            segments=[],
            sections=[],
            language="en",
            word_count=5,
        )

        result = await analyzer.analyze(content)

        assert result.main_points == ["Point"]
        assert result.summary == "This is a valid summary."

    @pytest.mark.asyncio
    async def test_analyze_truncates_long_content(self):
        """Test that long content is truncated for analysis."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"main_points": ["Point"], "summary": "This is a valid summary.", "topics": ["t"], "sentiment": "neutral"}'
        )

        analyzer = ContentAnalyzer(provider=mock_provider)

        # Create content longer than 3000 characters
        long_text = "A" * 4000
        content = ParsedContent(
            video_id="test",
            original_text=long_text,
            clean_text=long_text,
            segments=[],
            sections=[],
            language="en",
            word_count=4000,
        )

        await analyzer.analyze(content)

        # Check that the prompt was truncated
        call_args = mock_provider.generate_text.call_args
        prompt = call_args[1]["prompt"]  # keyword argument
        assert len(prompt) < len(long_text)
        assert "..." in prompt  # Should have truncation marker

    @pytest.mark.asyncio
    async def test_analyze_llm_error(self):
        """Test handling LLM provider error."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(side_effect=Exception("LLM error"))

        analyzer = ContentAnalyzer(provider=mock_provider)

        content = ParsedContent(
            video_id="test",
            original_text="Text",
            clean_text="Content",
            segments=[],
            sections=[],
            language="en",
            word_count=5,
        )

        with pytest.raises(AnalysisError) as exc_info:
            await analyzer.analyze(content)

        assert "Failed to analyze content" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_invalid_json(self):
        """Test handling invalid JSON response."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(return_value="This is not valid JSON")

        analyzer = ContentAnalyzer(provider=mock_provider)

        content = ParsedContent(
            video_id="test",
            original_text="Text",
            clean_text="Content",
            segments=[],
            sections=[],
            language="en",
            word_count=5,
        )

        with pytest.raises(AnalysisError) as exc_info:
            await analyzer.analyze(content)

        assert "Failed to parse" in str(exc_info.value)


class TestConvenienceFunction:
    """Tests for the convenience analyze_content function."""

    @pytest.mark.asyncio
    async def test_analyze_content_function(self):
        """Test the convenience function works."""
        with patch("src.stages.analyzer.ContentAnalyzer") as MockAnalyzer:
            mock_instance = MagicMock()
            MockAnalyzer.return_value = mock_instance

            mock_analysis = ContentAnalysis(
                video_id="test",
                main_points=["Point"],
                summary="This is a valid summary.",
                topics=["topic"],
            )
            mock_instance.analyze = AsyncMock(return_value=mock_analysis)

            content = ParsedContent(
                video_id="test",
                original_text="Text",
                clean_text="Content",
                segments=[],
                sections=[],
                language="en",
                word_count=5,
            )

            result = await analyze_content(content)

            # Verify ContentAnalyzer was instantiated and called
            MockAnalyzer.assert_called_once()
            mock_instance.analyze.assert_called_once_with(content)
            assert result == mock_analysis


class TestMultiVideoAnalyzer:
    """Tests for MultiVideoAnalyzer."""

    def test_init(self):
        """Test MultiVideoAnalyzer initialization."""
        mock_provider = MagicMock()
        analyzer = MultiVideoAnalyzer(provider=mock_provider)

        assert analyzer is not None

    @pytest.mark.asyncio
    async def test_analyze_multiple_success(self):
        """Test analyzing multiple contents."""
        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"main_points": ["P"], "summary": "This is a valid summary.", "topics": ["t"], "sentiment": "neutral"}'
        )

        analyzer = MultiVideoAnalyzer(provider=mock_provider)

        contents = {
            "vid1": ParsedContent(
                video_id="vid1",
                original_text="Text 1",
                clean_text="Content 1",
                segments=[],
                sections=[],
                language="en",
                word_count=5,
            ),
            "vid2": ParsedContent(
                video_id="vid2",
                original_text="Text 2",
                clean_text="Content 2",
                segments=[],
                sections=[],
                language="en",
                word_count=5,
            ),
        }

        result = await analyzer.analyze_multiple(contents)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result

    @pytest.mark.asyncio
    async def test_analyze_multiple_partial_failure(self):
        """Test analyzing when some contents fail."""
        class BadContent:
            video_id = "bad"

        mock_provider = MagicMock()
        mock_provider.generate_text = AsyncMock(
            return_value='{"main_points": ["P"], "summary": "This is a valid summary.", "topics": ["t"], "sentiment": "neutral"}'
        )

        analyzer = MultiVideoAnalyzer(provider=mock_provider)

        contents = {
            "vid1": ParsedContent(
                video_id="vid1",
                original_text="Good",
                clean_text="Good content",
                segments=[],
                sections=[],
                language="en",
                word_count=5,
            ),
            "vid2": BadContent(),  # This will fail
        }

        result = await analyzer.analyze_multiple(contents)

        # Should have succeeded content only
        assert "vid1" in result
        assert "vid2" not in result

    @pytest.mark.asyncio
    async def test_analyze_multiple_all_fail(self):
        """Test analyzing when all contents fail."""
        class BadContent:
            video_id = "bad"

        mock_provider = MagicMock()

        analyzer = MultiVideoAnalyzer(provider=mock_provider)

        contents = {
            "vid1": BadContent(),
            "vid2": BadContent(),
        }

        with pytest.raises(AnalysisError) as exc_info:
            await analyzer.analyze_multiple(contents)

        assert "Failed to analyze all" in str(exc_info.value)
