"""
Data Validation Utilities

Validation functions for pipeline data.
"""

from pydantic import ValidationError


def validate_video_id(video_id: str) -> bool:
    """
    Validate YouTube video ID format.

    Args:
        video_id: Video ID to validate

    Returns:
        True if valid format
    """
    # YouTube video IDs are typically 11 characters
    return len(video_id) == 11 and video_id.isalnum()


def validate_channel_id(channel_id: str) -> bool:
    """
    Validate YouTube channel ID format.

    Args:
        channel_id: Channel ID to validate

    Returns:
        True if valid format
    """
    # Channel IDs start with UC followed by 22 characters
    return channel_id.startswith("UC") and len(channel_id) == 24
