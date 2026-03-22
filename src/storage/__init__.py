"""
Storage layer - Database and file storage.

Exports:
    - Database: Database connection manager
    - Base: SQLAlchemy base class for models
    - Channel, Video, ProcessingStage: Database models
    - ChannelRepository, VideoRepository, ProcessingStageRepository: Repository classes
    - FileStore: File storage for generated assets
    - CheckpointStore: Checkpoint storage for pipeline recovery
"""

from src.storage.checkpoint import CheckpointStore
from src.storage.database import (
    Base,
    Channel,
    Database,
    ProcessingStage,
    Video,
)
from src.storage.file_store import FileStore
from src.storage.repositories import (
    ChannelRepository,
    ProcessingStageRepository,
    VideoRepository,
)

__all__ = [
    # Database
    "Database",
    "Base",
    # Models
    "Channel",
    "Video",
    "ProcessingStage",
    # Repositories
    "ChannelRepository",
    "VideoRepository",
    "ProcessingStageRepository",
    # Storage
    "FileStore",
    "CheckpointStore",
]
