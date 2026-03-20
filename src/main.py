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
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from src.config.settings import get_settings
from src.core.models import TemplateCategory

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
@click.option("--output", help="Output directory (default: ./output)")
def process(video_id: str, style: str, output: str | None) -> None:
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
    console.print()

    # TODO: Implement pipeline execution
    console.print("[yellow]Pipeline not yet implemented[/yellow]")
    console.print("[dim]This will run the 8-stage processing pipeline[/dim]")


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

    # TODO: Load from templates/presets.py
    presets = [
        {
            "id": "dramatic",
            "name": "Dramatic",
            "category": "dramatic",
            "description": "High-impact, cinematic storytelling",
        },
        {
            "id": "humorous",
            "name": "Humorous",
            "category": "humorous",
            "description": "Light, funny, entertaining",
        },
        {
            "id": "educational",
            "name": "Educational",
            "category": "educational",
            "description": "Clear, informative, academic",
        },
    ]

    for preset in presets:
        table.add_row(
            preset["id"],
            preset["name"],
            preset["category"],
            preset["description"],
        )

    console.print(table)


@styles.command(name="show")
@click.argument("template_id")
def styles_show(template_id: str) -> None:
    """Show details of a style template."""
    console.print(f"[cyan]Template:[/cyan] {template_id}")
    # TODO: Load and display template details


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
