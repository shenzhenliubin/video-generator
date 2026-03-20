"""
Fetcher Stage - Subtitle Download

Downloads subtitle files for YouTube videos.
"""

from src.core.models import Transcript


async def fetch_subtitles(video_id: str) -> Transcript:
    """
    Fetch subtitles for a YouTube video.

    Args:
        video_id: YouTube video ID

    Returns:
        Transcript with segmented text
    """
    # TODO: Implement subtitle fetching using youtube-transcript-api
    raise NotImplementedError("Fetcher stage not yet implemented")
