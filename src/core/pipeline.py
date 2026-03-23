"""
Pipeline Orchestrator - Video Generation Pipeline

Coordinates all 9 stages of the video generation pipeline:
1. Watcher - Monitor YouTube channels for new videos
2. Fetcher - Download subtitle files
3. Parser - Clean and segment subtitle text
4. Analyzer - Extract main points using LLM
5. Writer - Rewrite content in target style using LLM
6. Director - Create storyboard with scene descriptions
7. Artist - Generate images for each scene
8. Voice - Generate audio for narration
9. Renderer - Combine images and audio into video

Features:
- Checkpoint-based recovery from failures
- Concurrent video processing
- Progress tracking and logging
- Template-based style configuration
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
)

from src.config.settings import get_settings
from src.core.models import (
    Checkpoint,
    ContentAnalysis,
    GeneratedAudio,
    GeneratedImage,
    ParsedContent,
    PipelineResult,
    PipelineStage,
    RewrittenScript,
    Storyboard,
    StyleTemplate,
    Transcript,
    VideoMetadata,
    VideoOutput,
)
from src.stages.analyzer import ContentAnalyzer, analyze_content
from src.stages.artist import VideoArtist, generate_images
from src.stages.director import VideoDirector, create_storyboard
from src.stages.fetcher import SubtitleFetcher, fetch_subtitles
from src.stages.parser import SubtitleParser, parse_subtitles
from src.stages.renderer import VideoRenderer, render_video
from src.stages.voice import VoiceActor, generate_audio
from src.stages.watcher import ChannelWatcher, watch_channel
from src.stages.writer import ContentWriter, rewrite_content
from src.storage.checkpoint import CheckpointStore
from src.storage.file_store import FileStore
from src.templates.manager import TemplateManager

logger = logging.getLogger(__name__)
console = Console()


class PipelineError(Exception):
    """Raised when pipeline execution fails."""

    pass


class VideoPipeline:
    """
    Orchestrates the complete video generation pipeline.

    Manages execution of all 9 stages with checkpoint recovery,
    error handling, and progress tracking.
    """

    def __init__(
        self,
        template: StyleTemplate | None = None,
        checkpoint_dir: str | None = None,
        storage_dir: str | None = None,
    ):
        """
        Initialize video pipeline.

        Args:
            template: Style template for content generation
            checkpoint_dir: Directory for checkpoint files
            storage_dir: Directory for generated files
        """
        settings = get_settings()

        self.template = template
        self.storage_dir = storage_dir or settings.output_dir
        self.checkpoint_dir = checkpoint_dir or str(
            Path(self.storage_dir) / "checkpoints"
        )

        # Initialize storage
        self.file_store = FileStore(self.storage_dir)
        self.checkpoint_store = CheckpointStore(self.checkpoint_dir)

        # Template manager
        self.template_manager = TemplateManager()

        # Progress tracking
        self._progress: dict[str, dict[str, Any]] = {}

    async def process_video(
        self,
        video_id: str,
        resume: bool = False,
        start_from: PipelineStage | None = None,
    ) -> VideoOutput:
        """
        Process a single video through the complete pipeline.

        Args:
            video_id: YouTube video ID
            resume: Whether to resume from last checkpoint
            start_from: Stage to start from (skips earlier stages)

        Returns:
            VideoOutput with final video metadata

        Raises:
            PipelineError: If pipeline execution fails
        """
        logger.info(f"Starting pipeline for video: {video_id}")
        console.print(f"[cyan]Processing video:[/cyan] {video_id}")

        # Determine starting stage
        # Declare pipeline variables at function scope
        transcript = None
        parsed_content = None
        analysis = None
        script = None
        storyboard = None
        images = None
        audio = None

        if start_from:
            current_stage = start_from
        elif resume:
            last_stage = self.checkpoint_store.get_latest_stage(video_id)
            if last_stage:
                current_stage = self._get_next_stage(last_stage)
                console.print(f"[yellow]Resuming from:[/yellow] {last_stage.value}")
                # Load checkpoint data to populate variables
                # Load from ALL checkpoints up to the last stage, not just the last one
                stages_to_load = [
                    PipelineStage.FETCHER,
                    PipelineStage.PARSER,
                    PipelineStage.ANALYZER,
                    PipelineStage.WRITER,
                    PipelineStage.DIRECTOR,
                    PipelineStage.ARTIST,
                    PipelineStage.VOICE,
                ]

                for stage in stages_to_load:
                    checkpoint = self.checkpoint_store.load(video_id, stage)
                    if checkpoint and checkpoint.data:
                        if "transcript" in checkpoint.data:
                            transcript = Transcript(**checkpoint.data["transcript"])
                        if "parsed" in checkpoint.data:
                            parsed_content = ParsedContent(**checkpoint.data["parsed"])
                        if "analysis" in checkpoint.data:
                            analysis = ContentAnalysis(**checkpoint.data["analysis"])
                        if "script" in checkpoint.data:
                            script = RewrittenScript(**checkpoint.data["script"])
                        if "storyboard" in checkpoint.data:
                            storyboard = Storyboard(**checkpoint.data["storyboard"])
                        if "images" in checkpoint.data:
                            images = [GeneratedImage(**img) for img in checkpoint.data["images"]]
                        if "audio" in checkpoint.data:
                            audio = [GeneratedAudio(**aud) for aud in checkpoint.data["audio"]]
            else:
                current_stage = PipelineStage.WATCHER
        else:
            current_stage = PipelineStage.WATCHER

        # Initialize progress data
        self._progress[video_id] = {
            "video_id": video_id,
            "started_at": datetime.now().isoformat(),
            "stages_completed": [],
            "current_stage": current_stage.value,
        }

        # Execute pipeline stages
        results = {}

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Video Pipeline",
                total=len(PipelineStage) - 1,
            )

            # Stage 1: Watcher (skip if starting from later stage)
            if current_stage == PipelineStage.WATCHER:
                progress.update(task, description="[cyan]Stage 1: Watcher")
                transcript = await self._run_watcher(video_id, progress, task)
                current_stage = PipelineStage.FETCHER

            # Stage 2: Fetcher
            if current_stage == PipelineStage.FETCHER:
                progress.update(task, description="[cyan]Stage 2: Fetcher")
                transcript = await self._run_fetcher(video_id, progress, task)
                await self._save_checkpoint(video_id, PipelineStage.FETCHER, {"transcript": transcript})
                current_stage = PipelineStage.PARSER

            # Stage 3: Parser
            if current_stage == PipelineStage.PARSER:
                progress.update(task, description="[cyan]Stage 3: Parser")
                parsed_content = await self._run_parser(transcript, progress, task)
                await self._save_checkpoint(video_id, PipelineStage.PARSER, {"parsed": parsed_content})
                current_stage = PipelineStage.ANALYZER

            # Stage 4: Analyzer
            if current_stage == PipelineStage.ANALYZER:
                progress.update(task, description="[cyan]Stage 4: Analyzer")
                analysis = await self._run_analyzer(video_id, parsed_content, progress, task)
                await self._save_checkpoint(video_id, PipelineStage.ANALYZER, {"analysis": analysis})
                current_stage = PipelineStage.WRITER

            # Stage 5: Writer
            if current_stage == PipelineStage.WRITER:
                progress.update(task, description="[cyan]Stage 5: Writer")
                script = await self._run_writer(video_id, analysis, progress, task)
                await self._save_checkpoint(video_id, PipelineStage.WRITER, {"script": script})
                current_stage = PipelineStage.DIRECTOR

            # Stage 6: Director
            if current_stage == PipelineStage.DIRECTOR:
                progress.update(task, description="[cyan]Stage 6: Director")
                storyboard = await self._run_director(video_id, script, progress, task)
                await self._save_checkpoint(video_id, PipelineStage.DIRECTOR, {"storyboard": storyboard})
                current_stage = PipelineStage.ARTIST

            # Stage 7: Artist
            if current_stage == PipelineStage.ARTIST:
                progress.update(task, description="[cyan]Stage 7: Artist")
                images = await self._run_artist(storyboard, progress, task)
                await self._save_checkpoint(video_id, PipelineStage.ARTIST, {"images": images})
                current_stage = PipelineStage.VOICE

            # Stage 8: Voice
            if current_stage == PipelineStage.VOICE:
                progress.update(task, description="[cyan]Stage 8: Voice")
                audio = await self._run_voice(storyboard, progress, task)
                await self._save_checkpoint(video_id, PipelineStage.VOICE, {"audio": audio})
                current_stage = PipelineStage.RENDERER

            # Stage 9: Renderer
            if current_stage == PipelineStage.RENDERER:
                progress.update(task, description="[cyan]Stage 9: Renderer")
                # Debug output
                console.print(f"[dim]  DEBUG: storyboard={storyboard}, images={len(images) if images else 0}, audio={len(audio) if audio else 0}[/dim]")
                video_output = await self._run_renderer(storyboard, images, audio, progress, task)
                await self._save_checkpoint(video_id, PipelineStage.RENDERER, {"video": video_output})

        # Mark pipeline complete
        self._progress[video_id]["completed_at"] = datetime.now().isoformat()
        self._progress[video_id]["status"] = "completed"

        console.print(f"[green]✓ Pipeline complete![/green]")
        console.print(f"[cyan]Output:[/cyan] {video_output.video_path}")

        return video_output

    async def _run_watcher(
        self,
        video_id: str,
        progress: Progress,
        task: TaskID,
    ) -> VideoMetadata:
        """Run Watcher stage."""
        try:
            # For direct video processing, we create a minimal metadata
            # In real usage, watcher would be a background service
            metadata = VideoMetadata(
                video_id=video_id,
                channel_id="direct",
                channel_name="Direct Processing",
                title=f"Video {video_id}",
                description="Direct video processing",
                published_at=datetime.now(),
                duration=0,
                thumbnail_url=f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                url=f"https://www.youtube.com/watch?v={video_id}",
            )

            progress.update(task, advance=1)
            console.print("[dim]  → Video metadata recorded[/dim]")
            return metadata

        except Exception as e:
            logger.error(f"Watcher stage failed: {e}")
            raise PipelineError(f"Watcher failed: {e}") from e

    async def _run_fetcher(
        self,
        video_id: str,
        progress: Progress,
        task: TaskID,
    ) -> Transcript:
        """Run Fetcher stage."""
        try:
            fetcher = SubtitleFetcher()
            transcript = await fetcher.fetch(video_id)

            progress.update(task, advance=1)
            console.print(f"[dim]  → Fetched {len(transcript.segments)} subtitle segments[/dim]")
            return transcript

        except Exception as e:
            logger.error(f"Fetcher stage failed: {e}")
            raise PipelineError(f"Fetcher failed: {e}") from e

    async def _run_parser(
        self,
        transcript: Transcript,
        progress: Progress,
        task: TaskID,
    ) -> ParsedContent:
        """Run Parser stage."""
        try:
            parser = SubtitleParser()
            parsed = await parser.parse(transcript)

            progress.update(task, advance=1)
            console.print("[dim]  → Subtitles cleaned and segmented[/dim]")
            return parsed

        except Exception as e:
            logger.error(f"Parser stage failed: {e}")
            raise PipelineError(f"Parser failed: {e}") from e

    async def _run_analyzer(
        self,
        video_id: str,
        parsed_content: ParsedContent,
        progress: Progress,
        task: TaskID,
    ) -> ContentAnalysis:
        """Run Analyzer stage."""
        try:
            analyzer = ContentAnalyzer()
            analysis = await analyzer.analyze(parsed_content)

            progress.update(task, advance=1)
            console.print(f"[dim]  → Extracted {len(analysis.main_points)} key points[/dim]")
            return analysis

        except Exception as e:
            logger.error(f"Analyzer stage failed: {e}")
            raise PipelineError(f"Analyzer failed: {e}") from e

    async def _run_writer(
        self,
        video_id: str,
        analysis: ContentAnalysis,
        progress: Progress,
        task: TaskID,
    ) -> RewrittenScript:
        """Run Writer stage."""
        try:
            writer = ContentWriter()
            script = await writer.rewrite(analysis, self.template)

            progress.update(task, advance=1)
            console.print(f"[dim]  → Content rewritten in {self.template.category.value if self.template else 'default'} style[/dim]")
            return script

        except Exception as e:
            logger.error(f"Writer stage failed: {e}")
            raise PipelineError(f"Writer failed: {e}") from e

    async def _run_director(
        self,
        video_id: str,
        script: RewrittenScript,
        progress: Progress,
        task: TaskID,
    ) -> Storyboard:
        """Run Director stage."""
        try:
            director = VideoDirector()
            storyboard = await director.create_storyboard(script, self.template)

            progress.update(task, advance=1)
            console.print(f"[dim]  → Created storyboard with {len(storyboard.scenes)} scenes[/dim]")
            return storyboard

        except Exception as e:
            logger.error(f"Director stage failed: {e}")
            raise PipelineError(f"Director failed: {e}") from e

    async def _run_artist(
        self,
        storyboard: Storyboard,
        progress: Progress,
        task: TaskID,
    ) -> list[GeneratedImage]:
        """Run Artist stage."""
        try:
            artist = VideoArtist(file_store=self.file_store)
            images = await artist.generate_images(storyboard, self.template)

            progress.update(task, advance=1)
            console.print(f"[dim]  → Generated {len(images)} images[/dim]")
            return images

        except Exception as e:
            logger.error(f"Artist stage failed: {e}")
            raise PipelineError(f"Artist failed: {e}") from e

    async def _run_voice(
        self,
        storyboard: Storyboard,
        progress: Progress,
        task: TaskID,
    ) -> list[GeneratedAudio]:
        """Run Voice stage."""
        try:
            actor = VoiceActor(file_store=self.file_store)
            audio = await actor.generate_audio(storyboard, self.template)

            progress.update(task, advance=1)
            console.print(f"[dim]  → Generated {len(audio)} audio segments[/dim]")
            return audio

        except Exception as e:
            logger.error(f"Voice stage failed: {e}")
            raise PipelineError(f"Voice failed: {e}") from e

    async def _run_renderer(
        self,
        storyboard: Storyboard,
        images: list[GeneratedImage],
        audio: list[GeneratedAudio],
        progress: Progress,
        task: TaskID,
    ) -> VideoOutput:
        """Run Renderer stage."""
        try:
            renderer = VideoRenderer(file_store=self.file_store)
            video = await renderer.render_video(
                storyboard.script_id,
                images,
                audio,
                storyboard=storyboard,
            )

            progress.update(task, advance=1)
            console.print(f"[dim]  → Video rendered: {video.video_path}[/dim]")
            return video

        except Exception as e:
            logger.error(f"Renderer stage failed: {e}")
            raise PipelineError(f"Renderer failed: {e}") from e

    def _get_next_stage(self, stage: PipelineStage) -> PipelineStage:
        """Get the next stage in the pipeline."""
        stages = list(PipelineStage)
        idx = stages.index(stage)
        if idx + 1 < len(stages):
            return stages[idx + 1]
        return stage

    async def _save_checkpoint(
        self,
        video_id: str,
        stage: PipelineStage,
        data: dict[str, Any],
    ) -> None:
        """Save a checkpoint for recovery."""
        checkpoint = Checkpoint(
            video_id=video_id,
            stage=stage,
            data=data,
            success=True,
        )
        self.checkpoint_store.save(checkpoint)
        self._progress[video_id]["stages_completed"].append(stage.value)

    def get_progress(self, video_id: str) -> dict[str, Any] | None:
        """
        Get progress information for a video.

        Args:
            video_id: Video ID to check

        Returns:
            Progress dict if video exists, None otherwise
        """
        return self._progress.get(video_id)


class MultiVideoPipeline:
    """
    Process multiple videos concurrently.

    Manages multiple VideoPipeline instances with concurrency control.
    """

    def __init__(
        self,
        template: StyleTemplate | None = None,
        max_concurrent: int = 3,
    ):
        """
        Initialize multi-video pipeline.

        Args:
            template: Style template to use for all videos
            max_concurrent: Maximum concurrent video processing
        """
        settings = get_settings()
        self.template = template
        self.max_concurrent = max_concurrent or settings.max_concurrent_videos
        self.storage_dir = settings.output_dir

        self._results: dict[str, VideoOutput] = {}
        self._errors: dict[str, str] = {}

    async def process_multiple(
        self,
        video_ids: list[str],
        resume_all: bool = False,
    ) -> dict[str, VideoOutput]:
        """
        Process multiple videos concurrently.

        Args:
            video_ids: List of YouTube video IDs
            resume_all: Whether to resume all from checkpoints

        Returns:
            Dictionary mapping video_id to VideoOutput

        Raises:
            PipelineError: If all videos fail to process
        """
        logger.info(f"Processing {len(video_ids)} videos with max concurrency: {self.max_concurrent}")
        console.print(f"[cyan]Processing {len(video_ids)} videos...[/cyan]")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_with_limit(video_id: str) -> tuple[str, VideoOutput | None]:
            async with semaphore:
                try:
                    pipeline = VideoPipeline(template=self.template)
                    result = await pipeline.process_video(video_id, resume=resume_all)
                    return (video_id, result)
                except PipelineError as e:
                    self._errors[video_id] = str(e)
                    logger.error(f"Failed to process {video_id}: {e}")
                    return (video_id, None)
                except Exception as e:
                    self._errors[video_id] = str(e)
                    logger.error(f"Unexpected error processing {video_id}: {e}")
                    return (video_id, None)

        # Process all videos concurrently
        tasks = [process_with_limit(vid) for vid in video_ids]
        results = await asyncio.gather(*tasks)

        # Separate successful and failed
        for video_id, result in results:
            if result:
                self._results[video_id] = result

        # Report results
        successful = len(self._results)
        failed = len(self._errors)

        console.print(f"\n[green]Processing complete:[/green]")
        console.print(f"  ✓ Successful: {successful}")
        if failed > 0:
            console.print(f"  ✗ Failed: {failed}")

        # Raise if all failed
        if successful == 0:
            raise PipelineError(
                f"Failed to process all {len(video_ids)} videos. "
                f"Errors: {list(self._errors.keys())}"
            )

        return self._results


# =============================================================================
# Convenience Functions
# =============================================================================

async def process_video(
    video_id: str,
    template: StyleTemplate | None = None,
    resume: bool = False,
) -> VideoOutput:
    """
    Process a single video through the complete pipeline.

    Convenience function that creates a VideoPipeline and runs it.

    Args:
        video_id: YouTube video ID
        template: Optional style template
        resume: Whether to resume from checkpoint

    Returns:
        VideoOutput with final video metadata

    Raises:
        PipelineError: If pipeline execution fails
    """
    pipeline = VideoPipeline(template=template)
    return await pipeline.process_video(video_id, resume=resume)


async def process_multiple_videos(
    video_ids: list[str],
    template: StyleTemplate | None = None,
    max_concurrent: int = 3,
) -> dict[str, VideoOutput]:
    """
    Process multiple videos concurrently.

    Convenience function that creates a MultiVideoPipeline and runs it.

    Args:
        video_ids: List of YouTube video IDs
        template: Optional style template
        max_concurrent: Maximum concurrent processing

    Returns:
        Dictionary mapping video_id to VideoOutput
    """
    pipeline = MultiVideoPipeline(template=template, max_concurrent=max_concurrent)
    return await pipeline.process_multiple(video_ids)
