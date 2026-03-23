"""
API Models - Request and Response Schemas for FastAPI

Defines Pydantic models for HTTP API contracts.
Separate from core models which are used internally in the pipeline.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Common Models
# =============================================================================

class APIResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool = True
    message: str | None = None
    data: Any | None = None
    error: str | None = None


class PaginatedResponse(BaseModel):
    """Paginated API response."""

    items: list[Any]
    total: int
    page: int = 1
    limit: int = 20
    pages: int = 1


# =============================================================================
# Template Models
# =============================================================================

class TemplateCreate(BaseModel):
    """Request to create a new style template."""

    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1, max_length=500)

    # Provider selections
    llm_provider: str = Field(..., min_length=1)
    llm_model: str | None = None
    image_provider: str = Field(..., min_length=1)
    image_model: str | None = None
    tts_provider: str = Field(..., min_length=1)
    tts_model: str | None = None

    # Style parameters
    scene_duration: int = Field(default=5, ge=1, le=30)
    image_style_prompt: str = Field(default="", max_length=1000)
    voice_id: str | None = None

    # LLM parameters
    system_prompt: str = Field(default="", max_length=5000)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1000, ge=100, le=32000)


class TemplateUpdate(BaseModel):
    """Request to update a style template."""

    name: str | None = Field(None, min_length=1, max_length=100)
    category: str | None = None
    description: str | None = Field(None, min_length=1, max_length=500)

    # Provider selections
    llm_provider: str | None = None
    llm_model: str | None = None
    image_provider: str | None = None
    image_model: str | None = None
    tts_provider: str | None = None
    tts_model: str | None = None

    # Style parameters
    scene_duration: int | None = Field(None, ge=1, le=30)
    image_style_prompt: str | None = Field(None, max_length=1000)
    voice_id: str | None = None

    # LLM parameters
    system_prompt: str | None = Field(None, max_length=5000)
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=100, le=32000)


class TemplateResponse(BaseModel):
    """Response with template details."""

    id: str
    name: str
    category: str
    description: str

    # Provider selections
    llm_provider: str
    llm_model: str | None
    image_provider: str
    image_model: str | None
    tts_provider: str
    tts_model: str | None

    # Style parameters
    scene_duration: int
    image_style_prompt: str
    voice_id: str | None

    # LLM parameters
    system_prompt: str
    temperature: float
    max_tokens: int


# =============================================================================
# Channel Models
# =============================================================================

class ChannelCreate(BaseModel):
    """Request to add a monitored channel."""

    channel_id: str = Field(..., min_length=1, max_length=50)
    channel_name: str = Field(..., min_length=1, max_length=100)
    check_interval_minutes: int = Field(default=60, ge=5, le=10080)  # 5min to 1 week
    template_id: str = Field(..., min_length=1)
    enabled: bool = True


class ChannelUpdate(BaseModel):
    """Request to update a monitored channel."""

    channel_name: str | None = Field(None, min_length=1, max_length=100)
    check_interval_minutes: int | None = Field(None, ge=5, le=10080)
    template_id: str | None = None
    enabled: bool | None = None


class ChannelResponse(BaseModel):
    """Response with channel details."""

    id: str
    channel_id: str
    channel_name: str
    check_interval_minutes: int
    template_id: str
    enabled: bool
    last_checked_at: datetime | None
    last_video_id: str | None
    created_at: datetime
    video_count: int = Field(default=0)  # Number of videos generated from this channel


# =============================================================================
# Video Models
# =============================================================================

class VideoGenerateRequest(BaseModel):
    """Request to generate a video."""

    video_id: str = Field(..., min_length=1, max_length=20)
    template_id: str = Field(..., min_length=1)
    channel_id: str | None = None  # Optional: if from monitored channel


class VideoStatus(str, Enum):
    """Video generation task status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoTaskResponse(BaseModel):
    """Response with video task details."""

    id: str
    video_id: str
    channel_id: str | None
    template_id: str
    status: VideoStatus
    progress: int  # 0-100
    current_stage: str | None
    output_path: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    # Additional info
    video_title: str | None
    video_thumbnail: str | None
    video_url: str | None


class VideoListResponse(BaseModel):
    """Response with list of video tasks."""

    tasks: list[VideoTaskResponse]
    total: int
    page: int
    limit: int


# =============================================================================
# System Models
# =============================================================================

class SystemStatus(BaseModel):
    """System status response."""

    status: str
    version: str
    uptime_seconds: float
    scheduler_running: bool
    monitored_channels: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int


class HealthResponse(BaseModel):
    """Health check response."""

    healthy: bool
    database: bool
    scheduler: bool
    providers: dict[str, bool]  # provider_name -> available
