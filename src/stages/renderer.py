"""
Renderer Stage - Video Composition

Combines images and audio into final video using MoviePy.

Features:
- MoviePy-based video composition
- Synchronized image/audio scene alignment
- Automatic video output with proper encoding
- Subtitle support with SceneData structure
"""

from moviepy import CompositeVideoClip, VideoFileClip, AudioFileClip, TextClip, ImageClip, concatenate_videoclips, concatenate_audioclips

from src.core.models import GeneratedAudio, GeneratedImage, VideoOutput, SceneData
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
        storyboard=None,
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

            # Create SceneData objects - complete data structure for each scene
            scene_data_list = []
            current_time = 0.0

            for image_data in sorted_images:
                # Find corresponding audio
                audio_data = None
                for aud in sorted_audio:
                    if aud.scene_number == image_data.scene_number:
                        audio_data = aud
                        break

                if audio_data is None:
                    raise RenderError(f"No audio found for scene {image_data.scene_number}")

                # Find corresponding scene from storyboard
                narration = ""
                visual_description = ""
                camera_movement = "static"
                mood = "neutral"

                if storyboard and hasattr(storyboard, 'scenes'):
                    for scene in storyboard.scenes:
                        if scene.scene_number == image_data.scene_number:
                            narration = scene.narration
                            visual_description = scene.visual_description
                            camera_movement = scene.camera_movement
                            mood = scene.mood
                            break

                scene_data = SceneData(
                    scene_number=image_data.scene_number,
                    narration=narration,
                    visual_description=visual_description,
                    duration=audio_data.duration,
                    camera_movement=camera_movement,
                    mood=mood,
                    start_time=current_time,
                    image_path=image_data.image_path,
                    audio_path=audio_data.audio_path,
                    image_prompt=image_data.prompt_used,
                )
                scene_data_list.append(scene_data)
                current_time += audio_data.duration

            # Print scene data summary
            print(f"  Scene data assembled: {len(scene_data_list)} scenes")
            for sd in scene_data_list:
                print(f"    Scene {sd.scene_number}: {sd.duration:.1f}s, start={sd.start_time:.1f}s")
                print(f"      Narration: {sd.narration[:60]}..." if len(sd.narration) > 60 else f"      Narration: {sd.narration}")

            # Create video clips from images
            video_clips = []
            total_duration = 0

            for scene_data in scene_data_list:
                # Create clip from image - make it last for the scene duration
                clip = await self._create_image_clip(
                    scene_data.image_path,
                    scene_data.duration,
                    fps,
                    width,
                    height,
                )
                video_clips.append(clip)
                total_duration += scene_data.duration

            # Concatenate all video clips
            if len(video_clips) == 1:
                final_video = video_clips[0]
            else:
                final_video = concatenate_videoclips(video_clips, method="compose")

            # Add audio to the video
            final_video_with_audio = await self._add_audio_to_video(
                final_video,
                scene_data_list,
            )

            # Add subtitles using SceneData
            final_video_with_subtitles = await self._add_subtitles_to_video(
                final_video_with_audio,
                scene_data_list,
                width,
                height,
            )

            # Save the final video using MoviePy
            videos_dir = self.file_store.base_dir / "videos"
            videos_dir.mkdir(parents=True, exist_ok=True)
            video_path = str(videos_dir / f"{storyboard_id}.mp4")

            # Write video file
            final_video_with_subtitles.write_videofile(
                video_path,
                fps=fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
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
        # Create an ImageClip with the specified duration
        # Use resized() method and with_fps() for MoviePy 2.x
        clip = ImageClip(image_path, duration=duration).resized((width, height)).with_fps(fps)

        return clip

    async def _add_audio_to_video(
        self,
        video_clip: VideoFileClip,
        scene_data_list: list[SceneData],
    ) -> VideoFileClip:
        """
        Add audio tracks to video clip using SceneData.

        Args:
            video_clip: Video clip without audio
            scene_data_list: List of SceneData with audio paths

        Returns:
            VideoFileClip with audio added
        """
        # Load audio clips in order
        audio_clips = []

        for scene_data in scene_data_list:
            audio_clip = AudioFileClip(scene_data.audio_path)
            audio_clips.append(audio_clip)

        if audio_clips:
            # Concatenate audio clips - they'll be played sequentially
            final_audio = concatenate_audioclips(audio_clips)

            # For MoviePy 2.x: use with_audio directly
            video_clip = video_clip.with_audio(final_audio)

        return video_clip

    async def _add_subtitles_to_video(
        self,
        video_clip: VideoFileClip,
        scene_data_list: list[SceneData],
        width: int,
        height: int,
    ) -> VideoFileClip:
        """
        Add subtitles to video clip using SceneData.

        For MoviePy 2.x, we create all TextClips first, then composite them.

        Args:
            video_clip: Video clip without subtitles
            scene_data_list: List of SceneData with narration and timing
            width: Video width
            height: Video height

        Returns:
            VideoFileClip with subtitles added
        """
        subtitle_clips = []

        for scene_data in scene_data_list:
            try:
                # Create a TextClip with font that supports Chinese
                # Use 'caption' method for automatic text wrapping
                # Set size to limit width and enable multi-line text
                txt_clip = TextClip(
                    text=scene_data.narration,
                    font='/System/Library/Fonts/STHeiti Medium.ttc',
                    font_size=48,
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(int(width * 0.8), None),  # Limit to 80% of video width, auto height
                    text_align='center',
                )

                # Set timing - when the subtitle appears and for how long
                txt_clip = txt_clip.with_start(scene_data.start_time).with_duration(scene_data.duration)

                # Set position - bottom center of video
                txt_clip = txt_clip.with_position(('center', height * 0.85))

                subtitle_clips.append(txt_clip)
                print(f"  Created subtitle for scene {scene_data.scene_number}: {scene_data.narration[:30]}...")
            except Exception as e:
                print(f"  Error creating subtitle for scene {scene_data.scene_number}: {e}")
                import traceback
                traceback.print_exc()
                continue

        if subtitle_clips:
            print(f"  Compositing {len(subtitle_clips)} subtitle clips with video...")

            # Create composite with video and all subtitles
            # The video clip is the base, subtitles are layered on top
            all_clips = [video_clip] + subtitle_clips

            # CompositeVideoClip in MoviePy 2.x
            final_video = CompositeVideoClip(all_clips, size=video_clip.size)

            # Preserve audio from the original video clip
            if video_clip.audio is not None:
                final_video = final_video.with_audio(video_clip.audio)
                print(f"  Audio preserved in composite video")
            else:
                print(f"  WARNING: No audio found in original video clip")

            print(f"  ✓ Added {len(subtitle_clips)} subtitle clips")
            return final_video
        else:
            print(f"  WARNING: No subtitle clips created")
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
