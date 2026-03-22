"""
Fetcher Stage - Subtitle Download

Downloads subtitle files for YouTube videos using youtube-transcript-api.

Features:
- Fetch subtitles for a YouTube video
- Support both manual and auto-generated subtitles
- Handle multiple languages
- Convert to Transcript model
- Error handling for missing subtitles
"""

import asyncio
from typing import Any

from youtube_transcript_api import (
    NoTranscriptFound,
    YouTubeTranscriptApi,
)

from src.core.models import Transcript, TranscriptSegment


class SubtitleFetchError(Exception):
    """Raised when subtitle fetching fails."""
    pass


class SubtitleFetcher:
    """
    Fetches subtitles from YouTube videos.

    Handles various subtitle formats and languages.
    """

    def __init__(self):
        """Initialize subtitle fetcher."""
        self._api = YouTubeTranscriptApi()

    async def fetch_subtitles(
        self,
        video_id: str,
        languages: list[str] | None = None,
    ) -> Transcript:
        """
        Fetch subtitles for a YouTube video.

        Args:
            video_id: YouTube video ID (11 characters, e.g., "dQw4w9WgXcQ")
            languages: Preferred language codes (e.g., ['en', 'es']).
                     If None, fetches available subtitles.

        Returns:
            Transcript with segmented text and metadata

        Raises:
            SubtitleFetchError: If subtitles are not available or fetching fails
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            # Fetch transcript data
            transcript_data = await loop.run_in_executor(
                None,
                self._fetch_subtitles_sync,
                video_id,
                languages,
            )

            # Convert to Transcript model
            return Transcript(
                video_id=video_id,
                raw_text=self._extract_raw_text(transcript_data),
                segments=[
                    TranscriptSegment(
                        text=item["text"],
                        start=item["start"],
                        duration=item["duration"],
                    )
                    for item in transcript_data
                ],
                language=self._detect_language(transcript_data),
            )

        except NoTranscriptFound:
            raise SubtitleFetchError(
                f"No subtitles found for video {video_id}. "
                "The video may not have subtitles enabled."
            )
        except Exception as e:
            raise SubtitleFetchError(
                f"Failed to fetch subtitles for video {video_id}: {e}"
            ) from e

    def _fetch_subtitles_sync(
        self,
        video_id: str,
        languages: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Synchronous wrapper for youtube-transcript-api.

        Args:
            video_id: YouTube video ID
            languages: Language preferences

        Returns:
            List of transcript segments
        """
        if languages:
            return self._api.get_transcript(video_id, languages=languages)
        else:
            return self._api.get_transcript(video_id)

    @staticmethod
    def _extract_raw_text(transcript_data: list[dict]) -> str:
        """
        Extract full text from transcript segments.

        Args:
            transcript_data: List of transcript segments

        Returns:
            Concatenated text
        """
        return " ".join(item["text"] for item in transcript_data)

    @staticmethod
    def _detect_language(transcript_data: list[dict]) -> str:
        """
        Detect language from transcript metadata.

        Note: youtube-transcript-api doesn't provide language info directly.
        This is a placeholder that could be enhanced with language detection.

        Args:
            transcript_data: List of transcript segments

        Returns:
            Detected language code (defaults to 'en')
        """
        # TODO: Implement proper language detection
        # For now, default to English
        return "en"

    async def fetch_available_languages(
        self,
        video_id: str,
    ) -> list[str]:
        """
        Get list of available subtitle languages for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            List of available language codes
        """
        try:
            loop = asyncio.get_event_loop()
            # Try to fetch transcript list to detect available languages
            transcript_list = await loop.run_in_executor(
                None,
                self._api.list,
                video_id,
            )
            # Extract unique languages from transcript metadata
            languages = []
            for transcript in transcript_list:
                lang_code = transcript.language_code
                if lang_code and lang_code not in languages:
                    languages.append(lang_code)
            return languages

        except Exception:
            # If we can't list transcripts, return common languages
            # and let the fetch attempt determine availability
            return ["en"]


# Convenience function for backward compatibility
async def fetch_subtitles(
    video_id: str,
    languages: list[str] | None = None,
) -> Transcript:
    """
    Fetch subtitles for a YouTube video.

    This is a convenience function that maintains backward compatibility
    with the original fetcher.py design.

    Args:
        video_id: YouTube video ID
        languages: Preferred language codes

    Returns:
        Transcript with segmented text

    Raises:
        SubtitleFetchError: If subtitles are not available
    """
    fetcher = SubtitleFetcher()
    return await fetcher.fetch_subtitles(video_id, languages)


# Batch fetching for multiple videos
class MultiVideoFetcher:
    """
    Fetch subtitles for multiple videos efficiently.

    Manages concurrent fetching with limits.
    """

    def __init__(self, max_concurrent: int = 3):
        """
        Initialize multi-video fetcher.

        Args:
            max_concurrent: Maximum number of concurrent fetches
        """
        self.max_concurrent = max_concurrent
        self._fetcher = SubtitleFetcher()

    async def fetch_multiple(
        self,
        video_ids: list[str],
        languages: list[str] | None = None,
    ) -> dict[str, Transcript]:
        """
        Fetch subtitles for multiple videos concurrently.

        Args:
            video_ids: List of YouTube video IDs
            languages: Preferred language codes

        Returns:
            Dictionary mapping video_id to Transcript.
            Videos without subtitles are skipped.

        Raises:
            SubtitleFetchError: Only raised if ALL videos fail.
        """
        results = {}
        errors = []

        # Create async tasks for each video
        async def fetch_and_store(video_id: str):
            try:
                transcript = await self._fetcher.fetch_subtitles(video_id, languages)
                results[video_id] = transcript
            except SubtitleFetchError as e:
                errors.append((video_id, str(e)))

        # Process in batches to respect concurrency limit
        for i in range(0, len(video_ids), self.max_concurrent):
            batch = video_ids[i : i + self.max_concurrent]
            tasks = [fetch_and_store(vid) for vid in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

        # If all videos failed, raise an error
        if not results and errors:
            raise SubtitleFetchError(
                f"Failed to fetch subtitles for all {len(video_ids)} videos. "
                f"Errors: {errors}"
            )

        return results
