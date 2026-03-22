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
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from src.config.settings import get_settings
from src.core.models import TemplateCategory
from src.core.pipeline import PipelineError, process_video
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
def watch(channel_id: str, interval: int, once: bool) -> None:
    """
    Monitor a YouTube channel for new videos.

    When new videos are detected, they are automatically queued for processing.
    """
    console.print(f"[cyan]Watching channel:[/cyan] {channel_id}")
    console.print(f"[cyan]Check interval:[/cyan] {interval} seconds")

    if once:
        console.print("[yellow]Running once (daemon mode disabled)[/yellow]")
        # TODO: Implement single check
    else:
        console.print("[green]Starting continuous monitoring...[/green]")
        # TODO: Implement continuous monitoring


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
@click.option("--name", required=True, help="Template name")
@click.option("--category", required=True, type=click.Choice([c.value for c in TemplateCategory]))
@click.option("--description", help="Template description")
def styles_create(name: str, category: str, description: str) -> None:
    """Create a new style template."""
    console.print(f"[cyan]Creating template:[/cyan] {name}")
    console.print(f"[cyan]Category:[/cyan] {category}")
    # TODO: Implement template creation


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
# Entry Point
# =============================================================================

if __name__ == "__main__":
    cli()
