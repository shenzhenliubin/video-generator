"""
Database Repository Classes

High-level database operations for videos, channels, and processing stages.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.storage.database import Channel, Database, ProcessingStage, Video


class ChannelRepository:
    """Repository for Channel operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_channel_id(self, channel_id: str) -> Optional[Channel]:
        """Get a channel by its YouTube channel ID."""
        return self.session.execute(
            select(Channel).where(Channel.channel_id == channel_id)
        ).scalar_one_or_none()

    def create(
        self,
        channel_id: str,
        channel_name: str,
        channel_url: str | None = None,
        check_interval_seconds: int = 300,
    ) -> Channel:
        """Create a new channel."""
        channel = Channel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_url=channel_url,
            check_interval_seconds=check_interval_seconds,
            is_active=True,
        )
        self.session.add(channel)
        self.session.commit()
        self.session.refresh(channel)
        return channel

    def get_or_create(
        self,
        channel_id: str,
        channel_name: str,
        channel_url: str | None = None,
    ) -> Channel:
        """Get existing channel or create a new one."""
        channel = self.get_by_channel_id(channel_id)
        if channel is None:
            channel = self.create(channel_id, channel_name, channel_url)
        return channel

    def update_last_checked(
        self, channel_id: str, last_checked_at: datetime
    ) -> None:
        """Update the last checked timestamp for a channel."""
        self.session.execute(
            update(Channel)
            .where(Channel.channel_id == channel_id)
            .values(last_checked_at=last_checked_at)
        )
        self.session.commit()

    def update_last_video(
        self, channel_id: str, published_at: datetime
    ) -> None:
        """Update the last video published timestamp for a channel."""
        self.session.execute(
            update(Channel)
            .where(Channel.channel_id == channel_id)
            .values(last_video_published_at=published_at)
        )
        self.session.commit()

    def list_active(self) -> list[Channel]:
        """List all active channels."""
        return self.session.execute(
            select(Channel).where(Channel.is_active == True)
        ).scalars().all()


class VideoRepository:
    """Repository for Video operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_video_id(self, video_id: str) -> Optional[Video]:
        """Get a video by its YouTube video ID."""
        return self.session.execute(
            select(Video).where(Video.video_id == video_id)
        ).scalar_one_or_none()

    def create(
        self,
        video_id: str,
        channel_id: str,
        title: str,
        url: str,
        published_at: datetime,
        description: str | None = None,
        duration_seconds: int | None = None,
        thumbnail_url: str | None = None,
    ) -> Video:
        """Create a new video record."""
        video = Video(
            video_id=video_id,
            channel_id=channel_id,
            title=title,
            url=url,
            published_at=published_at,
            description=description,
            duration_seconds=duration_seconds,
            thumbnail_url=thumbnail_url,
            status="pending",
        )
        self.session.add(video)
        self.session.commit()
        self.session.refresh(video)
        return video

    def get_or_create(
        self,
        video_id: str,
        channel_id: str,
        title: str,
        url: str,
        published_at: datetime,
        **kwargs,
    ) -> Video:
        """Get existing video or create a new one."""
        video = self.get_by_video_id(video_id)
        if video is None:
            video = self.create(video_id, channel_id, title, url, published_at, **kwargs)
        return video

    def update_status(
        self,
        video_id: str,
        status: str,
        output_path: str | None = None,
        template_used: str | None = None,
        error_message: str | None = None,
        failed_at_stage: str | None = None,
    ) -> None:
        """Update the processing status of a video."""
        values = {"status": status}
        if output_path is not None:
            values["output_path"] = output_path
        if template_used is not None:
            values["template_used"] = template_used
        if error_message is not None:
            values["error_message"] = error_message
        if failed_at_stage is not None:
            values["failed_at_stage"] = failed_at_stage

        self.session.execute(
            update(Video).where(Video.video_id == video_id).values(**values)
        )
        self.session.commit()

    def list_by_status(self, status: str) -> list[Video]:
        """List videos by processing status."""
        return self.session.execute(
            select(Video).where(Video.status == status)
        ).scalars().all()

    def list_pending(self) -> list[Video]:
        """List all pending videos."""
        return self.list_by_status("pending")

    def list_by_channel(self, channel_id: str) -> list[Video]:
        """List all videos for a specific channel."""
        return self.session.execute(
            select(Video)
            .where(Video.channel_id == channel_id)
            .order_by(Video.published_at.desc())
        ).scalars().all()


class ProcessingStageRepository:
    """Repository for ProcessingStage operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self, video_id: str, stage_name: str
    ) -> ProcessingStage:
        """Create a new processing stage record."""
        stage = ProcessingStage(
            video_id=video_id,
            stage_name=stage_name,
            status="pending",
        )
        self.session.add(stage)
        self.session.commit()
        self.session.refresh(stage)
        return stage

    def get_stage(
        self, video_id: str, stage_name: str
    ) -> Optional[ProcessingStage]:
        """Get a specific processing stage for a video."""
        return self.session.execute(
            select(ProcessingStage)
            .where(ProcessingStage.video_id == video_id)
            .where(ProcessingStage.stage_name == stage_name)
        ).scalar_one_or_none()

    def update_status(
        self,
        video_id: str,
        stage_name: str,
        status: str,
        error_message: str | None = None,
        checkpoint_path: str | None = None,
    ) -> None:
        """Update the status of a processing stage."""
        values = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        if checkpoint_path is not None:
            values["checkpoint_path"] = checkpoint_path

        if status == "in_progress" and values.get("started_at") is None:
            values["started_at"] = datetime.now(timezone.utc)
        elif status == "completed":
            values["completed_at"] = datetime.now(timezone.utc)

        self.session.execute(
            update(ProcessingStage)
            .where(ProcessingStage.video_id == video_id)
            .where(ProcessingStage.stage_name == stage_name)
            .values(**values)
        )
        self.session.commit()

    def start_stage(self, video_id: str, stage_name: str) -> ProcessingStage:
        """Start a processing stage (create or update to in_progress)."""
        stage = self.get_stage(video_id, stage_name)
        if stage is None:
            stage = self.create(video_id, stage_name)

        self.update_status(video_id, stage_name, "in_progress")
        return stage

    def complete_stage(
        self, video_id: str, stage_name: str, checkpoint_path: str | None = None
    ) -> None:
        """Mark a processing stage as completed."""
        self.update_status(video_id, stage_name, "completed", checkpoint_path=checkpoint_path)

    def fail_stage(
        self, video_id: str, stage_name: str, error_message: str
    ) -> None:
        """Mark a processing stage as failed."""
        self.update_status(video_id, stage_name, "failed", error_message=error_message)

    def get_latest_stage(self, video_id: str) -> Optional[str]:
        """Get the latest completed stage name for a video."""
        stage = self.session.execute(
            select(ProcessingStage)
            .where(ProcessingStage.video_id == video_id)
            .where(ProcessingStage.status == "completed")
            .order_by(ProcessingStage.completed_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        return stage.stage_name if stage else None

    def get_all_stages(self, video_id: str) -> list[ProcessingStage]:
        """Get all processing stages for a video."""
        return self.session.execute(
            select(ProcessingStage)
            .where(ProcessingStage.video_id == video_id)
            .order_by(ProcessingStage.created_at)
        ).scalars().all()
