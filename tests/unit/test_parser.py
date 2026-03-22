"""
Unit Tests for Subtitle Parser

Tests for subtitle cleaning and segmentation functionality.
"""

import pytest

from src.core.models import ParsedContent, Transcript, TranscriptSegment
from src.stages.parser import (
    MultiVideoParser,
    SubtitleParser,
    parse_subtitles,
)


class TestSubtitleParser:
    """Tests for SubtitleParser."""

    def test_init(self):
        """Test SubtitleParser initialization."""
        parser = SubtitleParser()
        assert parser is not None

    def test_clean_text_music_patterns(self):
        """Test removing music descriptions."""
        parser = SubtitleParser()

        text = "Hello [music] world [Music] test"
        result = parser._clean_text(text)

        assert "[music]" not in result.lower()
        assert result == "Hello world test"

    def test_clean_text_sound_effects(self):
        """Test removing sound effect descriptions."""
        parser = SubtitleParser()

        text = "Hello [laughter] world [applause] test"
        result = parser._clean_text(text)

        assert "[laughter]" not in result.lower()
        assert "[applause]" not in result.lower()
        assert result == "Hello world test"

    def test_clean_text_brackets(self):
        """Test removing bracketed content."""
        parser = SubtitleParser()

        text = "Hello [upbeat music plays] world [video fades] test"
        result = parser._clean_text(text)

        assert "[upbeat music plays]" not in result
        assert "[video fades]" not in result
        assert result == "Hello world test"

    def test_clean_text_punctuation_spacing(self):
        """Test fixing punctuation spacing."""
        parser = SubtitleParser()

        text = "Hello world , this is a test . Great !"
        result = parser._clean_text(text)

        assert result == "Hello world, this is a test. Great!"

    def test_clean_text_whitespace(self):
        """Test normalizing whitespace."""
        parser = SubtitleParser()

        text = "Hello    world\t\ttest  \n\n  end"
        result = parser._clean_text(text)

        assert result == "Hello world test end"

    def test_parse_segments(self):
        """Test parsing transcript segments."""
        parser = SubtitleParser()

        segments = [
            {"text": "Hello [music] world", "start": 0.0, "duration": 1.0},
            {"text": "Test segment", "start": 1.0, "duration": 1.0},
        ]

        result = parser._parse_segments(segments)

        assert len(result) == 2
        assert result[0]["text"] == "Hello world"
        assert result[1]["text"] == "Test segment"

    def test_parse_segments_empty_after_cleaning(self):
        """Test segments that become empty after cleaning are skipped."""
        parser = SubtitleParser()

        segments = [
            {"text": "[music]", "start": 0.0, "duration": 1.0},
            {"text": "Real text", "start": 1.0, "duration": 1.0},
        ]

        result = parser._parse_segments(segments)

        assert len(result) == 1
        assert result[0]["text"] == "Real text"

    def test_segment_into_sections(self):
        """Test segmenting transcript into sections based on gaps."""
        parser = SubtitleParser()

        segments = [
            {"text": "First", "start": 0.0, "duration": 1.0},
            {"text": "Second", "start": 1.0, "duration": 1.0},
            # 5 second gap
            {"text": "Third", "start": 7.0, "duration": 1.0},
            {"text": "Fourth", "start": 8.0, "duration": 1.0},
        ]

        result = parser._segment_into_sections(segments, gap_threshold=3.0)

        assert len(result) == 2
        assert result[0]["text"] == "First Second"
        assert result[1]["text"] == "Third Fourth"

    def test_count_words(self):
        """Test word counting."""
        parser = SubtitleParser()

        text = "Hello world test"
        result = parser._count_words(text)

        assert result == 3

    def test_count_words_empty(self):
        """Test word counting with empty text."""
        parser = SubtitleParser()

        text = ""
        result = parser._count_words(text)

        assert result == 0

    def test_parse_full_transcript(self):
        """Test parsing a full transcript."""
        parser = SubtitleParser()

        transcript = Transcript(
            video_id="test_video",
            raw_text="Hello [music] world. Test [laughter] content.",
            segments=[
                TranscriptSegment(text="Hello [music] world.", start=0.0, duration=2.0),
                TranscriptSegment(text="Test [laughter] content.", start=3.0, duration=2.0),
            ],
            language="en",
        )

        result = parser.parse(transcript)

        assert isinstance(result, ParsedContent)
        assert result.video_id == "test_video"
        assert "[music]" not in result.clean_text
        assert "[laughter]" not in result.clean_text
        assert result.word_count > 0
        assert len(result.segments) == 2


class TestConvenienceFunction:
    """Tests for the convenience parse_subtitles function."""

    def test_parse_subtitles_function(self):
        """Test the convenience function works."""
        transcript = Transcript(
            video_id="test",
            raw_text="Hello [music] world.",
            segments=[
                TranscriptSegment(text="Hello [music] world.", start=0.0, duration=1.0),
            ],
            language="en",
        )

        result = parse_subtitles(transcript)

        assert isinstance(result, ParsedContent)
        assert result.video_id == "test"
        assert "[music]" not in result.clean_text


class TestMultiVideoParser:
    """Tests for MultiVideoParser."""

    def test_init(self):
        """Test MultiVideoParser initialization."""
        parser = MultiVideoParser()
        assert parser is not None

    def test_parse_multiple(self):
        """Test parsing multiple transcripts."""
        parser = MultiVideoParser()

        transcripts = {
            "vid1": Transcript(
                video_id="vid1",
                raw_text="Hello [music] world.",
                segments=[
                    TranscriptSegment(text="Hello [music] world.", start=0.0, duration=1.0),
                ],
                language="en",
            ),
            "vid2": Transcript(
                video_id="vid2",
                raw_text="Test [laughter] content.",
                segments=[
                    TranscriptSegment(text="Test [laughter] content.", start=0.0, duration=1.0),
                ],
                language="en",
            ),
        }

        result = parser.parse_multiple(transcripts)

        assert len(result) == 2
        assert "vid1" in result
        assert "vid2" in result
        assert result["vid1"].clean_text == "Hello world."
        assert result["vid2"].clean_text == "Test content."

    def test_parse_multiple_partial_failure(self):
        """Test parsing when some transcripts fail."""
        parser = MultiVideoParser()

        # Create a mock that raises an error for vid2
        class BadTranscript:
            video_id = "bad"

        transcripts = {
            "vid1": Transcript(
                video_id="vid1",
                raw_text="Good content.",
                segments=[
                    TranscriptSegment(text="Good content.", start=0.0, duration=1.0),
                ],
                language="en",
            ),
            "vid2": BadTranscript(),  # This will fail
        }

        result = parser.parse_multiple(transcripts)

        # Should have succeeded video only
        assert "vid1" in result
        assert "vid2" not in result
