"""
Pytest Configuration

Shared fixtures and test configuration.
"""

import pytest


@pytest.fixture
def sample_video_id() -> str:
    """Sample YouTube video ID for testing."""
    return "dQw4w9WgXcQ"


@pytest.fixture
def sample_channel_id() -> str:
    """Sample YouTube channel ID for testing."""
    return "UC_uAXFkgdQ8bzPhxCfQ-yhA"


@pytest.fixture
def sample_transcript_text() -> str:
    """Sample subtitle text for testing."""
    return """
    Welcome to today's video. We're going to talk about
    artificial intelligence and how it's changing the world.
    AI has advanced rapidly in recent years, and we're seeing
    its impact in every industry.
    """
