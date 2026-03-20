"""
File Store

Manages storage of generated files (images, audio, video).
"""

from pathlib import Path
from typing import Any


class FileStore:
    """Storage for generated files."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.base_dir / "images").mkdir(exist_ok=True)
        (self.base_dir / "audio").mkdir(exist_ok=True)
        (self.base_dir / "videos").mkdir(exist_ok=True)

    def save_image(self, video_id: str, scene_number: int, data: bytes) -> str:
        """
        Save a generated image.

        Args:
            video_id: Video ID
            scene_number: Scene number
            data: Image data

        Returns:
            Path to saved file
        """
        path = self.base_dir / "images" / video_id
        path.mkdir(exist_ok=True)
        file_path = path / f"scene_{scene_number:03d}.png"
        file_path.write_bytes(data)
        return str(file_path)

    def save_audio(self, video_id: str, scene_number: int, data: bytes) -> str:
        """
        Save generated audio.

        Args:
            video_id: Video ID
            scene_number: Scene number
            data: Audio data

        Returns:
            Path to saved file
        """
        path = self.base_dir / "audio" / video_id
        path.mkdir(exist_ok=True)
        file_path = path / f"scene_{scene_number:03d}.mp3"
        file_path.write_bytes(data)
        return str(file_path)

    def save_video(self, video_id: str, data: bytes) -> str:
        """
        Save final video.

        Args:
            video_id: Video ID
            data: Video data

        Returns:
            Path to saved file
        """
        path = self.base_dir / "videos"
        file_path = path / f"{video_id}.mp4"
        file_path.write_bytes(data)
        return str(file_path)
