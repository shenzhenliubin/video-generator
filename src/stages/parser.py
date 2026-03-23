"""
Parser Stage - Subtitle Cleaning and Segmentation

Processes raw YouTube subtitle data into clean, structured content.

Features:
- Remove YouTube artifacts (music descriptions, sound effects)
- Clean up text formatting
- Segment content into logical sections
- Extract key phrases and topics
"""

import re
from typing import Any

from src.core.models import ParsedContent, Transcript


class SubtitleParser:
    """
    Parse and clean YouTube subtitle data.

    Processes raw transcripts into structured content suitable for AI analysis.
    """

    # Patterns to remove from subtitles
    MUSIC_PATTERNS = [
        r"\[music\]",
        r"\[Music\]",
        r"\[background music\]",
        r"\(music\)",
        r"\(Music\)",
        r"\[no speech\]",
        r"\[silence\]",
    ]

    SOUND_EFFECT_PATTERNS = [
        r"\[laughs?\]",
        r"\[laughing\]",
        r"\[applause\]",
        r"\[cheers?\]",
        r"\[audio\]",
        r"\[video\]",
    ]

    # Patterns for cleaning
    WHITESPACE_PATTERN = re.compile(r"\s+")
    PUNCTUATION_SPACE_PATTERN = re.compile(r"\s+([.,!?;:])")
    BRACKET_PATTERN = re.compile(r"\[[^\]]*\]")

    async def parse(self, transcript: Transcript) -> ParsedContent:
        """
        Parse transcript into clean, structured content.

        Args:
            transcript: Raw transcript from Fetcher stage

        Returns:
            ParsedContent with cleaned text and metadata
        """
        # Clean the full text
        clean_text = self._clean_text(transcript.raw_text)

        # Parse segments
        parsed_segments = self._parse_segments(transcript.segments)

        # Extract sections (paragraphs based on timing gaps)
        sections = self._segment_into_sections(
            transcript.segments, gap_threshold=3.0
        )

        return ParsedContent(
            video_id=transcript.video_id,
            original_text=transcript.raw_text,
            clean_text=clean_text,
            segments=parsed_segments,
            sections=sections,
            language=transcript.language,
            word_count=self._count_words(clean_text),
        )

    def _clean_text(self, text: str) -> str:
        """
        Clean raw subtitle text.

        Args:
            text: Raw subtitle text

        Returns:
            Cleaned text with artifacts removed
        """
        # Remove music descriptions
        for pattern in self.MUSIC_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove sound effects
        for pattern in self.SOUND_EFFECT_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove remaining bracketed content
        text = self.BRACKET_PATTERN.sub("", text)

        # Fix punctuation spacing
        text = self.PUNCTUATION_SPACE_PATTERN.sub(r"\1", text)

        # Normalize whitespace
        text = self.WHITESPACE_PATTERN.sub(" ", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _parse_segments(self, segments: list[Any]) -> list[dict[str, Any]]:
        """
        Parse individual segments with cleaned text.

        Args:
            segments: Raw transcript segments (Pydantic models or dicts)

        Returns:
            List of parsed segments with cleaned text
        """
        parsed = []

        for segment in segments:
            # Handle both Pydantic models and dictionaries
            if hasattr(segment, "text"):
                text = segment.text
                start = segment.start
                duration = segment.duration
            else:
                text = segment.get("text", "")
                start = segment.get("start", 0)
                duration = segment.get("duration", 0)

            clean_seg_text = self._clean_segment_text(text)

            # Skip empty segments after cleaning
            if not clean_seg_text:
                continue

            parsed.append(
                {
                    "text": clean_seg_text,
                    "start": start,
                    "duration": duration,
                }
            )

        return parsed

    def _clean_segment_text(self, text: str) -> str:
        """
        Clean individual segment text.

        Args:
            text: Raw segment text

        Returns:
            Cleaned segment text
        """
        # Remove music/sound patterns
        for pattern in self.MUSIC_PATTERNS + self.SOUND_EFFECT_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove other bracketed content
        text = self.BRACKET_PATTERN.sub("", text)

        # Clean up whitespace
        text = self.WHITESPACE_PATTERN.sub(" ", text).strip()

        return text

    def _segment_into_sections(
        self,
        segments: list[Any],
        gap_threshold: float = 3.0,
    ) -> list[dict[str, Any]]:
        """
        Segment transcript into logical sections based on timing gaps.

        Args:
            segments: Parsed transcript segments (Pydantic models or dicts)
            gap_threshold: Minimum gap (seconds) to create a new section

        Returns:
            List of sections with combined text and timing info
        """
        if not segments:
            return []

        sections = []
        current_section = {
            "segments": [],
            "start_time": self._get_start_time(segments[0]),
        }

        for i, segment in enumerate(segments):
            # Check for gap
            if i > 0:
                prev_end = self._get_start_time(segments[i - 1]) + self._get_duration(segments[i - 1])
                current_start = self._get_start_time(segment)
                gap = current_start - prev_end

                # If gap exceeds threshold, finalize current section
                if gap > gap_threshold and current_section["segments"]:
                    # Save current section
                    sections.append(self._finalize_section(current_section))
                    # Start new section
                    current_section = {
                        "segments": [],
                        "start_time": self._get_start_time(segment),
                    }

            current_section["segments"].append(segment)

        # Don't forget the last section
        if current_section["segments"]:
            sections.append(self._finalize_section(current_section))

        return sections

    def _get_start_time(self, segment: Any) -> float:
        """Get start time from segment (Pydantic model or dict)."""
        if hasattr(segment, "start"):
            return segment.start
        return segment.get("start", 0)

    def _get_duration(self, segment: Any) -> float:
        """Get duration from segment (Pydantic model or dict)."""
        if hasattr(segment, "duration"):
            return segment.duration
        return segment.get("duration", 0)

    def _get_text(self, segment: Any) -> str:
        """Get text from segment (Pydantic model or dict)."""
        if hasattr(segment, "text"):
            return segment.text
        return segment.get("text", "")

    def _finalize_section(self, section_data: dict[str, Any]) -> dict[str, Any]:
        """
        Finalize a section by combining its segments.

        Args:
            section_data: Section data with segments list

        Returns:
            Finalized section with combined text and timing
        """
        segments = section_data["segments"]

        # Combine text
        text = " ".join(self._get_text(seg) for seg in segments)

        # Calculate timing
        start_time = section_data["start_time"]
        end_time = self._get_start_time(segments[-1]) + self._get_duration(segments[-1])
        duration = end_time - start_time

        return {
            "text": text,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "segment_count": len(segments),
        }

    def _count_words(self, text: str) -> int:
        """
        Count words in text.

        Args:
            text: Text to count

        Returns:
            Word count
        """
        # Split by whitespace and count non-empty tokens
        words = text.split()
        return len([w for w in words if w])


# Convenience function for backward compatibility
async def parse_subtitles(transcript: Transcript) -> ParsedContent:
    """
    Parse subtitle transcript into clean content.

    This is a convenience function that maintains backward compatibility
    with the original parser.py design.

    Args:
        transcript: Raw transcript from Fetcher stage

    Returns:
        ParsedContent with cleaned and structured text
    """
    parser = SubtitleParser()
    return await parser.parse(transcript)


# Batch parsing for multiple transcripts
class MultiVideoParser:
    """
    Parse subtitles for multiple videos.

    Processes multiple transcripts efficiently.
    """

    def __init__(self):
        """Initialize multi-video parser."""
        self._parser = SubtitleParser()

    def parse_multiple(
        self,
        transcripts: dict[str, Transcript],
    ) -> dict[str, ParsedContent]:
        """
        Parse multiple transcripts.

        Args:
            transcripts: Dictionary mapping video_id to Transcript

        Returns:
            Dictionary mapping video_id to ParsedContent
        """
        results = {}

        for video_id, transcript in transcripts.items():
            try:
                parsed = self._parser.parse(transcript)
                results[video_id] = parsed
            except Exception as e:
                # Log error but continue with other videos
                print(f"Error parsing transcript for {video_id}: {e}")

        return results
