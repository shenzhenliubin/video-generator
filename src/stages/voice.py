"""
Voice Stage - Audio Synthesis

Generates narration audio for each scene.
"""

from src.core.models import GeneratedAudio, Storyboard


async def generate_audio(storyboard: Storyboard) -> list[GeneratedAudio]:
    """
    Generate audio for storyboard scenes.

    Args:
        storyboard: Storyboard with narration text

    Returns:
        List of generated audio files
    """
    # TODO: Implement TTS audio generation
    raise NotImplementedError("Voice stage not yet implemented")
