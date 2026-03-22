"""
Unit tests for Database models and repositories.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.storage.database import Base, Channel, Database, ProcessingStage, Video
from src.storage.repositories import (
    ChannelRepository,
    ProcessingStageRepository,
    VideoRepository,
)


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(in_memory_db):
    """Create a database session for testing."""
    session = Session(bind=in_memory_db)
    yield session
    session.close()


class TestChannelModel:
    """Test Channel model."""

    def test_create_channel(self, db_session: Session) -> None:
        """Test creating a channel."""
        channel = Channel(
            channel_id="UC_test123",
            channel_name="Test Channel",
            channel_url="https://www.youtube.com/channel/UC_test123",
            is_active=True,
            check_interval_seconds=300,
        )
        db_session.add(channel)
        db_session.commit()

        assert channel.id is not None
        assert channel.channel_id == "UC_test123"
        assert channel.is_active is True

    def test_channel_defaults(self, db_session: Session) -> None:
        """Test default values for channel."""
        channel = Channel(
            channel_id="UC_defaults",
            channel_name="Defaults Channel",
        )
        db_session.add(channel)
        db_session.commit()

        assert channel.is_active is True
        assert channel.check_interval_seconds == 300
        assert channel.last_checked_at is None


class TestVideoModel:
    """Test Video model."""

    def test_create_video(self, db_session: Session) -> None:
        """Test creating a video."""
        video = Video(
            video_id="vid123",
            channel_id="UC_test",
            title="Test Video",
            url="https://www.youtube.com/watch?v=vid123",
            published_at=datetime.now(timezone.utc),
            status="pending",
        )
        db_session.add(video)
        db_session.commit()

        assert video.id is not None
        assert video.video_id == "vid123"
        assert video.status == "pending"

    def test_video_status_enum(self, db_session: Session) -> None:
        """Test different video statuses."""
        for status in ["pending", "processing", "completed", "failed"]:
            video = Video(
                video_id=f"vid_{status}",
                channel_id="UC_test",
                title=f"Video {status}",
                url=f"https://www.youtube.com/watch?v=vid_{status}",
                published_at=datetime.now(timezone.utc),
                status=status,
            )
            db_session.add(video)
        db_session.commit()

        videos = db_session.query(Video).all()
        assert len(videos) == 4


class TestProcessingStageModel:
    """Test ProcessingStage model."""

    def test_create_processing_stage(self, db_session: Session) -> None:
        """Test creating a processing stage."""
        stage = ProcessingStage(
            video_id="vid123",
            stage_name="fetcher",
            status="pending",
        )
        db_session.add(stage)
        db_session.commit()

        assert stage.id is not None
        assert stage.stage_name == "fetcher"
        assert stage.status == "pending"

    def test_stage_timing(self, db_session: Session) -> None:
        """Test stage timing information."""
        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)

        stage = ProcessingStage(
            video_id="vid123",
            stage_name="parser",
            status="completed",
            started_at=started,
            completed_at=completed,
            duration_seconds=5,
        )
        db_session.add(stage)
        db_session.commit()

        assert stage.started_at is not None
        assert stage.completed_at is not None
        assert stage.duration_seconds == 5


class TestChannelRepository:
    """Test Channel repository operations."""

    def test_get_or_create_new(self, db_session: Session) -> None:
        """Test get_or_create with a new channel."""
        repo = ChannelRepository(db_session)

        channel = repo.get_or_create(
            channel_id="UC_new",
            channel_name="New Channel",
            channel_url="https://www.youtube.com/channel/UC_new",
        )

        assert channel.id is not None
        assert channel.channel_id == "UC_new"

    def test_get_or_create_existing(self, db_session: Session) -> None:
        """Test get_or_create with an existing channel."""
        repo = ChannelRepository(db_session)

        # First call creates
        channel1 = repo.get_or_create(
            channel_id="UC_existing",
            channel_name="Existing Channel",
        )

        # Second call should return the same channel
        channel2 = repo.get_or_create(
            channel_id="UC_existing",
            channel_name="Different Name",  # This should be ignored
        )

        assert channel1.id == channel2.id
        assert channel2.channel_name == "Existing Channel"  # Name not updated

    def test_update_last_checked(self, db_session: Session) -> None:
        """Test updating last_checked timestamp."""
        repo = ChannelRepository(db_session)

        channel = repo.create(
            channel_id="UC_checked",
            channel_name="Checked Channel",
        )

        timestamp = datetime(2025, 3, 20, 12, 0, 0)
        repo.update_last_checked("UC_checked", timestamp)

        # Refresh from database
        db_session.refresh(channel)
        assert channel.last_checked_at == timestamp

    def test_list_active(self, db_session: Session) -> None:
        """Test listing active channels."""
        repo = ChannelRepository(db_session)

        # Create active and inactive channels
        repo.create("UC_active1", "Active 1")
        repo.create("UC_active2", "Active 2")

        inactive = repo.create("UC_inactive", "Inactive")
        inactive.is_active = False
        db_session.commit()

        active_channels = repo.list_active()
        assert len(active_channels) == 2
        assert all(c.is_active for c in active_channels)


class TestVideoRepository:
    """Test Video repository operations."""

    def test_create_video(self, db_session: Session) -> None:
        """Test creating a video."""
        repo = VideoRepository(db_session)

        video = repo.create(
            video_id="vid_create",
            channel_id="UC_test",
            title="Created Video",
            url="https://www.youtube.com/watch?v=vid_create",
            published_at=datetime.now(timezone.utc),
        )

        assert video.id is not None
        assert video.video_id == "vid_create"

    def test_update_status(self, db_session: Session) -> None:
        """Test updating video status."""
        repo = VideoRepository(db_session)

        video = repo.create(
            video_id="vid_status",
            channel_id="UC_test",
            title="Status Video",
            url="https://www.youtube.com/watch?v=vid_status",
            published_at=datetime.now(timezone.utc),
        )

        repo.update_status(
            "vid_status",
            "processing",
        )

        db_session.refresh(video)
        assert video.status == "processing"

    def test_update_status_with_output(self, db_session: Session) -> None:
        """Test updating video status with output path."""
        repo = VideoRepository(db_session)

        video = repo.create(
            video_id="vid_output",
            channel_id="UC_test",
            title="Output Video",
            url="https://www.youtube.com/watch?v=vid_output",
            published_at=datetime.now(timezone.utc),
        )

        repo.update_status(
            "vid_output",
            "completed",
            output_path="/output/vid_output.mp4",
            template_used="dramatic",
        )

        db_session.refresh(video)
        assert video.status == "completed"
        assert video.output_path == "/output/vid_output.mp4"
        assert video.template_used == "dramatic"

    def test_list_pending(self, db_session: Session) -> None:
        """Test listing pending videos."""
        repo = VideoRepository(db_session)

        # Create videos with different statuses
        repo.create("vid_pending1", "UC_test", "P1", "url1", datetime.now(timezone.utc))
        repo.create("vid_pending2", "UC_test", "P2", "url2", datetime.now(timezone.utc))

        processing = repo.create("vid_processing", "UC_test", "Proc", "url3", datetime.now(timezone.utc))
        repo.update_status("vid_processing", "processing")

        pending = repo.list_pending()
        assert len(pending) == 2
        assert all(v.status == "pending" for v in pending)


class TestProcessingStageRepository:
    """Test ProcessingStage repository operations."""

    def test_create_stage(self, db_session: Session) -> None:
        """Test creating a processing stage."""
        repo = ProcessingStageRepository(db_session)

        stage = repo.create("vid_stage", "fetcher")

        assert stage.id is not None
        assert stage.video_id == "vid_stage"
        assert stage.stage_name == "fetcher"
        assert stage.status == "pending"

    def test_start_stage(self, db_session: Session) -> None:
        """Test starting a processing stage."""
        repo = ProcessingStageRepository(db_session)

        stage = repo.start_stage("vid_start", "parser")

        assert stage.status == "in_progress"
        assert stage.started_at is not None

    def test_complete_stage(self, db_session: Session) -> None:
        """Test completing a processing stage."""
        repo = ProcessingStageRepository(db_session)

        repo.start_stage("vid_complete", "analyzer")
        repo.complete_stage("vid_complete", "analyzer", "/checkpoints/vid_complete/analyzer.json")

        stage = repo.get_stage("vid_complete", "analyzer")
        assert stage.status == "completed"
        assert stage.completed_at is not None
        assert stage.checkpoint_path == "/checkpoints/vid_complete/analyzer.json"

    def test_fail_stage(self, db_session: Session) -> None:
        """Test failing a processing stage."""
        repo = ProcessingStageRepository(db_session)

        repo.start_stage("vid_fail", "writer")
        repo.fail_stage("vid_fail", "writer", "LLM API timeout")

        stage = repo.get_stage("vid_fail", "writer")
        assert stage.status == "failed"
        assert "LLM API timeout" in stage.error_message

    def test_get_latest_stage(self, db_session: Session) -> None:
        """Test getting the latest completed stage."""
        repo = ProcessingStageRepository(db_session)

        # Complete stages in order
        repo.start_stage("vid_latest", "fetcher")
        repo.complete_stage("vid_latest", "fetcher")

        repo.start_stage("vid_latest", "parser")
        repo.complete_stage("vid_latest", "parser")

        repo.start_stage("vid_latest", "analyzer")
        # analyzer not completed yet

        latest = repo.get_latest_stage("vid_latest")
        assert latest == "parser"

    def test_get_all_stages(self, db_session: Session) -> None:
        """Test getting all stages for a video."""
        repo = ProcessingStageRepository(db_session)

        # Create multiple stages
        for stage_name in ["fetcher", "parser", "analyzer"]:
            repo.create("vid_all", stage_name)

        stages = repo.get_all_stages("vid_all")
        assert len(stages) == 3
        stage_names = [s.stage_name for s in stages]
        assert stage_names == ["fetcher", "parser", "analyzer"]
