"""
Configuration Management - Pydantic Settings

This module handles all configuration loading and validation.
Uses pydantic-settings for environment variable loading.

Configuration precedence:
1. Environment variables (highest)
2. .env file
3. Default values
"""

import os
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Create a .env file from .env.example to configure.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # YouTube API
    # =========================================================================
    youtube_api_key: str = ""

    # =========================================================================
    # OpenAI
    # =========================================================================
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_image_model: str = "dall-e-3"

    # =========================================================================
    # Anthropic (Claude)
    # =========================================================================
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-opus-20240229"

    # =========================================================================
    # ElevenLabs (TTS)
    # =========================================================================
    elevenlabs_api_key: str = ""
    elevenlabs_default_voice: str = "21m00Tcm4TlvDq8ikWAM"  # "Rachel"

    # =========================================================================
    # Replicate (Stability AI)
    # =========================================================================
    replicate_api_token: str = ""

    # =========================================================================
    # SiliconFlow (硅基流动)
    # =========================================================================
    siliconflow_api_key: str = ""

    # =========================================================================
    # Database
    # =========================================================================
    database_url: str = "sqlite:///./video_generator.db"

    # =========================================================================
    # Paths
    # =========================================================================
    output_dir: str = "./output"
    temp_dir: str = "./temp"

    # =========================================================================
    # Logging
    # =========================================================================
    log_level: str = "INFO"
    log_file: str = "video_generator.log"

    # =========================================================================
    # Provider defaults
    # =========================================================================
    default_llm_provider: str = "openai"
    default_image_provider: str = "openai"
    default_tts_provider: str = "elevenlabs"

    # =========================================================================
    # Processing limits
    # =========================================================================
    max_concurrent_videos: int = 3
    checkpoint_interval: int = 60

    # =========================================================================
    # Web API
    # =========================================================================
    api_port: int = 8888
    api_host: str = "0.0.0.0"

    # =========================================================================
    # Fallback providers
    # =========================================================================
    fallback_llm_provider: str | None = None
    fallback_image_provider: str | None = None
    fallback_tts_provider: str | None = None

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Provider configuration getters
    # =========================================================================

    def get_llm_config(self, provider: str) -> dict[str, Any]:
        """Get configuration for an LLM provider."""
        configs = {
            "openai": {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
            },
            "anthropic": {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
            },
            "siliconflow": {
                "api_key": self.siliconflow_api_key,
            },
        }
        return configs.get(provider, {})

    def get_image_config(self, provider: str) -> dict[str, Any]:
        """Get configuration for an image provider."""
        configs = {
            "openai": {
                "api_key": self.openai_api_key,
                "model": self.openai_image_model,
            },
            "stability": {
                "api_token": self.replicate_api_token,
            },
            "siliconflow": {
                "api_key": self.siliconflow_api_key,
            },
        }
        return configs.get(provider, {})

    def get_tts_config(self, provider: str) -> dict[str, Any]:
        """Get configuration for a TTS provider."""
        configs = {
            "elevenlabs": {
                "api_key": self.elevenlabs_api_key,
                "default_voice": self.elevenlabs_default_voice,
            },
            "local": {},  # No config needed
            "siliconflow": {
                "api_key": self.siliconflow_api_key,
            },
        }
        return configs.get(provider, {})

    def validate_provider_available(self, provider_type: str, provider: str) -> bool:
        """
        Check if a provider has valid credentials configured.

        Returns:
            True if provider is configured and available
        """
        if provider_type == "llm":
            config = self.get_llm_config(provider)
            return bool(config.get("api_key"))
        elif provider_type == "image":
            config = self.get_image_config(provider)
            return bool(config.get("api_key") or config.get("api_token"))
        elif provider_type == "tts":
            if provider == "local":
                return True  # Always available
            config = self.get_tts_config(provider)
            return bool(config.get("api_key"))
        return False


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get the global settings instance.

    Creates the instance on first call.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment.

    Useful after changing environment variables.
    """
    global _settings
    _settings = Settings()
    return _settings
