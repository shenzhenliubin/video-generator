"""
Unit Tests for Subtitle Fetcher

Tests for YouTube subtitle downloading functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import Transcript, TranscriptSegment
from src.stages.fetcher import (
    MultiVideoFetcher,
    SubtitleFetchError,
    SubtitleFetcher,
    fetch_subtitles,
)
from youtube_transcript_api import NoTranscriptFound


class TestSubtitleFetcher:
    """Tests for SubtitleFetcher."""

    def test_init(self):
        """Test SubtitleFetcher initialization."""
        fetcher = SubtitleFetcher()
        assert fetcher._api is not None

    @pytest.mark.asyncio
    async def test_fetch_subtitles_success(self):
        """Test successful subtitle fetch."""
        fetcher = SubtitleFetcher()

        # Mock transcript data
        mock_transcript_data = [
            {"text": "Hello world", "start": 0.0, "duration": 1.0},
            {"text": "This is a test", "start": 1.0, "duration": 2.0},
        ]

        with patch.object(
            fetcher, "_fetch_subtitles_sync", return_value=mock_transcript_data
        ):
            result = await fetcher.fetch_subtitles("test_video_id")

            # Verify result
            assert isinstance(result, Transcript)
            assert result.video_id == "test_video_id"
            assert result.raw_text == "Hello world This is a test"
            assert len(result.segments) == 2
            assert result.segments[0].text == "Hello world"
            assert result.segments[0].start == 0.0
            assert result.segments[0].duration == 1.0
            assert result.language == "en"

    @pytest.mark.asyncio
    async def test_fetch_subtitles_not_found(self):
        """Test subtitle fetch when no subtitles available."""
        fetcher = SubtitleFetcher()

        # Create NoTranscriptFound with required arguments
        error = NoTranscriptFound(
            video_id="no_subs_video",
            requested_language_codes=None,
            transcript_data=[]
        )

        with patch.object(
            fetcher, "_fetch_subtitles_sync", side_effect=error
        ):
            with pytest.raises(SubtitleFetchError) as exc_info:
                await fetcher.fetch_subtitles("no_subs_video")

            assert "No subtitles found" in str(exc_info.value)
            assert "no_subs_video" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_subtitles_with_languages(self):
        """Test subtitle fetch with language preference."""
        fetcher = SubtitleFetcher()
        mock_data = [{"text": "Hola", "start": 0.0, "duration": 1.0}]

        with patch.object(
            fetcher,
            "_fetch_subtitles_sync",
            return_value=mock_data,
        ) as mock_fetch:
            await fetcher.fetch_subtitles("test_id", languages=["es", "en"])

            # Verify languages were passed
            mock_fetch.assert_called_once_with("test_id", ["es", "en"])

    @pytest.mark.asyncio
    async def test_fetch_subtitles_api_error(self):
        """Test subtitle fetch with API error."""
        fetcher = SubtitleFetcher()

        with patch.object(
            fetcher, "_fetch_subtitles_sync", side_effect=Exception("Network error")
        ):
            with pytest.raises(SubtitleFetchError) as exc_info:
                await fetcher.fetch_subtitles("error_video")

            assert "Failed to fetch subtitles" in str(exc_info.value)

    def test_extract_raw_text(self):
        """Test raw text extraction from segments."""
        data = [
            {"text": "First", "start": 0.0, "duration": 1.0},
            {"text": "Second", "start": 1.0, "duration": 1.0},
            {"text": "Third", "start": 2.0, "duration": 1.0},
        ]

        result = SubtitleFetcher._extract_raw_text(data)
        assert result == "First Second Third"

    def test_detect_language(self):
        """Test language detection (placeholder)."""
        data = [{"text": "Hello", "start": 0.0, "duration": 1.0}]
        result = SubtitleFetcher._detect_language(data)
        assert result == "en"  # Default placeholder

    @pytest.mark.asyncio
    async def test_fetch_available_languages(self):
        """Test getting available languages for a video."""
        fetcher = SubtitleFetcher()

        # Mock transcript list - patch at module level
        mock_transcript = MagicMock()
        mock_transcript.language_code = "en"

        with patch("youtube_transcript_api.YouTubeTranscriptApi.list", return_value=[mock_transcript]):
            languages = await fetcher.fetch_available_languages("test_id")

            assert languages == ["en"]

    @pytest.mark.asyncio
    async def test_fetch_available_languages_fallback(self):
        """Test language fetch falls back to default on error."""
        fetcher = SubtitleFetcher()

        with patch("youtube_transcript_api.YouTubeTranscriptApi.list", side_effect=Exception("API Error")):
            languages = await fetcher.fetch_available_languages("test_id")

            assert languages == ["en"]  # Fallback


class TestMultiVideoFetcher:
    """Tests for MultiVideoFetcher."""

    def test_init(self):
        """Test MultiVideoFetcher initialization."""
        fetcher = MultiVideoFetcher(max_concurrent=5)
        assert fetcher.max_concurrent == 5
        assert fetcher._fetcher is not None

    @pytest.mark.asyncio
    async def test_fetch_multiple_success(self):
        """Test fetching subtitles for multiple videos."""
        fetcher = MultiVideoFetcher(max_concurrent=2)

        mock_transcript = Transcript(
            video_id="test",
            raw_text="Test content",
            segments=[
                TranscriptSegment(text="Test", start=0.0, duration=1.0)
            ],
            language="en",
        )

        with patch.object(
            fetcher._fetcher, "fetch_subtitles", return_value=mock_transcript
        ):
            results = await fetcher.fetch_multiple(["vid1", "vid2", "vid3"])

            assert len(results) == 3
            assert "vid1" in results
            assert "vid2" in results
            assert "vid3" in results

    @pytest.mark.asyncio
    async def test_fetch_multiple_partial_failure(self):
        """Test fetching when some videos fail."""
        fetcher = MultiVideoFetcher(max_concurrent=2)

        mock_transcript = Transcript(
            video_id="good",
            raw_text="Good content",
            segments=[
                TranscriptSegment(text="Good", start=0.0, duration=1.0)
            ],
            language="en",
        )

        async def side_effect(video_id, languages=None):
            if video_id == "bad":
                raise SubtitleFetchError("No subs")
            return mock_transcript

        with patch.object(
            fetcher._fetcher, "fetch_subtitles", side_effect=side_effect
        ):
            results = await fetcher.fetch_multiple(["good", "bad"])

            # Should have succeeded video only
            assert "good" in results
            assert "bad" not in results

    @pytest.mark.asyncio
    async def test_fetch_multiple_all_fail(self):
        """Test fetching when all videos fail."""
        fetcher = MultiVideoFetcher()

        with patch.object(
            fetcher._fetcher,
            "fetch_subtitles",
            side_effect=SubtitleFetchError("All failed"),
        ):
            with pytest.raises(SubtitleFetchError) as exc_info:
                await fetcher.fetch_multiple(["vid1", "vid2"])

            assert "Failed to fetch subtitles for all" in str(exc_info.value)


class TestConvenienceFunction:
    """Tests for the convenience fetch_subtitles function."""

    @pytest.mark.asyncio
    async def test_fetch_subtitles_function(self):
        """Test the convenience function works."""
        from src.stages.fetcher import fetch_subtitles

        with patch("src.stages.fetcher.SubtitleFetcher") as MockFetcher:
            mock_instance = AsyncMock()
            MockFetcher.return_value = mock_instance

            mock_transcript = Transcript(
                video_id="test",
                raw_text="Test",
                segments=[
                    TranscriptSegment(text="Test", start=0.0, duration=1.0)
                ],
                language="en",
            )
            mock_instance.fetch_subtitles.return_value = mock_transcript

            result = await fetch_subtitles("test_id", ["en"])

            # Verify SubtitleFetcher was instantiated and called
            MockFetcher.assert_called_once()
            mock_instance.fetch_subtitles.assert_called_once_with("test_id", ["en"])
            assert result == mock_transcript
