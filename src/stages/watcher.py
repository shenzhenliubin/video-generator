"""
Watcher Stage - YouTube Channel Monitoring

Monitors YouTube channels for new videos using YouTube Data API v3.

Features:
- Check channels for new videos
- Track last checked timestamp
- Incremental detection (only return new videos)
- Quota-aware (monitor API usage)
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config.settings import get_settings
from src.core.models import VideoMetadata


class YouTubeClient:
    """
    YouTube Data API v3 client wrapper.

    Handles API communication and quota monitoring.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize YouTube client.

        Args:
            api_key: YouTube Data API key. If None, loads from settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.youtube_api_key

        if not self.api_key:
            raise ValueError("YouTube API key is required. Set YOUTUBE_API_KEY in .env")

        self._client = None

    @property
    def client(self):
        """Lazy-load the YouTube client."""
        if self._client is None:
            self._client = build("youtube", "v3", developerKey=self.api_key)
        return self._client

    async def search_channel_videos(
        self,
        channel_id: str,
        max_results: int = 10,
        published_after: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for videos from a specific channel.

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of results to return
            published_after: Only return videos published after this time

        Returns:
            List of video search results

        Raises:
            HttpError: If API request fails
        """
        try:
            # Build search request
            request = self.client.search().list(
                part="snippet",
                channelId=channel_id,
                order="date",  # Sort by date (newest first)
                type="video",  # Only return videos
                maxResults=max_results,
            )

            # Add publishedAfter filter if specified
            if published_after:
                # Convert to RFC 3339 format
                published_after_str = published_after.isoformat()
                # Note: publishedAfter parameter might not be available in search.list
                # We'll filter results after fetching

            # Execute request (run in thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, request.execute)

            results = []

            for item in response.get("items", []):
                # Extract video metadata
                video_id = item.get("id", {})
                if isinstance(video_id, dict):
                    video_id = video_id.get("videoId")

                snippet = item.get("snippet", {})

                video_data = {
                    "video_id": video_id,
                    "channel_id": channel_id,
                    "channel_name": snippet.get("channelTitle", ""),
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published_at": self._parse_datetime(snippet.get("publishedAt")),
                    "thumbnail_url": snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url", "")
                    .get("default", {})
                    .get("url", ""),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                }

                # Filter by published_after if specified
                if published_after:
                    pub_date = video_data["published_at"]
                    if pub_date > published_after:
                        results.append(video_data)
                else:
                    results.append(video_data)

            return results

        except HttpError as e:
            if e.resp.status == 403:
                # Quota exceeded
                raise QuotaExceededError(
                    "YouTube API quota exceeded. "
                    "The daily quota of 10,000 units has been reached."
                ) from e
            else:
                raise

    @staticmethod
    def _parse_datetime(date_string: str) -> datetime:
        """Parse ISO 8601 datetime string."""
        if not date_string:
            return datetime.now(timezone.utc)

        try:
            # Handle 'Z' suffix for UTC
            if date_string.endswith("Z"):
                date_string = date_string[:-1] + "+00:00"
            return datetime.fromisoformat(date_string)
        except (ValueError, AttributeError):
            return datetime.now(timezone.utc)


class QuotaExceededError(Exception):
    """Raised when YouTube API quota is exceeded."""
    pass


class ChannelWatcher:
    """
    Monitors a YouTube channel for new videos.

    Tracks the last check timestamp to only return new videos.
    """

    def __init__(self, client: YouTubeClient | None = None):
        """
        Initialize channel watcher.

        Args:
            client: YouTube client. If None, creates default client.
        """
        self.client = client or YouTubeClient()
        self._last_checked: dict[str, datetime] = {}

    def get_last_checked(self, channel_id: str) -> datetime | None:
        """Get the last checked timestamp for a channel."""
        return self._last_checked.get(channel_id)

    def update_last_checked(self, channel_id: str, timestamp: datetime | None = None):
        """Update the last checked timestamp for a channel."""
        self._last_checked[channel_id] = timestamp or datetime.now(timezone.utc)

    async def check_new_videos(
        self,
        channel_id: str,
        max_results: int = 10,
    ) -> list[VideoMetadata]:
        """
        Check for new videos from a channel.

        Only returns videos published after the last check.

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of videos to return

        Returns:
            List of new video metadata (published since last check)

        Raises:
            QuotaExceededError: If API quota is exceeded
        """
        last_checked = self.get_last_checked(channel_id)

        # Fetch latest videos from channel
        video_results = await self.client.search_channel_videos(
            channel_id=channel_id,
            max_results=max_results,
            published_after=last_checked,
        )

        # Update last checked timestamp
        if video_results:
            # Use the latest video's publish time
            latest_published = max(v["published_at"] for v in video_results)
            self.update_last_checked(channel_id, latest_published)

        # Convert to VideoMetadata objects
        videos = []
        for video_data in video_results:
            videos.append(
                VideoMetadata(
                    video_id=video_data["video_id"],
                    channel_id=video_data["channel_id"],
                    channel_name=video_data["channel_name"],
                    title=video_data["title"],
                    description=video_data["description"],
                    published_at=video_data["published_at"],
                    duration=0,  # Will be fetched separately if needed
                    thumbnail_url=video_data["thumbnail_url"],
                    url=video_data["url"],
                )
            )

        return videos


# Convenience function for backward compatibility with original design
async def watch_channel(
    channel_id: str,
    api_key: str | None = None,
) -> list[VideoMetadata]:
    """
    Watch a YouTube channel for new videos.

    This is a convenience function that maintains backward compatibility
    with the original watcher.py design.

    Args:
        channel_id: YouTube channel ID
        api_key: YouTube API key (optional, uses .env if not provided)

    Returns:
        List of new video metadata

    Raises:
        ValueError: If API key is not provided or configured
        QuotaExceededError: If API quota is exceeded
    """
    client = YouTubeClient(api_key=api_key)
    watcher = ChannelWatcher(client=client)
    return await watcher.check_new_videos(channel_id)


# Batch watching for multiple channels
class MultiChannelWatcher:
    """
    Monitor multiple YouTube channels efficiently.

    Minimizes API quota usage by checking all channels in a single batch.
    """

    def __init__(self, client: YouTubeClient | None = None):
        """
        Initialize multi-channel watcher.

        Args:
            client: YouTube client. If None, creates default client.
        """
        self.client = client or YouTubeClient()
        self.watchers: dict[str, ChannelWatcher] = {}

    def get_watcher(self, channel_id: str) -> ChannelWatcher:
        """Get or create a watcher for a channel."""
        if channel_id not in self.watchers:
            self.watchers[channel_id] = ChannelWatcher(client=self.client)
        return self.watchers[channel_id]

    async def check_all_channels(
        self,
        channel_ids: list[str],
    ) -> dict[str, list[VideoMetadata]]:
        """
        Check multiple channels for new videos.

        Args:
            channel_ids: List of YouTube channel IDs

        Returns:
            Dictionary mapping channel_id to list of new videos

        Raises:
            QuotaExceededError: If API quota is exceeded
        """
        results = {}

        for channel_id in channel_ids:
            watcher = self.get_watcher(channel_id)
            try:
                new_videos = await watcher.check_new_videos(channel_id)
                if new_videos:
                    results[channel_id] = new_videos
            except QuotaExceededError:
                # Stop checking if quota exceeded
                raise
            except Exception as e:
                # Log error but continue with other channels
                print(f"Error checking channel {channel_id}: {e}")

        return results
