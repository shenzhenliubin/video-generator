"""
Voice Stage - Audio Synthesis

Generates narration audio for each scene.

Features:
- Text-to-speech conversion using TTS providers
- Support multiple TTS providers (ElevenLabs, local TTS, etc.)
- Batch audio generation for multiple storyboards
- Automatic file storage and duration tracking
"""

from pathlib import Path

from src.api.base import TTSProvider
from src.api.factory import ProviderFactory
from src.config.settings import get_settings
from src.core.models import GeneratedAudio, Storyboard, StyleTemplate
from src.storage.file_store import FileStore


class VoiceActor:
    """
    Generate narration audio for storyboard scenes.

    Transforms scene narrations into audio assets using
    text-to-speech providers.
    """

    # Default speech parameters
    DEFAULT_SPEED = 1.0

    def __init__(
        self,
        provider: TTSProvider | None = None,
        file_store: FileStore | None = None,
    ):
        """
        Initialize voice actor.

        Args:
            provider: TTS provider. If None, uses default from settings.
            file_store: File store for saving audio. If None, creates default.
        """
        if provider is None:
            settings = get_settings()
            self.provider = ProviderFactory.create_tts(settings.default_tts_provider)
        else:
            self.provider = provider

        if file_store is None:
            settings = get_settings()
            self.file_store = FileStore(settings.storage_dir)
        else:
            self.file_store = file_store

    async def generate_audio(
        self,
        storyboard: Storyboard,
        template: StyleTemplate | None = None,
        speed: float = DEFAULT_SPEED,
    ) -> list[GeneratedAudio]:
        """
        Generate audio for all scenes in a storyboard.

        Args:
            storyboard: Storyboard with scene narrations
            template: Optional style template for voice selection
            speed: Speech speed multiplier

        Returns:
            List of GeneratedAudio objects

        Raises:
            VoiceError: If audio generation fails
        """
        try:
            # Extract video_id from script_id
            # Format: "original_video_id_template_id" -> "original_video_id"
            video_id = storyboard.script_id.split("_")[0] if "_" in storyboard.script_id else storyboard.script_id

            generated_audio = []

            for scene in storyboard.scenes:
                # Get the narration text
                text = scene.narration

                # Get voice_id from template if available, otherwise use default
                voice_id = None
                if template and template.voice_id:
                    voice_id = template.voice_id

                # Synthesize the audio
                audio_data, mime_type = await self.provider.synthesize(
                    text=text,
                    voice_id=voice_id,
                    speed=speed,
                )

                # Save the audio
                audio_path = self.file_store.save_audio(video_id, scene.scene_number, audio_data)

                # Calculate approximate duration (based on text length and speed)
                # Rough estimate: average reading speed is 150 words per minute
                word_count = len(text.split())
                duration = (word_count / 150) * 60 / speed

                generated_audio.append(
                    GeneratedAudio(
                        scene_number=scene.scene_number,
                        audio_path=audio_path,
                        text=text,
                        provider=self.provider.__class__.__name__,
                        voice_id=voice_id,
                        duration=duration,
                    )
                )

            return generated_audio

        except Exception as e:
            raise VoiceError(
                f"Failed to generate audio for {storyboard.script_id}: {e}"
            ) from e


class VoiceError(Exception):
    """Raised when audio generation fails."""
    pass


# Convenience function for backward compatibility
async def generate_audio(
    storyboard: Storyboard,
    template: StyleTemplate | None = None,
) -> list[GeneratedAudio]:
    """
    Generate audio for storyboard scenes.

    This is a convenience function that maintains backward compatibility
    with the original voice.py design.

    Args:
        storyboard: Storyboard with scene narrations
        template: Optional style template for voice selection

    Returns:
        List of GeneratedAudio objects

    Raises:
        VoiceError: If audio generation fails
    """
    actor = VoiceActor()
    return await actor.generate_audio(storyboard, template)


# Batch audio generation for multiple storyboards
class MultiVideoVoiceActor:
    """
    Generate audio for multiple video storyboards.

    Processes multiple storyboards efficiently with batch templates.
    """

    def __init__(
        self,
        provider: TTSProvider | None = None,
        file_store: FileStore | None = None,
    ):
        """
        Initialize multi-video voice actor.

        Args:
            provider: TTS provider. If None, uses default from settings.
            file_store: File store for saving audio. If None, creates default.
        """
        self._actor = VoiceActor(provider, file_store)

    async def generate_multiple(
        self,
        storyboards: dict[str, Storyboard],
        template: StyleTemplate | None = None,
    ) -> dict[str, list[GeneratedAudio]]:
        """
        Generate audio for multiple storyboards with the same template.

        Args:
            storyboards: Dictionary mapping video_id to Storyboard
            template: Optional style template to apply to all

        Returns:
            Dictionary mapping video_id to list of GeneratedAudio
        """
        results = {}
        errors = []

        for video_id, storyboard in storyboards.items():
            try:
                audio = await self._actor.generate_audio(storyboard, template)
                results[video_id] = audio
            except VoiceError as e:
                errors.append((video_id, str(e)))

        # If all audio generations failed, raise an error
        if not results and errors:
            raise VoiceError(
                f"Failed to generate audio for all {len(storyboards)} storyboards. "
                f"Errors: {errors}"
            )

        return results

    async def generate_multiple_with_templates(
        self,
        storyboards: dict[str, Storyboard],
        templates: dict[str, StyleTemplate],
    ) -> dict[str, list[GeneratedAudio]]:
        """
        Generate audio for multiple storyboards with different templates per video.

        Args:
            storyboards: Dictionary mapping video_id to Storyboard
            templates: Dictionary mapping video_id to StyleTemplate

        Returns:
            Dictionary mapping video_id to list of GeneratedAudio
        """
        results = {}
        errors = []

        for video_id, storyboard in storyboards.items():
            try:
                template = templates.get(video_id)
                audio = await self._actor.generate_audio(storyboard, template)
                results[video_id] = audio
            except VoiceError as e:
                errors.append((video_id, str(e)))

        # If all audio generations failed, raise an error
        if not results and errors:
            raise VoiceError(
                f"Failed to generate audio for all {len(storyboards)} storyboards. "
                f"Errors: {errors}"
            )

        return results
