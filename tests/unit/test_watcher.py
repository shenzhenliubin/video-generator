"""
Unit Tests for YouTube Watcher

Tests for channel monitoring and video detection.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import VideoMetadata
from src.stages.watcher import (
    ChannelWatcher,
    MultiChannelWatcher,
    YouTubeClient,
)


class TestYouTubeClient:
    """Tests for YouTubeClient."""

    @pytest.mark.asyncio
    async def test_parse_datetime(self):
        """Test datetime parsing."""
        client = YouTubeClient(api_key="test_key")

        # Test ISO format with Z suffix
        dt = client._parse_datetime("2025-03-20T12:00:00Z")
        assert dt.tzinfo is not None  # Should be timezone aware

        # Test empty string
        dt = client._parse_datetime("")
        assert isinstance(dt, datetime)


class TestChannelWatcher:
    """Tests for ChannelWatcher."""

    def test_get_last_checked(self):
        """Test getting last checked timestamp."""
        watcher = ChannelWatcher()

        # Initially no timestamp
        assert watcher.get_last_checked("UC_test") is None

        # After updating
        now = datetime.now(timezone.utc)
        watcher.update_last_checked("UC_test", now)
        assert watcher.get_last_checked("UC_test") == now

    @pytest.mark.asyncio
    async def test_check_new_videos_first_time(self):
        """Test checking channel for first time."""
        watcher = ChannelWatcher()

        now = datetime.now(timezone.utc)

        # Create sample video data
        sample_videos = [
            {
                "video_id": "video1",
                "channel_id": "UC_test",
                "channel_name": "Test Channel",
                "title": "Video 1",
                "description": "",
                "published_at": now.isoformat(),
                "thumbnail_url": "",
                "url": "https://youtube.com/watch?v=video1"
            }
        ]

        with patch.object(watcher.client, "search_channel_videos") as mock_search:
            # Setup mock to return sample videos
            mock_search.return_value = sample_videos

            # Execute
            results = await watcher.check_new_videos("UC_test")

            # Assert
            assert len(results) == 1
            assert results[0].video_id == "video1"
            # Last checked should be updated
            assert watcher.get_last_checked("UC_test") is not None


class TestMultiChannelWatcher:
    """Tests for MultiChannelWatcher."""

    @pytest.mark.asyncio
    async def test_check_multiple_channels(self):
        """Test checking multiple channels efficiently."""
        multi_watcher = MultiChannelWatcher()

        # Create mock watchers
        watcher1 = MagicMock()
        watcher1.check_new_videos = AsyncMock()
        watcher1.check_new_videos.return_value = [
            VideoMetadata(
                video_id="v1",
                channel_id="UC_ch1",
                channel_name="Channel 1",
                title="Video 1",
                description="",
                published_at=datetime.now(timezone.utc),
                duration=600,
                thumbnail_url="",
                url="https://youtube.com/watch?v=v1"
            )
        ]

        watcher2 = MagicMock()
        watcher2.check_new_videos = AsyncMock()
        watcher2.check_new_videos.return_value = []

        # Create a function to return watchers
        watchers_dict = {"UC_ch1": watcher1, "UC_ch2": watcher2}

        def get_watcher_side_effect(channel_id):
            return watchers_dict.get(channel_id, ChannelWatcher())

        with patch.object(multi_watcher, "get_watcher", side_effect=get_watcher_side_effect):
            # Execute
            results = await multi_watcher.check_all_channels(["UC_ch1", "UC_ch2"])

            # Assert
            assert "UC_ch1" in results
            assert len(results["UC_ch1"]) == 1
            assert "UC_ch2" not in results  # No new videos for channel 2


class TestConvenienceFunction:
    """Tests for the convenience watch_channel function."""

    @pytest.mark.asyncio
    async def test_watch_channel(self):
        """Test the convenience function."""
        from src.stages.watcher import watch_channel

        with patch("src.stages.watcher.YouTubeClient") as mock_client_class:
            # Setup mock
            mock_client = MagicMock()
            mock_watcher = MagicMock()
            mock_client_class.return_value = mock_client
            mock_watcher.check_new_videos = AsyncMock()
            mock_watcher.check_new_videos.return_value = []

            # Mock the ChannelWatcher creation
            with patch("src.stages.watcher.ChannelWatcher", return_value=mock_watcher):
                result = await watch_channel("UC_test")

                # Should return the watcher's result
                assert result == []
