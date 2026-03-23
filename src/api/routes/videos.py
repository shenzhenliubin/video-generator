"""
Video Routes - Video Generation API

Endpoints for generating videos and checking task status.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, func
from pydantic import BaseModel

from src.api.models import (
    APIResponse,
    VideoGenerateRequest,
    VideoStatus,
    VideoTaskResponse,
    VideoListResponse,
)
from src.config.settings import get_settings
from src.core.models import StyleTemplate
from src.core.pipeline import VideoPipeline
from src.storage.database import Database, VideoGenerationTask
from src.templates.manager import TemplateManager

router = APIRouter(prefix="/api/videos", tags=["videos"])


def get_db() -> Database:
    """Get database instance."""
    settings = get_settings()
    return Database(settings.database_url)


async def run_pipeline_task(task_id: str, video_id: str, template_id: str):
    """
    Background task to run the video generation pipeline.

    Updates task status and progress during execution.
    """
    db = get_db()
    session = db.get_session()

    try:
        # Load template
        manager = TemplateManager()
        template = manager.load(template_id)

        # Initialize pipeline
        pipeline = VideoPipeline(template=template)

        # Update task status to processing
        task = session.get(VideoGenerationTask, task_id)
        if task:
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

    except Exception as e:
        # Update task as failed
        task = session.get(VideoGenerationTask, task_id)
        if task:
            task.status = "failed"
            task.completed_at = datetime.now(timezone.utc)
            task.error_message = str(e)
            session.commit()
    finally:
        session.close()


@router.post("/generate", response_model=VideoTaskResponse, status_code=status.HTTP_201_CREATED)
async def generate_video(
    request: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
) -> VideoTaskResponse:
    """
    Generate a video from a YouTube video ID.

    Creates a new video generation task and starts processing in the background.
    """
    db = get_db()
    session = db.get_session()

    try:
        # Validate template exists
        template_manager = TemplateManager()
        try:
            template = template_manager.load(request.template_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Template '{request.template_id}' not found",
            )

        # Check if task already exists for this video
        existing = session.execute(
            select(VideoGenerationTask).where(
                VideoGenerationTask.video_id == request.video_id,
                VideoGenerationTask.template_id == request.template_id,
            )
        ).scalar_one_or_none()

        if existing:
            # If existing task is failed, allow retry
            if existing.status == "failed":
                existing.status = "pending"
                existing.error_message = None
                existing.completed_at = None
                session.commit()
            # If existing task is pending/processing, return it
            elif existing.status in ["pending", "processing"]:
                pass
            # If completed, return existing
            else:
                return VideoTaskResponse(
                    id=existing.id,
                    video_id=existing.video_id,
                    channel_id=existing.channel_id,
                    template_id=existing.template_id,
                    status=VideoStatus(existing.status),
                    progress=existing.progress,
                    current_stage=existing.current_stage,
                    output_path=existing.output_path,
                    error_message=existing.error_message,
                    created_at=existing.created_at,
                    started_at=existing.started_at,
                    completed_at=existing.completed_at,
                    video_title=existing.video_title,
                    video_thumbnail=existing.video_thumbnail,
                    video_url=existing.video_url,
                )

        # Create new task
        task_id = str(uuid.uuid4())

        new_task = VideoGenerationTask(
            id=task_id,
            video_id=request.video_id,
            channel_id=request.channel_id,
            template_id=request.template_id,
            status="pending",
            progress=0,
            current_stage=None,
            # Basic video URL info
            video_url=f"https://www.youtube.com/watch?v={request.video_id}",
            video_thumbnail=f"https://img.youtube.com/vi/{request.video_id}/maxresdefault.jpg",
        )

        session.add(new_task)
        session.commit()
        session.refresh(new_task)

        # Start background task
        background_tasks.add_task(
            run_pipeline_task,
            task_id,
            request.video_id,
            request.template_id,
        )

        return VideoTaskResponse(
            id=new_task.id,
            video_id=new_task.video_id,
            channel_id=new_task.channel_id,
            template_id=new_task.template_id,
            status=VideoStatus(new_task.status),
            progress=new_task.progress,
            current_stage=new_task.current_stage,
            output_path=new_task.output_path,
            error_message=new_task.error_message,
            created_at=new_task.created_at,
            started_at=new_task.started_at,
            completed_at=new_task.completed_at,
            video_title=new_task.video_title,
            video_thumbnail=new_task.video_thumbnail,
            video_url=new_task.video_url,
        )
    finally:
        session.close()


@router.get("", response_model=VideoListResponse)
async def list_videos(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> VideoListResponse:
    """List video generation tasks with pagination."""
    db = get_db()
    session = db.get_session()

    try:
        # Build query
        query = select(VideoGenerationTask)
        if status_filter:
            query = query.where(VideoGenerationTask.status == status_filter)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = session.execute(count_query).scalar() or 0

        # Apply pagination
        query = query.order_by(VideoGenerationTask.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)

        result = session.execute(query).scalars().all()

        tasks = [
            VideoTaskResponse(
                id=t.id,
                video_id=t.video_id,
                channel_id=t.channel_id,
                template_id=t.template_id,
                status=VideoStatus(t.status),
                progress=t.progress,
                current_stage=t.current_stage,
                output_path=t.output_path,
                error_message=t.error_message,
                created_at=t.created_at,
                started_at=t.started_at,
                completed_at=t.completed_at,
                video_title=t.video_title,
                video_thumbnail=t.video_thumbnail,
                video_url=t.video_url,
            )
            for t in result
        ]

        pages = (total + limit - 1) // limit if total > 0 else 1

        return VideoListResponse(
            tasks=tasks,
            total=total,
            page=page,
            limit=limit,
        )
    finally:
        session.close()


@router.get("/{task_id}", response_model=VideoTaskResponse)
async def get_video_task(task_id: str) -> VideoTaskResponse:
    """Get a specific video task by ID."""
    db = get_db()
    session = db.get_session()

    try:
        task = session.get(VideoGenerationTask, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found",
            )

        return VideoTaskResponse(
            id=task.id,
            video_id=task.video_id,
            channel_id=task.channel_id,
            template_id=task.template_id,
            status=VideoStatus(task.status),
            progress=task.progress,
            current_stage=task.current_stage,
            output_path=task.output_path,
            error_message=task.error_message,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            video_title=task.video_title,
            video_thumbnail=task.video_thumbnail,
            video_url=task.video_url,
        )
    finally:
        session.close()


@router.get("/{task_id}/status", response_model=dict)
async def get_video_status(task_id: str) -> dict:
    """
    Get the current status of a video generation task.

    Returns a simplified status response for polling.
    """
    db = get_db()
    session = db.get_session()

    try:
        task = session.get(VideoGenerationTask, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found",
            )

        return {
            "task_id": task.id,
            "status": task.status,
            "progress": task.progress,
            "current_stage": task.current_stage,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error": task.error_message,
        }
    finally:
        session.close()


@router.post("/{task_id}/cancel", response_model=APIResponse)
async def cancel_video_task(task_id: str) -> APIResponse:
    """
    Cancel a video generation task.

    Only pending or processing tasks can be cancelled.
    """
    db = get_db()
    session = db.get_session()

    try:
        task = session.get(VideoGenerationTask, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found",
            )

        if task.status in ["completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel task with status '{task.status}'",
            )

        task.status = "failed"
        task.error_message = "Cancelled by user"
        task.completed_at = datetime.now(timezone.utc)
        session.commit()

        return APIResponse(
            success=True,
            message=f"Task '{task_id}' cancelled successfully",
        )
    finally:
        session.close()


@router.delete("/{task_id}", response_model=APIResponse)
async def delete_video_task(task_id: str) -> APIResponse:
    """
    Delete a video generation task.

    Removes the task record. The generated video file is not deleted.
    """
    db = get_db()
    session = db.get_session()

    try:
        task = session.get(VideoGenerationTask, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found",
            )

        session.delete(task)
        session.commit()

        return APIResponse(
            success=True,
            message=f"Task '{task_id}' deleted successfully",
        )
    finally:
        session.close()
