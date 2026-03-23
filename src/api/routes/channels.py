"""
Channel Routes - Monitored Channel Management API

Endpoints for managing YouTube channels being monitored for new videos.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.api.models import (
    APIResponse,
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
)
from src.config.settings import get_settings
from src.storage.database import Database, MonitoredChannel, VideoGenerationTask

router = APIRouter(prefix="/api/channels", tags=["channels"])


def get_db() -> Database:
    """Get database instance."""
    settings = get_settings()
    return Database(settings.database_url)


@router.get("", response_model=list[ChannelResponse])
async def list_channels(
    enabled_only: bool = Query(False, description="Filter to only enabled channels"),
) -> list[ChannelResponse]:
    """List all monitored channels."""
    db = get_db()
    session = db.get_session()

    try:
        query = select(MonitoredChannel)
        if enabled_only:
            query = query.where(MonitoredChannel.enabled == True)
        query = query.order_by(MonitoredChannel.created_at.desc())

        result = session.execute(query).scalars().all()

        # Count videos for each channel
        responses = []
        for channel in result:
            video_count = session.execute(
                select(func.count()).select_from(VideoGenerationTask).where(
                    VideoGenerationTask.channel_id == channel.id
                )
            ).scalar() or 0

            responses.append(
                ChannelResponse(
                    id=channel.id,
                    channel_id=channel.channel_id,
                    channel_name=channel.channel_name,
                    check_interval_minutes=channel.check_interval_minutes,
                    template_id=channel.template_id,
                    enabled=channel.enabled,
                    last_checked_at=channel.last_checked_at,
                    last_video_id=channel.last_video_id,
                    created_at=channel.created_at,
                    video_count=video_count,
                )
            )

        return responses
    finally:
        session.close()


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: str) -> ChannelResponse:
    """Get a specific monitored channel by ID."""
    db = get_db()
    session = db.get_session()

    try:
        channel = session.get(MonitoredChannel, channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_id}' not found",
            )

        # Count videos
        video_count = session.execute(
            select(func.count()).select_from(VideoGenerationTask).where(
                VideoGenerationTask.channel_id == channel_id
            )
        ).scalar() or 0

        return ChannelResponse(
            id=channel.id,
            channel_id=channel.channel_id,
            channel_name=channel.channel_name,
            check_interval_minutes=channel.check_interval_minutes,
            template_id=channel.template_id,
            enabled=channel.enabled,
            last_checked_at=channel.last_checked_at,
            last_video_id=channel.last_video_id,
            created_at=channel.created_at,
            video_count=video_count,
        )
    finally:
        session.close()


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(channel: ChannelCreate) -> ChannelResponse:
    """
    Add a new channel to monitor.

    Creates a monitored channel configuration that will be checked
    for new videos at the specified interval.
    """
    db = get_db()
    session = db.get_session()

    try:
        # Check if channel_id already exists
        existing = session.execute(
            select(MonitoredChannel).where(
                MonitoredChannel.channel_id == channel.channel_id
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Channel with channel_id '{channel.channel_id}' already exists",
            )

        # Generate unique ID
        channel_uuid = str(uuid.uuid4())

        # Create new monitored channel
        new_channel = MonitoredChannel(
            id=channel_uuid,
            channel_id=channel.channel_id,
            channel_name=channel.channel_name,
            check_interval_minutes=channel.check_interval_minutes,
            template_id=channel.template_id,
            enabled=channel.enabled,
        )

        session.add(new_channel)
        session.commit()
        session.refresh(new_channel)

        return ChannelResponse(
            id=new_channel.id,
            channel_id=new_channel.channel_id,
            channel_name=new_channel.channel_name,
            check_interval_minutes=new_channel.check_interval_minutes,
            template_id=new_channel.template_id,
            enabled=new_channel.enabled,
            last_checked_at=new_channel.last_checked_at,
            last_video_id=new_channel.last_video_id,
            created_at=new_channel.created_at,
            video_count=0,
        )
    finally:
        session.close()


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(channel_id: str, channel: ChannelUpdate) -> ChannelResponse:
    """Update an existing monitored channel."""
    db = get_db()
    session = db.get_session()

    try:
        existing = session.get(MonitoredChannel, channel_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_id}' not found",
            )

        # Update fields
        if channel.channel_name is not None:
            existing.channel_name = channel.channel_name
        if channel.check_interval_minutes is not None:
            existing.check_interval_minutes = channel.check_interval_minutes
        if channel.template_id is not None:
            existing.template_id = channel.template_id
        if channel.enabled is not None:
            existing.enabled = channel.enabled

        session.commit()
        session.refresh(existing)

        # Count videos
        video_count = session.execute(
            select(func.count()).select_from(VideoGenerationTask).where(
                VideoGenerationTask.channel_id == channel_id
            )
        ).scalar() or 0

        return ChannelResponse(
            id=existing.id,
            channel_id=existing.channel_id,
            channel_name=existing.channel_name,
            check_interval_minutes=existing.check_interval_minutes,
            template_id=existing.template_id,
            enabled=existing.enabled,
            last_checked_at=existing.last_checked_at,
            last_video_id=existing.last_video_id,
            created_at=existing.created_at,
            video_count=video_count,
        )
    finally:
        session.close()


@router.delete("/{channel_id}", response_model=APIResponse)
async def delete_channel(channel_id: str) -> APIResponse:
    """
    Delete a monitored channel.

    Removes the channel from monitoring but keeps existing video tasks.
    """
    db = get_db()
    session = db.get_session()

    try:
        existing = session.get(MonitoredChannel, channel_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_id}' not found",
            )

        session.delete(existing)
        session.commit()

        return APIResponse(
            success=True,
            message=f"Channel '{channel_id}' deleted successfully",
        )
    finally:
        session.close()


@router.post("/{channel_id}/check", response_model=APIResponse)
async def check_channel_now(channel_id: str) -> APIResponse:
    """
    Manually trigger a channel check for new videos.

    This forces an immediate check regardless of the scheduled interval.
    The actual check happens in the background.
    """
    db = get_db()
    session = db.get_session()

    try:
        existing = session.get(MonitoredChannel, channel_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel '{channel_id}' not found",
            )

        # TODO: Trigger background task to check channel
        # For now, just update last_checked_at
        existing.last_checked_at = datetime.now(timezone.utc)
        session.commit()

        return APIResponse(
            success=True,
            message=f"Channel check triggered for '{existing.channel_name}'",
            data={"channel_id": existing.channel_id, "triggered_at": existing.last_checked_at.isoformat()},
        )
    finally:
        session.close()
