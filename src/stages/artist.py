"""
Artist Stage - Image Generation

Generates images for each scene in the storyboard.

Features:
- Generate images from scene descriptions using ImageProvider
- Support multiple image providers (DALL-E, Stability AI, etc.)
- Batch image generation for multiple storyboards
- Automatic file storage and path management
"""

from pathlib import Path

from src.api.base import ImageProvider
from src.api.factory import ProviderFactory
from src.config.settings import get_settings
from src.core.models import GeneratedImage, Storyboard, StyleTemplate
from src.storage.file_store import FileStore


class VideoArtist:
    """
    Generate images for storyboard scenes.

    Transforms scene descriptions into visual assets using
    image generation providers.
    """

    # Default dimensions for video generation
    DEFAULT_WIDTH = 1920
    DEFAULT_HEIGHT = 1080

    # Image prompt enhancement
    PROMPT_ENHANCEMENT = """You are enhancing image generation prompts for video production.
Take the scene description and create a detailed, evocative prompt that will generate
a high-quality image suitable for video backgrounds.

Guidelines:
- Add specific details about lighting, mood, and atmosphere
- Include camera angle and composition suggestions
- Specify art style (photorealistic, cinematic, illustrative, etc.)
- Keep prompts concise but descriptive (50-150 words)
- Focus on visual elements that can be rendered"""

    def __init__(
        self,
        provider: ImageProvider | None = None,
        file_store: FileStore | None = None,
    ):
        """
        Initialize video artist.

        Args:
            provider: Image provider. If None, uses default from settings.
            file_store: File store for saving images. If None, creates default.
        """
        if provider is None:
            settings = get_settings()
            self.provider = ProviderFactory.create_image(settings.default_image_provider)
        else:
            self.provider = provider

        if file_store is None:
            settings = get_settings()
            self.file_store = FileStore(settings.storage_dir)
        else:
            self.file_store = file_store

    async def generate_images(
        self,
        storyboard: Storyboard,
        template: StyleTemplate | None = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ) -> list[GeneratedImage]:
        """
        Generate images for all scenes in a storyboard.

        Args:
            storyboard: Storyboard with scene descriptions
            template: Optional style template for image style reference
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            List of GeneratedImage objects

        Raises:
            ArtistError: If image generation fails
        """
        try:
            # Extract video_id from script_id
            # Format: "original_video_id_template_id" -> "original_video_id"
            video_id = storyboard.script_id.split("_")[0] if "_" in storyboard.script_id else storyboard.script_id

            generated_images = []

            for scene in storyboard.scenes:
                # Build the image prompt
                prompt = self._build_prompt(scene, template)

                # Determine aspect ratio
                aspect_ratio = self._get_aspect_ratio(width, height)

                # Get image style from template if available
                style = None
                if template and template.image_style_prompt:
                    style = template.image_style_prompt

                # Generate the image
                image_data = await self.provider.generate_image(
                    prompt=prompt,
                    style=style,
                    aspect_ratio=aspect_ratio,
                )

                # Save the image
                image_path = self.file_store.save_image(video_id, scene.scene_number, image_data)

                generated_images.append(
                    GeneratedImage(
                        scene_number=scene.scene_number,
                        image_path=image_path,
                        prompt_used=prompt,
                        provider=self.provider.__class__.__name__,
                        width=width,
                        height=height,
                    )
                )

            return generated_images

        except Exception as e:
            raise ArtistError(
                f"Failed to generate images for {storyboard.script_id}: {e}"
            ) from e

    def _build_prompt(
        self,
        scene,
        template: StyleTemplate | None = None,
    ) -> str:
        """
        Build an effective image generation prompt from scene data.

        Args:
            scene: Scene object with visual_description
            template: Optional style template

        Returns:
            Enhanced prompt for image generation
        """
        # Start with the visual description
        prompt_parts = [scene.visual_description]

        # Add mood/atmosphere
        if hasattr(scene, 'mood') and scene.mood != "neutral":
            prompt_parts.append(f"Mood: {scene.mood}")

        # Add camera movement hints
        if hasattr(scene, 'camera_movement'):
            camera_hint = self._camera_to_composition(scene.camera_movement)
            if camera_hint:
                prompt_parts.append(camera_hint)

        # Add style from template
        style_suffix = ""
        if template and hasattr(template, 'image_style_prompt') and template.image_style_prompt:
            style_suffix = f" {template.image_style_prompt}"
        elif template and template.category:
            # Add category-based style hints
            style_suffix = self._get_category_style(template.category.value if hasattr(template.category, 'value') else template.category)
            if style_suffix:
                prompt_suffix = f". {style_suffix}"
                prompt_parts.append(prompt_suffix)

        # Combine all parts
        base_prompt = ". ".join(prompt_parts)

        return base_prompt + style_suffix

    def _camera_to_composition(self, camera_movement: str) -> str:
        """
        Convert camera movement to composition hint.

        Args:
            camera_movement: Camera movement description

        Returns:
            Composition hint for image generation
        """
        hints = {
            "static": "centered composition, balanced framing",
            "panning": "wide horizontal composition, panoramic view",
            "zoom in": "central focus point, dynamic perspective",
            "tracking shot": "sense of movement, action framing",
            "close-up": "intimate composition, shallow depth of field",
            "wide shot": "expansive composition, establishing view",
            "low angle": "dramatic perspective, looking up",
            "high angle": "oversized perspective, looking down",
            "handheld": "candid feel, natural framing",
        }
        return hints.get(camera_movement.lower(), "")

    def _get_category_style(self, category: str) -> str:
        """
        Get image style hint based on template category.

        Args:
            category: Template category

        Returns:
            Style hint suffix
        """
        styles = {
            "dramatic": "Cinematic dramatic lighting, high contrast",
            "humorous": "Bright colorful, cartoonish style",
            "educational": "Clean professional, infographics style",
            "cinematic": "Film grain, cinematic color grading",
            "documentary": "Natural lighting, photojournalistic style",
            "news": "Broadcast quality, news graphics style",
        }
        return styles.get(category.lower(), "")

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """
        Convert dimensions to aspect ratio string.

        Args:
            width: Image width
            height: Image height

        Returns:
            Aspect ratio string (e.g., "16:9")
        """
        # Simplify the ratio
        from math import gcd

        divisor = gcd(width, height)
        return f"{width // divisor}:{height // divisor}"


class ArtistError(Exception):
    """Raised when image generation fails."""
    pass


# Convenience function for backward compatibility
async def generate_images(
    storyboard: Storyboard,
    template: StyleTemplate | None = None,
) -> list[GeneratedImage]:
    """
    Generate images for storyboard scenes.

    This is a convenience function that maintains backward compatibility
    with the original artist.py design.

    Args:
        storyboard: Storyboard with scene descriptions
        template: Optional style template for image style reference

    Returns:
        List of GeneratedImage objects

    Raises:
        ArtistError: If image generation fails
    """
    artist = VideoArtist()
    return await artist.generate_images(storyboard, template)


# Batch image generation for multiple storyboards
class MultiVideoArtist:
    """
    Generate images for multiple video storyboards.

    Processes multiple storyboards efficiently with batch templates.
    """

    def __init__(
        self,
        provider: ImageProvider | None = None,
        file_store: FileStore | None = None,
    ):
        """
        Initialize multi-video artist.

        Args:
            provider: Image provider. If None, uses default from settings.
            file_store: File store for saving images. If None, creates default.
        """
        self._artist = VideoArtist(provider, file_store)

    async def generate_multiple(
        self,
        storyboards: dict[str, Storyboard],
        template: StyleTemplate | None = None,
    ) -> dict[str, list[GeneratedImage]]:
        """
        Generate images for multiple storyboards with the same template.

        Args:
            storyboards: Dictionary mapping video_id to Storyboard
            template: Optional style template to apply to all

        Returns:
            Dictionary mapping video_id to list of GeneratedImage
        """
        results = {}
        errors = []

        for video_id, storyboard in storyboards.items():
            try:
                images = await self._artist.generate_images(storyboard, template)
                results[video_id] = images
            except ArtistError as e:
                errors.append((video_id, str(e)))

        # If all image generations failed, raise an error
        if not results and errors:
            raise ArtistError(
                f"Failed to generate images for all {len(storyboards)} storyboards. "
                f"Errors: {errors}"
            )

        return results

    async def generate_multiple_with_templates(
        self,
        storyboards: dict[str, Storyboard],
        templates: dict[str, StyleTemplate],
    ) -> dict[str, list[GeneratedImage]]:
        """
        Generate images for multiple storyboards with different templates per video.

        Args:
            storyboards: Dictionary mapping video_id to Storyboard
            templates: Dictionary mapping video_id to StyleTemplate

        Returns:
            Dictionary mapping video_id to list of GeneratedImage
        """
        results = {}
        errors = []

        for video_id, storyboard in storyboards.items():
            try:
                template = templates.get(video_id)
                images = await self._artist.generate_images(storyboard, template)
                results[video_id] = images
            except ArtistError as e:
                errors.append((video_id, str(e)))

        # If all image generations failed, raise an error
        if not results and errors:
            raise ArtistError(
                f"Failed to generate images for all {len(storyboards)} storyboards. "
                f"Errors: {errors}"
            )

        return results
