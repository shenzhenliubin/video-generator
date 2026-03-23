"""
CLI Entry Point - Video Generator

This module provides the command-line interface for the video generator.
Uses Click for command parsing and Rich for beautiful terminal output.

Commands:
    watch       - Monitor YouTube channels for new videos
    process     - Process a single video
    styles      - Manage style templates
    config      - View and edit configuration
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config.settings import get_settings
from src.core.models import StyleTemplate, TemplateCategory, VideoMetadata
from src.core.pipeline import PipelineError, process_video
from src.stages.watcher import ChannelWatcher, QuotaExceededError
from src.storage.database import Database
from src.storage.repositories import ChannelRepository, VideoRepository
from src.templates.manager import TemplateManager

logger = logging.getLogger(__name__)

console = Console()


# ============================================================================
# CLI Group
# =============================================================================

@click.group()
@click.version_option(version="0.1.0")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def cli(verbose: bool) -> None:
    """
    Video Generator - YouTube content repurposing pipeline.

    Automate the creation of new videos from YouTube content:
    - Extract subtitles
    - Analyze with AI
    - Rewrite in different styles
    - Generate images and audio
    - Render final video
    """
    if verbose:
        console.print("[yellow]Verbose mode enabled[/yellow]")


# ============================================================================
# Watch Command
# =============================================================================

@cli.command()
@click.option("--channel-id", required=True, help="YouTube channel ID to monitor")
@click.option("--interval", default=300, help="Check interval in seconds (default: 5 min)")
@click.option("--once", is_flag=True, help="Check once and exit")
@click.option("--auto-process", is_flag=True, help="Automatically process new videos")
@click.option("--style", default="dramatic", help="Style template for auto-processing")
def watch(channel_id: str, interval: int, once: bool, auto_process: bool, style: str) -> None:
    """
    Monitor a YouTube channel for new videos.

    When new videos are detected, they are automatically queued for processing.
    """
    settings = get_settings()

    console.print(f"[cyan]Watching channel:[/cyan] {channel_id}")
    console.print(f"[cyan]Check interval:[/cyan] {interval} seconds")
    if auto_process:
        console.print(f"[cyan]Auto-process style:[/cyan] {style}")

    # Initialize database
    db = Database(settings.database_url)
    session = db.get_session()

    try:
        # Get or create channel in database
        channel_repo = ChannelRepository(session)
        channel = channel_repo.get_or_create(
            channel_id=channel_id,
            channel_name=f"Channel {channel_id}",
            channel_url=f"https://www.youtube.com/channel/{channel_id}",
        )
        console.print(f"[green]✓ Channel registered:[/green] {channel.channel_name}")

        # Get last checked timestamp from database
        last_checked = channel.last_checked_at
        if last_checked:
            console.print(f"[dim]  Last checked:[dim] {last_checked.isoformat()}")

        # Initialize watcher
        watcher = ChannelWatcher()

        # Load template for auto-processing
        template = None
        if auto_process:
            template_manager = TemplateManager()
            try:
                template = template_manager.load(style)
            except KeyError:
                console.print(f"[red]Error:[/red] Template '{style}' not found.")
                raise click.ClickException("Template not found")

        # Run check
        asyncio.run(_run_watch_check(
            watcher=watcher,
            channel_id=channel_id,
            channel_repo=channel_repo,
            video_repo=VideoRepository(session),
            template=template,
            once=once,
            interval=interval,
        ))

    except QuotaExceededError as e:
        console.print(f"[red]API Error:[/red] {e}")
        raise click.ClickException("YouTube API quota exceeded")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Watch command failed")
        raise click.ClickException("Watch failed")
    finally:
        session.close()


async def _run_watch_check(
    watcher: ChannelWatcher,
    channel_id: str,
    channel_repo: ChannelRepository,
    video_repo: VideoRepository,
    template: StyleTemplate | None,
    once: bool,
    interval: int,
) -> None:
    """
    Run the watch check loop.

    Args:
        watcher: Channel watcher instance
        channel_id: YouTube channel ID
        channel_repo: Channel repository
        video_repo: Video repository
        template: Template for auto-processing (None to disable)
        once: Run once and exit
        interval: Check interval in seconds
    """
    shutdown = False

    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        nonlocal shutdown
        console.print("\n[yellow]Received shutdown signal...[/yellow]")
        shutdown = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    check_count = 0

    while not shutdown:
        check_count += 1
        check_time = datetime.now(timezone.utc)

        console.print()
        console.print(f"[cyan]Check #{check_count}[/cyan] - {check_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Check for new videos
            new_videos = await watcher.check_new_videos(channel_id)

            # Update last checked timestamp in database
            channel_repo.update_last_checked(channel_id, check_time)

            if new_videos:
                console.print(f"[green]Found {len(new_videos)} new video(s)[/green]")

                for video in new_videos:
                    console.print()
                    console.print(Panel(
                        f"[cyan]Title:[/cyan] {video.title}\n"
                        f"[cyan]Published:[/cyan] {video.published_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                        f"[cyan]URL:[/cyan] {video.url}",
                        title=f"[green]New Video: {video.video_id}[/green]",
                        border_style="green",
                    ))

                    # Save to database
                    video_repo.create(
                        video_id=video.video_id,
                        channel_id=video.channel_id,
                        title=video.title,
                        url=video.url,
                        published_at=video.published_at,
                        description=video.description,
                        duration_seconds=video.duration,
                        thumbnail_url=video.thumbnail_url,
                    )
                    console.print("[dim]  → Saved to database[/dim]")

                    # Auto-process if enabled
                    if template:
                        console.print(f"[yellow]Processing with style: {template.id}...[/yellow]")
                        try:
                            result = await process_video(
                                video_id=video.video_id,
                                template=template,
                                resume=False,
                            )
                            console.print(f"[green]✓ Video processed: {result.video_path}[/green]")

                            # Update status in database
                            video_repo.update_status(
                                video.video_id,
                                "completed",
                                output_path=result.video_path,
                                template_used=template.id,
                            )
                        except PipelineError as e:
                            console.print(f"[red]✗ Processing failed:[/red] {e}")
                            video_repo.update_status(
                                video.video_id,
                                "failed",
                                error_message=str(e),
                            )
            else:
                console.print("[dim]No new videos found[/dim]")

            # Exit if once mode
            if once:
                console.print("[yellow]Single check complete, exiting[/yellow]")
                break

            # Wait for next interval
            if not shutdown:
                console.print(f"[dim]Waiting {interval} seconds until next check...[/dim]")
                console.print("[dim](Press Ctrl+C to exit)[/dim]")

                # Sleep in small increments to allow shutdown signal
                remaining = interval
                while remaining > 0 and not shutdown:
                    sleep_time = min(remaining, 5)
                    await asyncio.sleep(sleep_time)
                    remaining -= sleep_time

        except QuotaExceededError:
            console.print("[red]YouTube API quota exceeded. Pausing checks.[/red]")
            console.print("[yellow]The quota will reset at midnight Pacific Time.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error during check:[/red] {e}")
            logger.exception(f"Error checking channel {channel_id}")

    console.print()
    console.print("[yellow]Watch command finished[/yellow]")


# ============================================================================
# Process Command
# =============================================================================

@cli.command()
@click.option("--video-id", required=True, help="YouTube video ID to process")
@click.option(
    "--style",
    type=click.Choice([c.value for c in TemplateCategory]),
    default="dramatic",
    help="Style template to use",
)
@click.option("--output", help="Output directory (default: uses settings.output_dir)")
@click.option("--resume", is_flag=True, help="Resume from last checkpoint if available")
def process(video_id: str, style: str, output: str | None, resume: bool) -> None:
    """
    Process a single YouTube video.

    Runs the full pipeline: subtitle extraction → analysis → rewrite →
    storyboard → image/audio generation → video rendering.
    """
    settings = get_settings()
    output_dir = output or settings.output_dir

    console.print(f"[cyan]Processing video:[/cyan] {video_id}")
    console.print(f"[cyan]Style:[/cyan] {style}")
    console.print(f"[cyan]Output:[/cyan] {output_dir}")
    if resume:
        console.print(f"[yellow]Resume mode:[/yellow] enabled")
    console.print()

    # Load template
    try:
        template_manager = TemplateManager()
        # Use style as template ID (they match in current setup)
        template = template_manager.load(style)
        console.print(f"[green]✓ Loaded template:[/green] {template.name}")
        console.print(f"[dim]  {template.description}[/dim]")
        console.print()
    except KeyError as e:
        console.print(f"[red]Error:[/red] Template '{style}' not found.")
        console.print(f"[dim]Available templates: {', '.join([t.id for t in template_manager.list_all()])}[/dim]")
        raise click.ClickException("Template not found")

    # Run pipeline
    try:
        result = asyncio.run(process_video(
            video_id=video_id,
            template=template,
            resume=resume,
        ))

        console.print()
        console.print("[green]✓ Processing complete![/green]")
        console.print(f"[cyan]Video output:[/cyan] {result.video_path}")
        console.print(f"[cyan]Duration:[/cyan] {result.duration} seconds")
        console.print(f"[cyan]Resolution:[/cyan] {result.resolution}")
        console.print(f"[cyan]Scenes:[/cyan] {result.scenes_count}")

    except PipelineError as e:
        console.print()
        console.print(f"[red]Pipeline error:[/red] {e}")
        logger.error(f"Pipeline failed for video {video_id}: {e}")
        raise click.ClickException("Pipeline processing failed")
    except Exception as e:
        console.print()
        console.print(f"[red]Unexpected error:[/red] {e}")
        logger.exception(f"Unexpected error processing video {video_id}")
        raise click.ClickException("Processing failed")


# ============================================================================
# Styles Command
# =============================================================================

@cli.group()
def styles() -> None:
    """Manage style templates."""
    pass


@styles.command(name="list")
def styles_list() -> None:
    """List available style templates."""
    table = Table(title="Style Templates")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Description")
    table.add_column("Providers", style="dim")

    template_manager = TemplateManager()
    templates = template_manager.list_all()

    if not templates:
        console.print("[yellow]No templates found[/yellow]")
        return

    for template in templates:
        table.add_row(
            template.id,
            template.name,
            template.category.value,
            template.description,
            f"LLM: {template.llm_provider}, Image: {template.image_provider}, TTS: {template.tts_provider}",
        )

    console.print(table)


@styles.command(name="show")
@click.argument("template_id")
def styles_show(template_id: str) -> None:
    """Show details of a style template."""
    template_manager = TemplateManager()

    try:
        template = template_manager.load(template_id)
    except KeyError:
        console.print(f"[red]Error:[/red] Template '{template_id}' not found.")
        console.print(f"[dim]Available templates: {', '.join([t.id for t in template_manager.list_all()])}[/dim]")
        raise click.ClickException("Template not found")

    # Display template details
    console.print()
    console.print(f"[cyan]Template ID:[/cyan] {template.id}")
    console.print(f"[cyan]Name:[/cyan] {template.name}")
    console.print(f"[cyan]Category:[/cyan] {template.category.value}")
    console.print(f"[cyan]Description:[/cyan] {template.description}")
    console.print()

    # Providers
    console.print("[cyan]Providers:[/cyan]")
    console.print(f"  LLM: {template.llm_provider}")
    console.print(f"  Image: {template.image_provider}")
    console.print(f"  TTS: {template.tts_provider}")
    console.print()

    # Parameters
    console.print("[cyan]Parameters:[/cyan]")
    console.print(f"  Scene Duration: {template.scene_duration} seconds")
    console.print(f"  Temperature: {template.temperature}")
    console.print(f"  Max Tokens: {template.max_tokens}")
    console.print()

    # Optional fields
    if template.image_style_prompt:
        console.print(f"[cyan]Image Style:[/cyan] {template.image_style_prompt}")
    if template.voice_id:
        console.print(f"[cyan]Voice ID:[/cyan] {template.voice_id}")
    if template.background_music:
        console.print(f"[cyan]Background Music:[/cyan] {template.background_music}")
    if template.system_prompt:
        console.print(f"[cyan]System Prompt:[/cyan]")
        console.print(f"[dim]{template.system_prompt}[/dim]")


@styles.command(name="create")
@click.option("--id", required=True, help="Template ID (unique identifier)")
@click.option("--name", required=True, help="Template display name")
@click.option("--category", required=True, type=click.Choice([c.value for c in TemplateCategory]), help="Template category")
@click.option("--description", help="Template description")
@click.option("--llm-provider", default="siliconflow", help="LLM provider (default: siliconflow)")
@click.option("--image-provider", default="siliconflow", help="Image provider (default: siliconflow)")
@click.option("--tts-provider", default="siliconflow", help="TTS provider (default: siliconflow)")
@click.option("--scene-duration", default=5, type=int, help="Scene duration in seconds (default: 5)")
@click.option("--temperature", default=0.7, type=float, help="LLM temperature (default: 0.7)")
@click.option("--max-tokens", default=1000, type=int, help="LLM max tokens (default: 1000)")
@click.option("--voice-id", help="TTS voice ID")
@click.option("--image-style", help="Image style prompt")
@click.option("--system-prompt", help="System prompt for LLM")
@click.option("--bg-music", help="Background music file")
def styles_create(
    id: str,
    name: str,
    category: str,
    description: str | None,
    llm_provider: str,
    image_provider: str,
    tts_provider: str,
    scene_duration: int,
    temperature: float,
    max_tokens: int,
    voice_id: str | None,
    image_style: str | None,
    system_prompt: str | None,
    bg_music: str | None,
) -> None:
    """Create a new style template."""
    console.print(f"[cyan]Creating template:[/cyan] {name}")
    console.print(f"[cyan]ID:[/cyan] {id}")
    console.print(f"[cyan]Category:[/cyan] {category}")
    console.print()

    # Check if template already exists
    template_manager = TemplateManager()
    try:
        existing = template_manager.load(id)
        console.print(f"[yellow]Warning:[/yellow] Template '{id}' already exists.")
        if not click.confirm("Do you want to overwrite it?"):
            console.print("[yellow]Creation cancelled[/yellow]")
            return
    except KeyError:
        pass  # Template doesn't exist, proceed with creation

    # Use default description if not provided
    if not description:
        description = f"{name} style template for {category} content."

    # Create template
    template = StyleTemplate(
        id=id,
        name=name,
        category=TemplateCategory[category.upper()],
        description=description,
        llm_provider=llm_provider,
        image_provider=image_provider,
        tts_provider=tts_provider,
        scene_duration=scene_duration,
        temperature=temperature,
        max_tokens=max_tokens,
        voice_id=voice_id,
        image_style_prompt=image_style or "",
        background_music=bg_music,
        system_prompt=system_prompt or "",
    )

    # Save template
    try:
        template_manager.save(template)
        console.print(f"[green]✓ Template saved:[/green] templates/{id}.yaml")
        console.print()

        # Show template summary
        console.print("[cyan]Template Summary:[/cyan]")
        console.print(f"  ID: {template.id}")
        console.print(f"  Name: {template.name}")
        console.print(f"  Category: {template.category.value}")
        console.print(f"  Description: {template.description}")
        console.print(f"  Providers: LLM={template.llm_provider}, Image={template.image_provider}, TTS={template.tts_provider}")
        console.print(f"  Scene Duration: {template.scene_duration}s")
        console.print(f"  Temperature: {template.temperature}")
        console.print(f"  Max Tokens: {template.max_tokens}")

        if template.voice_id:
            console.print(f"  Voice ID: {template.voice_id}")
        if template.image_style_prompt:
            console.print(f"  Image Style: {template.image_style_prompt}")
        if template.background_music:
            console.print(f"  Background Music: {template.background_music}")
        if template.system_prompt:
            console.print(f"  System Prompt: {template.system_prompt[:100]}...")

    except Exception as e:
        console.print(f"[red]Error saving template:[/red] {e}")
        raise click.ClickException("Failed to save template")


@styles.command(name="delete")
@click.argument("template_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def styles_delete(template_id: str, force: bool) -> None:
    """Delete a style template."""
    template_manager = TemplateManager()

    # Check if template exists
    try:
        template = template_manager.load(template_id)
    except KeyError:
        console.print(f"[red]Error:[/red] Template '{template_id}' not found.")
        console.print(f"[dim]Available templates: {', '.join([t.id for t in template_manager.list_all()])}[/dim]")
        raise click.ClickException("Template not found")

    console.print(f"[cyan]Deleting template:[/cyan] {template.name} ({template_id})")
    console.print(f"[dim]Category: {template.category.value}[/dim]")

    # Confirm deletion
    if not force:
        if not click.confirm("Are you sure you want to delete this template?"):
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    # Delete template
    try:
        template_manager.delete(template_id)
        console.print(f"[green]✓ Template deleted:[/green] templates/{template_id}.yaml")
    except Exception as e:
        console.print(f"[red]Error deleting template:[/red] {e}")
        raise click.ClickException("Failed to delete template")


@styles.command(name="edit")
@click.argument("template_id")
@click.option("--name", help="Template display name")
@click.option("--description", help="Template description")
@click.option("--llm-provider", help="LLM provider")
@click.option("--image-provider", help="Image provider")
@click.option("--tts-provider", help="TTS provider")
@click.option("--scene-duration", type=int, help="Scene duration in seconds")
@click.option("--temperature", type=float, help="LLM temperature")
@click.option("--max-tokens", type=int, help="LLM max tokens")
@click.option("--voice-id", help="TTS voice ID")
@click.option("--image-style", help="Image style prompt")
@click.option("--system-prompt", help="System prompt for LLM")
@click.option("--bg-music", help="Background music file")
def styles_edit(template_id: str, **kwargs) -> None:
    """Edit an existing style template."""
    template_manager = TemplateManager()

    # Load existing template
    try:
        template = template_manager.load(template_id)
    except KeyError:
        console.print(f"[red]Error:[/red] Template '{template_id}' not found.")
        console.print(f"[dim]Available templates: {', '.join([t.id for t in template_manager.list_all()])}[/dim]")
        raise click.ClickException("Template not found")

    # Update fields if provided
    updated = False
    if kwargs.get("name"):
        template.name = kwargs["name"]
        updated = True
    if kwargs.get("description") is not None:
        template.description = kwargs["description"]
        updated = True
    if kwargs.get("llm_provider"):
        template.llm_provider = kwargs["llm_provider"]
        updated = True
    if kwargs.get("image_provider"):
        template.image_provider = kwargs["image_provider"]
        updated = True
    if kwargs.get("tts_provider"):
        template.tts_provider = kwargs["tts_provider"]
        updated = True
    if kwargs.get("scene_duration") is not None:
        template.scene_duration = kwargs["scene_duration"]
        updated = True
    if kwargs.get("temperature") is not None:
        template.temperature = kwargs["temperature"]
        updated = True
    if kwargs.get("max_tokens") is not None:
        template.max_tokens = kwargs["max_tokens"]
        updated = True
    if kwargs.get("voice_id") is not None:
        template.voice_id = kwargs["voice_id"]
        updated = True
    if kwargs.get("image_style") is not None:
        template.image_style_prompt = kwargs["image_style"]
        updated = True
    if kwargs.get("system_prompt") is not None:
        template.system_prompt = kwargs["system_prompt"]
        updated = True
    if kwargs.get("bg_music") is not None:
        template.background_music = kwargs["bg_music"]
        updated = True

    if not updated:
        console.print("[yellow]No changes specified[/yellow]")
        console.print("[dim]Use --help to see available options[/dim]")
        return

    # Save updated template
    try:
        template_manager.save(template)
        console.print(f"[green]✓ Template updated:[/green] templates/{template_id}.yaml")
        console.print()
        console.print("[cyan]Updated values:[/cyan]")
        for key, value in kwargs.items():
            if value is not None:
                console.print(f"  {key}: {value}")
    except Exception as e:
        console.print(f"[red]Error updating template:[/red] {e}")
        raise click.ClickException("Failed to update template")


# ============================================================================
# Config Command
# =============================================================================

@cli.command()
def config() -> None:
    """Show current configuration."""
    settings = get_settings()

    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    # Provider settings
    table.add_row("Default LLM", settings.default_llm_provider)
    table.add_row("Default Image", settings.default_image_provider)
    table.add_row("Default TTS", settings.default_tts_provider)

    # Processing settings
    table.add_row("Max Concurrent", str(settings.max_concurrent_videos))
    table.add_row("Checkpoint Interval", str(settings.checkpoint_interval))

    # Paths
    table.add_row("Output Dir", settings.output_dir)
    table.add_row("Temp Dir", settings.temp_dir)

    console.print(table)
    console.print()

    # Provider availability
    console.print("[cyan]Provider Status:[/cyan]")

    providers = [
        ("LLM", settings.default_llm_provider, "llm"),
        ("Image", settings.default_image_provider, "image"),
        ("TTS", settings.default_tts_provider, "tts"),
    ]

    for provider_type, provider_name, provider_kind in providers:
        available = settings.validate_provider_available(provider_kind, provider_name)
        status = "[green]✓[/green]" if available else "[red]✗[/red]"
        console.print(f"  {status} {provider_type}: {provider_name}")


# ============================================================================
# API Command
# ============================================================================

@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
@click.option("--port", default=None, type=int, help="Port to bind to (default: from settings)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def api(host: str, port: int | None, reload: bool) -> None:
    """Start the FastAPI web server."""
    import uvicorn

    settings = get_settings()
    api_port = port or settings.api_port

    console.print(Panel.fit(
        "[cyan]Video Generator API[/cyan]",
        subtitle="v0.2.0"
    ))
    console.print()
    console.print(f"[cyan]Server:[/cyan] http://{host}:{api_port}")
    console.print(f"[cyan]Docs:[/cyan] http://{host}:{api_port}/docs")
    console.print()

    if reload:
        console.print("[yellow]Development mode with auto-reload[/yellow]")
        console.print()

    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=api_port,
        reload=reload,
    )


# ============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    cli()
