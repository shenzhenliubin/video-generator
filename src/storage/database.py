"""
Database Storage - SQLAlchemy Models and Setup

Database models for storing video metadata, processing state, and channel information.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
from sqlalchemy import create_engine


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class Channel(Base):
    """
    YouTube channels being monitored.

    Stores channel information and the last check timestamp
    to avoid duplicate processing.
    """
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    channel_name: Mapped[str] = mapped_column(String(255))
    channel_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Tracking state
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_video_published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Channel(channel_id={self.channel_id}, name={self.channel_name})>"


class Video(Base):
    """
    YouTube videos detected from monitored channels.

    Stores metadata and processing status for each video.
    """
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    # Foreign key to channel
    channel_id: Mapped[str] = mapped_column(String(50), index=True)

    # Video metadata from YouTube
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # URLs and thumbnails
    url: Mapped[str] = mapped_column(String(500))
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Processing state
    status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True
    )  # pending, processing, completed, failed

    # Output
    output_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    template_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failed_at_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships will be accessed via backref from ProcessingStage

    def __repr__(self) -> str:
        return f"<Video(video_id={self.video_id}, title={self.title}, status={self.status})>"


class ProcessingStage(Base):
    """
    Track processing progress for each video through the pipeline.

    Records the status of each stage (fetcher, parser, analyzer, writer,
    director, artist, voice, renderer) for recovery and monitoring.
    """
    __tablename__ = "processing_stages"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key to video
    video_id: Mapped[str] = mapped_column(String(20), index=True)

    # Stage information
    stage_name: Mapped[str] = mapped_column(String(100), index=True)
    """Pipeline stage: fetcher, parser, analyzer, writer, director, artist, voice, renderer"""

    status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True
    )  # pending, in_progress, completed, failed

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Checkpoint reference (file path to JSON checkpoint)
    checkpoint_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<ProcessingStage(video_id={self.video_id}, "
            f"stage={self.stage_name}, status={self.status})>"
        )


class Database:
    """Database connection manager."""

    def __init__(self, url: str) -> None:
        self.engine = create_engine(
            url,
            echo=False,  # Set to True for SQL query logging
            connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Create all tables."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all tables (use with caution!)."""
        Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def init_sample_data(self) -> None:
        """Initialize sample data for development."""
        session = self.get_session()
        try:
            # Check if data already exists
            if session.query(Channel).count() > 0:
                return

            # Add sample channel
            sample_channel = Channel(
                channel_id="UC_sample",
                channel_name="Sample Channel",
                channel_url="https://www.youtube.com/channel/UC_sample",
                is_active=True,
                check_interval_seconds=300,
            )
            session.add(sample_channel)
            session.commit()

        finally:
            session.close()
