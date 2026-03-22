"""
Renderer Stage - Video Composition

Combines images and audio into final video using MoviePy.

Features:
- MoviePy-based video composition
- Synchronized image/audio scene alignment
- Automatic video output with proper encoding
- Batch video rendering for multiple projects
- Support for multiple output formats
"""

from moviepy import CompositeVideoClip, VideoFileClip, AudioFileClip

from src.core.models import GeneratedAudio, GeneratedImage, VideoOutput
from src.storage.file_store import FileStore


class VideoRenderer:
    """
    Render final videos from images and audio.

    Combines scene images with narration audio using MoviePy
    to create the final video output.
    """

    def __init__(self, file_store: FileStore | None = None):
        """
        Initialize video renderer.

        Args:
            file_store: File store for saving videos. If None, creates default.
        """
        if file_store is None:
            from src.config.settings import get_settings
            self.file_store = FileStore(get_settings().storage_dir)
        else:
            self.file_store = file_store

    async def render_video(
        self,
        storyboard_id: str,
        images: list[GeneratedImage],
        audio_segments: list[GeneratedAudio],
        resolution: str = "1920x1080",
        output_format: str = "mp4",
        fps: int = 24,
    ) -> VideoOutput:
        """
        Render final video from images and audio.

        Args:
            storyboard_id: Storyboard identifier
            images: List of generated images (one per scene)
            audio_segments: List of generated audio segments
            resolution: Video resolution as "WIDTHxHEIGHT" string
            output_format: Output video format (mp4, avi, etc.)
            fps: Frames per second

        Returns:
            VideoOutput with metadata

        Raises:
            RenderError: If video rendering fails
        """
        try:
            # Parse resolution
            width, height = map(int, resolution.split("x"))

            # Sort images and audio by scene_number
            sorted_images = sorted(images, key=lambda img: img.scene_number)
            sorted_audio = sorted(audio_segments, key=lambda aud: aud.scene_number)

            if not sorted_images:
                raise RenderError("No images provided for rendering")

            if not sorted_audio:
                raise RenderError("No audio segments provided for rendering")

            if len(sorted_images) != len(sorted_audio):
                raise RenderError(
                    f"Image/audio count mismatch: {len(sorted_images)} images vs {len(sorted_audio)} audio"
                )

            # Extract video_id from storyboard_id
            # Format: "original_video_id_template_id" -> "original_video_id"
            video_id = storyboard_id.split("_")[0] if "_" in storyboard_id else storyboard_id

            # Create video clips from images
            video_clips = []
            total_duration = 0

            for image_data in sorted_images:
                # Load image and create video clip from it
                try:
                    # Create a video clip from the image (display for scene duration)
                    scene_duration = await self._get_scene_duration(
                        sorted_images,
                        sorted_audio,
                        image_data.scene_number,
                    )

                    # Create clip from image - make it last for the scene duration
                    # We use a placeholder approach since MoviePy needs video files
                    # For now, we'll create a simple approach: use the image as a static frame
                    clip = await self._create_image_clip(
                        image_data.image_path,
                        scene_duration,
                        fps,
                        width,
                        height,
                    )
                    video_clips.append(clip)
                    total_duration += scene_duration

                except Exception as e:
                    raise RenderError(
                        f"Failed to create clip for scene {image_data.scene_number}: {e}"
                    ) from e

            # Concatenate all video clips
            if len(video_clips) == 1:
                final_video = video_clips[0]
            else:
                final_video = await self._concatenate_clips(video_clips)

            # Add audio to the video
            final_video_with_audio = await self._add_audio_to_video(
                final_video,
                sorted_audio,
                video_id,
            )

            # Save the final video
            video_path = self.file_store.save_video(
                video_id,
                final_video_with_audio,
            )

            return VideoOutput(
                storyboard_id=storyboard_id,
                video_path=video_path,
                duration=int(total_duration),
                resolution=resolution,
                format=output_format,
                scenes_count=len(sorted_images),
            )

        except Exception as e:
            raise RenderError(
                f"Failed to render video for {storyboard_id}: {e}"
            ) from e

    async def _create_image_clip(
        self,
        image_path: str,
        duration: float,
        fps: int,
        width: int,
        height: int,
    ) -> VideoFileClip:
        """
        Create a video clip from an image.

        Args:
            image_path: Path to the image file
            duration: Duration in seconds
            fps: Frames per second
            width: Target width
            height: Target height

        Returns:
            VideoFileClip with the image as video
        """
        # Load the image
        from moviepy import ImageSequenceClip
        from PIL import Image

        # Create a clip by repeating the image for the duration
        img = Image.open(image_path)
        img = img.resize((width, height))

        # Create a temporary sequence clip
        import tempfile
        import os

        temp_dir = tempfile.mkdtemp()
        temp_pattern = os.path.join(temp_dir, "frame_%04d.png")

        # Save the image once (will be used by MoviePy)
        frame_path = temp_pattern % 0
        img.save(frame_path)

        # Create a clip with fps frames repeating the image
        clip = ImageSequenceClip(
            [frame_path] * int(duration * fps),
            fps=fps,
        )

        # Note: In a real implementation, we might want to clean up temp files
        # For now, MoviePy will handle them

        return clip

    async def _get_scene_duration(
        self,
        images: list[GeneratedImage],
        audio_segments: list[GeneratedAudio],
        scene_number: int,
    ) -> float:
        """
        Get the duration for a scene based on audio segment.

        Args:
            images: List of generated images
            audio_segments: List of generated audio
            scene_number: Scene number

        Returns:
            Duration in seconds
        """
        # Find the corresponding audio segment
        for audio in audio_segments:
            if audio.scene_number == scene_number:
                return audio.duration

        # Fallback: estimate from image (shouldn't happen in normal flow)
        return 5.0

    async def _concatenate_clips(self, clips: list[VideoFileClip]) -> VideoFileClip:
        """
        Concatenate video clips in sequence.

        Args:
            clips: List of VideoFileClip to concatenate

        Returns:
            Concatenated VideoFileClip
        """
        if len(clips) == 1:
            return clips[0]

        # Use concatenate method
        from moviepy import concatenate_videoclips

        return concatenate_videoclips(clips, method="compose")

    async def _add_audio_to_video(
        self,
        video_clip: VideoFileClip,
        audio_segments: list[GeneratedAudio],
        video_id: str,
    ) -> VideoFileClip:
        """
        Add audio tracks to video clip.

        Args:
            video_clip: Video clip without audio
            audio_segments: List of audio segments with duration info
            video_id: Video ID for file naming

        Returns:
            VideoFileClip with audio added
        """
        # Load and concatenate all audio segments
        audio_clips = []
        current_time = 0.0

        for audio_data in sorted(audio_segments, key=lambda a: a.scene_number):
            audio_clip = AudioFileClip(audio_data.audio_path)
            # Set start time for this audio segment
            audio_clip = audio_clip.set_start(current_time)
            audio_clips.append(audio_clip)
            current_time += audio_data.duration

        if audio_clips:
            # Concatenate audio clips
            from moviepy import concatenate_audioclips

            final_audio = concatenate_audioclips(audio_clips)
            # Set audio for the video
            video_clip = video_clip.set_audio(final_audio)

        return video_clip


class RenderError(Exception):
    """Raised when video rendering fails."""
    pass


# Convenience function for backward compatibility
async def render_video(
    storyboard_id: str,
    images: list[GeneratedImage],
    audio: list[GeneratedAudio],
) -> VideoOutput:
    """
    Render final video from images and audio.

    This is a convenience function that maintains backward compatibility
    with the original renderer.py design.

    Args:
        storyboard_id: Storyboard identifier
        images: List of generated images
        audio: List of generated audio segments

    Returns:
        VideoOutput with metadata

    Raises:
        RenderError: If video rendering fails
    """
    renderer = VideoRenderer()
    return await renderer.render_video(storyboard_id, images, audio)


# Batch video rendering for multiple projects
class MultiVideoRenderer:
    """
    Render videos for multiple video projects.

    Processes multiple image/audio sets efficiently.
    """

    def __init__(self, file_store: FileStore | None = None):
        """
        Initialize multi-video renderer.

        Args:
            file_store: File store for saving videos. If None, creates default.
        """
        self._renderer = VideoRenderer(file_store)

    async def render_multiple(
        self,
        projects: dict[str, tuple[list[GeneratedImage], list[GeneratedAudio]]],
        resolution: str = "1920x1080",
        output_format: str = "mp4",
        fps: int = 24,
    ) -> dict[str, VideoOutput]:
        """
        Render multiple videos from images and audio sets.

        Args:
            projects: Dictionary mapping storyboard_id to tuple of (images, audio)
            resolution: Video resolution as "WIDTHxHEIGHT" string
            output_format: Output video format
            fps: Frames per second

        Returns:
            Dictionary mapping storyboard_id to VideoOutput
        """
        results = {}
        errors = []

        for storyboard_id, (images, audio) in projects.items():
            try:
                video = await self._renderer.render_video(
                    storyboard_id, images, audio, resolution, output_format, fps
                )
                results[storyboard_id] = video
            except RenderError as e:
                errors.append((storyboard_id, str(e)))

        # If all renders failed, raise an error
        if not results and errors:
            raise RenderError(
                f"Failed to render all {len(projects)} videos. "
                f"Errors: {errors}"
            )

        return results
