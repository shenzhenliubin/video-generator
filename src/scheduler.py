"""
Background Scheduler - APScheduler for Channel Monitoring

Handles periodic channel checks and automatic video generation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from src.config.settings import get_settings
from src.core.pipeline import VideoPipeline
from src.stages.watcher import ChannelWatcher
from src.storage.database import Database, MonitoredChannel, VideoGenerationTask
from src.templates.manager import TemplateManager


class VideoScheduler:
    """
    Background scheduler for automatic channel monitoring and video generation.

    Checks monitored channels for new videos at configured intervals
    and automatically creates generation tasks.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.db = Database(get_settings().database_url)

    async def start(self) -> None:
        """Start the background scheduler."""
        if self.scheduler is not None and self.scheduler.running:
            print("Scheduler is already running")
            return

        # Create scheduler
        self.scheduler = AsyncIOScheduler()

        # Add channel monitoring job
        self.scheduler.add_job(
            self._check_all_channels,
            trigger=IntervalTrigger(minutes=5),  # Check every 5 minutes
            id="check_channels",
            name="Check all monitored channels for new videos",
            replace_existing=True,
        )

        # Start scheduler
        self.scheduler.start()
        print("✓ Background scheduler started")

    async def stop(self) -> None:
        """Stop the background scheduler."""
        if self.scheduler is not None and self.scheduler.running:
            self.scheduler.shutdown()
            print("✓ Background scheduler stopped")

    async def _check_all_channels(self) -> None:
        """
        Check all enabled monitored channels for new videos.

        Called periodically by the scheduler.
        """
        session = self.db.get_session()

        try:
            # Get all enabled channels
            result = session.execute(
                select(MonitoredChannel).where(
                    MonitoredChannel.enabled == True
                )
            ).scalars().all()

            if not result:
                return

            print(f"[Scheduler] Checking {len(result)} channel(s)...")

            # Process each channel
            for channel in result:
                try:
                    await self._check_channel(session, channel)
                except Exception as e:
                    print(f"[Scheduler] Error checking channel {channel.channel_id}: {e}")

        finally:
            session.close()

    async def _check_channel(
        self,
        session,
        channel: MonitoredChannel,
    ) -> None:
        """
        Check a single channel for new videos and create tasks.

        Args:
            session: Database session
            channel: MonitoredChannel to check
        """
        # Skip if recently checked (within interval)
        if channel.last_checked_at:
            minutes_since_check = (
                datetime.now(timezone.utc) - channel.last_checked_at
            ).total_seconds() / 60
            if minutes_since_check < channel.check_interval_minutes:
                return

        # Check for new videos
        try:
            watcher = ChannelWatcher()
            new_videos = await watcher.check_new_videos(channel.channel_id)

            if not new_videos:
                # Update last checked time even if no new videos
                channel.last_checked_at = datetime.now(timezone.utc)
                session.commit()
                return

            print(f"[Scheduler] Found {len(new_videos)} new video(s) from {channel.channel_name}")

            # Create tasks for new videos
            for video in new_videos:
                await self._create_video_task(session, channel, video)

            # Update last checked and last video
            channel.last_checked_at = datetime.now(timezone.utc)
            if new_videos:
                channel.last_video_id = new_videos[0].video_id

            session.commit()

        except Exception as e:
            print(f"[Scheduler] Error checking {channel.channel_name}: {e}")
            raise

    async def _create_video_task(
        self,
        session,
        channel: MonitoredChannel,
        video,
    ) -> None:
        """
        Create a video generation task for a new video.

        Args:
            session: Database session
            channel: MonitoredChannel
            video: VideoMetadata from watcher
        """
        import uuid

        # Check if task already exists
        existing = session.execute(
            select(VideoGenerationTask).where(
                VideoGenerationTask.video_id == video.video_id,
                VideoGenerationTask.template_id == channel.template_id,
            )
        ).scalar_one_or_none()

        if existing:
            return

        # Create new task
        task = VideoGenerationTask(
            id=str(uuid.uuid4()),
            video_id=video.video_id,
            channel_id=channel.id,
            template_id=channel.template_id,
            status="pending",
            progress=0,
            video_title=video.title,
            video_thumbnail=video.thumbnail_url,
            video_url=video.url,
        )

        session.add(task)
        session.flush()  # Get task ID

        print(f"[Scheduler] Created task for video: {video.title[:50]}...")

        # Start pipeline in background (non-blocking)
        asyncio.create_task(
            self._run_pipeline_for_task(
                task.id,
                video.video_id,
                channel.template_id,
            )
        )

    async def _run_pipeline_for_task(
        self,
        task_id: str,
        video_id: str,
        template_id: str,
    ) -> None:
        """
        Run the video generation pipeline for a task.

        Args:
            task_id: VideoGenerationTask ID
            video_id: YouTube video ID
            template_id: Style template ID
        """
        session = self.db.get_session()

        try:
            # Load template
            manager = TemplateManager()
            template = manager.load(template_id)

            # Initialize pipeline
            pipeline = VideoPipeline(template=template)

            # Update task status
            task = session.get(VideoGenerationTask, task_id)
            if not task:
                return

            task.status = "processing"
            task.started_at = datetime.now(timezone.utc)
            task.progress = 0
            task.current_stage = "fetcher"
            session.commit()

            # Run pipeline
            result = await pipeline.process_video(video_id)

            # Update task as completed
            task = session.get(VideoGenerationTask, task_id)
            if task:
                task.status = "completed"
                task.completed_at = datetime.now(timezone.utc)
                task.progress = 100
                task.current_stage = "renderer"
                task.output_path = result.video_path
                session.commit()

                print(f"[Scheduler] ✓ Completed task for video: {video_id}")

        except Exception as e:
            # Update task as failed
            task = session.get(VideoGenerationTask, task_id)
            if task:
                task.status = "failed"
                task.completed_at = datetime.now(timezone.utc)
                task.error_message = str(e)
                session.commit()

                print(f"[Scheduler] ✗ Failed task for video {video_id}: {e}")

        finally:
            session.close()

    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self.scheduler is not None and self.scheduler.running


# Global scheduler instance
_scheduler: Optional[VideoScheduler] = None


def get_scheduler() -> VideoScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = VideoScheduler()
    return _scheduler
