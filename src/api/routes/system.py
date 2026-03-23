"""
System Routes - Health Check and System Status

Endpoints for monitoring system health and status.
"""

import time
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select, func

from src.api.models import HealthResponse, SystemStatus
from src.config.settings import get_settings
from src.scheduler import get_scheduler
from src.storage.database import Database, MonitoredChannel, VideoGenerationTask

router = APIRouter(prefix="/api/system", tags=["system"])


def get_db() -> Database:
    """Get database instance."""
    settings = get_settings()
    return Database(settings.database_url)


# Track server start time
_server_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the health status of the system and its components.
    """
    db = get_db()
    session = db.get_session()

    try:
        # Check database
        db_healthy = False
        try:
            session.execute(select(func.count()).select_from(MonitoredChannel)).scalar()
            db_healthy = True
        except Exception:
            pass

        # Check scheduler
        scheduler = get_scheduler()
        scheduler_healthy = scheduler.is_running()

        # Check providers (TODO: actual provider health checks)
        providers_healthy = {
            "siliconflow": True,  # Placeholder
            "openai": True,  # Placeholder
            "anthropic": True,  # Placeholder
        }

        all_healthy = db_healthy and scheduler_healthy

        return HealthResponse(
            healthy=all_healthy,
            database=db_healthy,
            scheduler=scheduler_healthy,
            providers=providers_healthy,
        )
    finally:
        session.close()


@router.get("/status", response_model=SystemStatus)
async def system_status() -> SystemStatus:
    """
    Get system status information.

    Returns statistics about monitored channels, tasks, and system uptime.
    """
    db = get_db()
    session = db.get_session()

    try:
        # Get channel count
        channel_count = session.execute(
            select(func.count()).select_from(MonitoredChannel).where(
                MonitoredChannel.enabled == True
            )
        ).scalar() or 0

        # Get task counts by status
        active_count = session.execute(
            select(func.count()).select_from(VideoGenerationTask).where(
                VideoGenerationTask.status == "processing"
            )
        ).scalar() or 0

        completed_count = session.execute(
            select(func.count()).select_from(VideoGenerationTask).where(
                VideoGenerationTask.status == "completed"
            )
        ).scalar() or 0

        failed_count = session.execute(
            select(func.count()).select_from(VideoGenerationTask).where(
                VideoGenerationTask.status == "failed"
            )
        ).scalar() or 0

        # Calculate uptime
        uptime = time.time() - _server_start_time

        # Check scheduler status
        scheduler = get_scheduler()
        scheduler_running = scheduler.is_running()

        return SystemStatus(
            status="healthy",
            version="0.2.0",  # Phase 2
            uptime_seconds=uptime,
            scheduler_running=scheduler_running,
            monitored_channels=channel_count,
            active_tasks=active_count,
            completed_tasks=completed_count,
            failed_tasks=failed_count,
        )
    finally:
        session.close()


@router.get("/info")
async def system_info() -> dict[str, Any]:
    """
    Get system information.

    Returns details about the system configuration and capabilities.
    """
    settings = get_settings()

    return {
        "name": "Video Generator API",
        "version": "0.2.0",
        "description": "YouTube content repurposing pipeline - automated video generation",
        "environment": {
            "default_llm_provider": settings.default_llm_provider,
            "default_image_provider": settings.default_image_provider,
            "default_tts_provider": settings.default_tts_provider,
            "max_concurrent_videos": settings.max_concurrent_videos,
        },
        "features": {
            "template_management": True,
            "channel_monitoring": True,
            "video_generation": True,
            "background_processing": True,
            "progress_tracking": True,
        },
    }
