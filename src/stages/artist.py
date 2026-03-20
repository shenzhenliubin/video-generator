"""
Artist Stage - Image Generation

Generates images for each scene in the storyboard.
"""

from src.core.models import GeneratedImage, Storyboard


async def generate_images(storyboard: Storyboard) -> list[GeneratedImage]:
    """
    Generate images for storyboard scenes.

    Args:
        storyboard: Storyboard with scene descriptions

    Returns:
        List of generated images
    """
    # TODO: Implement image generation
    raise NotImplementedError("Artist stage not yet implemented")
