"""
Core Data Models - Pydantic Models for Pipeline Data

This module defines all data models used throughout the pipeline.
Each stage has well-defined input/output contracts.

All models use Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# YouTube & Input Models
# =============================================================================

class VideoMetadata(BaseModel):
    """Metadata for a YouTube video."""

    video_id: str
    channel_id: str
    channel_name: str
    title: str
    description: str
    published_at: datetime
    duration: int = Field(ge=0)  # seconds
    thumbnail_url: str
    url: str


# =============================================================================
# Transcript Models
# =============================================================================

class TranscriptSegment(BaseModel):
    """A single segment of subtitle text with timing."""

    text: str
    start: float  # seconds
    duration: float  # seconds


class Transcript(BaseModel):
    """Full transcript with segmented text."""

    video_id: str
    raw_text: str
    segments: list[TranscriptSegment]
    language: str = "en"

    @field_validator("segments")
    @classmethod
    def segments_not_empty(cls, v: list[TranscriptSegment]) -> list[TranscriptSegment]:
        if not v:
            raise ValueError("segments cannot be empty")
        return v


# =============================================================================
# Content Analysis Models
# =============================================================================

class ParsedContent(BaseModel):
    """Result of parsing and cleaning subtitle content."""

    video_id: str
    original_text: str  # Raw text from transcript
    clean_text: str  # Cleaned text with artifacts removed
    segments: list[dict[str, Any]]  # Parsed segments with cleaned text
    sections: list[dict[str, Any]]  # Logical sections based on timing gaps
    language: str = "en"
    word_count: int = Field(ge=0)


class ContentAnalysis(BaseModel):
    """Result of LLM content analysis."""

    video_id: str
    main_points: list[str] = Field(min_length=1, max_length=5)
    summary: str = Field(min_length=10)
    topics: list[str] = Field(default_factory=list)
    sentiment: str | None = None


# =============================================================================
# Style & Rewrite Models
# =============================================================================

class TemplateCategory(str, Enum):
    """Predefined style template categories."""

    DRAMATIC = "dramatic"
    HUMOROUS = "humorous"
    EDUCATIONAL = "educational"
    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    NEWS = "news"


class StyleTemplate(BaseModel):
    """Style template configuration."""

    id: str
    name: str
    category: TemplateCategory
    description: str

    # Provider selections
    llm_provider: str
    image_provider: str
    tts_provider: str

    # Style parameters
    scene_duration: int = Field(default=5, ge=1, le=30)  # seconds per scene
    image_style_prompt: str = ""
    voice_id: str | None = None
    background_music: str | None = None

    # LLM parameters
    system_prompt: str = ""
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1000, ge=100)


class RewrittenScript(BaseModel):
    """Result of content rewriting."""

    original_video_id: str
    template_id: str
    title: str
    script: str = Field(min_length=50)
    style_notes: str = ""


# =============================================================================
# Storyboard Models
# =============================================================================

class Scene(BaseModel):
    """A single scene in the storyboard."""

    scene_number: int
    narration: str
    visual_description: str
    duration: int  # seconds
    camera_movement: str = "static"
    mood: str = "neutral"


class Storyboard(BaseModel):
    """Complete storyboard for video generation."""

    script_id: str
    scenes: list[Scene]
    total_duration: int

    @field_validator("scenes")
    @classmethod
    def scenes_not_empty(cls, v: list[Scene]) -> list[Scene]:
        if not v:
            raise ValueError("scenes cannot be empty")
        return v


# =============================================================================
# Generation Models
# =============================================================================

class GeneratedImage(BaseModel):
    """Result of image generation."""

    scene_number: int
    image_path: str
    prompt_used: str
    provider: str
    width: int
    height: int


class GeneratedAudio(BaseModel):
    """Result of audio generation."""

    scene_number: int
    audio_path: str
    text: str
    provider: str
    voice_id: str | None = None
    duration: float  # seconds


class SubtitleSentence(BaseModel):
    """
    A single sentence subtitle with timing information.

    Used for sentence-by-subtitle display where each sentence appears
    as it is spoken in the audio.
    """

    text: str  # The sentence text
    start_time: float  # When this sentence appears (relative to scene start)
    duration: float  # How long this sentence displays


class SceneData(BaseModel):
    """
    Complete scene data for rendering.

    Combines storyboard scene, generated image, and generated audio
    into a single data structure for video rendering.
    """

    scene_number: int
    narration: str  # Full subtitle text (can be split into sentences)
    visual_description: str  # From storyboard
    duration: float  # Audio duration (actual, not estimated)
    camera_movement: str = "static"
    mood: str = "neutral"
    start_time: float = 0.0  # Calculated when processing multiple scenes
    image_path: str = ""  # Path to generated image
    audio_path: str = ""  # Path to generated audio
    image_prompt: str = ""  # Prompt used for image generation
    subtitle_sentences: list[SubtitleSentence] = Field(default_factory=list)  # Optional: sentence-level breakdown


# =============================================================================
# Output Models
# =============================================================================

class VideoOutput(BaseModel):
    """Final generated video metadata."""

    storyboard_id: str
    video_path: str
    duration: int  # seconds
    resolution: str  # e.g., "1920x1080"
    format: str = "mp4"
    scenes_count: int
    created_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Pipeline State Models
# =============================================================================

class PipelineStage(str, Enum):
    """Stages in the processing pipeline."""

    WATCHER = "watcher"
    FETCHER = "fetcher"
    PARSER = "parser"
    ANALYZER = "analyzer"
    WRITER = "writer"
    DIRECTOR = "director"
    ARTIST = "artist"
    VOICE = "voice"
    RENDERER = "renderer"


class Checkpoint(BaseModel):
    """Pipeline checkpoint for recovery."""

    video_id: str
    stage: PipelineStage
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = True
    error_message: str | None = None


class PipelineResult(BaseModel):
    """Result of a single pipeline stage execution."""

    stage: PipelineStage
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    duration: float  # seconds


# =============================================================================
# Configuration Models
# =============================================================================

class ProviderConfig(BaseModel):
    """Configuration for a provider."""

    type: str  # "llm", "image", "tts"
    name: str  # "openai", "anthropic", etc.
    config: dict[str, Any] = Field(default_factory=dict)


class SystemConfig(BaseModel):
    """Global system configuration."""

    # Processing limits
    max_concurrent_videos: int = Field(default=3, ge=1, le=10)
    checkpoint_interval: int = Field(default=60, ge=10)  # seconds

    # Paths
    output_dir: str = "./output"
    temp_dir: str = "./temp"
    database_url: str = "sqlite:///./video_generator.db"

    # Logging
    log_level: str = "INFO"
    log_file: str = "video_generator.log"

    # Default providers
    default_llm_provider: str = "openai"
    default_image_provider: str = "openai"
    default_tts_provider: str = "elevenlabs"

    # Fallback providers (used when primary fails)
    fallback_llm_provider: str | None = None
    fallback_image_provider: str | None = None
    fallback_tts_provider: str | None = None
