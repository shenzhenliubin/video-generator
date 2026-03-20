"""
Checkpoint Storage

Save and load pipeline checkpoints for recovery.
"""

import json
from pathlib import Path
from typing import Any

from src.core.models import Checkpoint, PipelineStage


class CheckpointStore:
    """Store for pipeline checkpoints."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, checkpoint: Checkpoint) -> None:
        """
        Save a checkpoint.

        Args:
            checkpoint: Checkpoint to save
        """
        video_dir = self.base_dir / checkpoint.video_id
        video_dir.mkdir(exist_ok=True)

        path = video_dir / f"{checkpoint.stage.value}.json"
        with open(path, "w") as f:
            json.dump(checkpoint.model_dump(), f, default=str)

    def load(self, video_id: str, stage: PipelineStage) -> Checkpoint | None:
        """
        Load a checkpoint.

        Args:
            video_id: Video ID
            stage: Pipeline stage

        Returns:
            Checkpoint if exists, None otherwise
        """
        path = self.base_dir / video_id / f"{stage.value}.json"
        if not path.exists():
            return None

        with open(path) as f:
            data = json.load(f)
            return Checkpoint(**data)

    def get_latest_stage(self, video_id: str) -> PipelineStage | None:
        """
        Get the latest completed stage for a video.

        Args:
            video_id: Video ID

        Returns:
            Latest stage, or None if no checkpoints exist
        """
        video_dir = self.base_dir / video_id
        if not video_dir.exists():
            return None

        stages = []
        for f in video_dir.glob("*.json"):
            stage_name = f.stem
            try:
                stages.append(PipelineStage(stage_name))
            except ValueError:
                continue

        if not stages:
            return None

        return max(stages, key=lambda s: s.value)
