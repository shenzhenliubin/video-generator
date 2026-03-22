"""
Style Template Manager

Manages loading, saving, and listing style templates from YAML configuration files.
"""

import os
from pathlib import Path

import yaml

from src.core.models import StyleTemplate, TemplateCategory


class TemplateManager:
    """Manager for style templates."""

    def __init__(self, templates_dir: str | None = None) -> None:
        """
        Initialize template manager.

        Args:
            templates_dir: Directory containing template YAML files.
                          Defaults to project root/templates/
        """
        if templates_dir is None:
            # Default to templates directory in project root
            project_root = Path(__file__).parent.parent.parent
            templates_dir = str(project_root / "templates")

        self._templates_dir = Path(templates_dir)
        self._templates: dict[str, StyleTemplate] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all template YAML files from the templates directory."""
        if not self._templates_dir.exists():
            return

        for yaml_file in self._templates_dir.glob("*.yaml"):
            try:
                template = self._load_from_file(yaml_file)
                self._templates[template.id] = template
            except Exception as e:
                print(f"Warning: Failed to load template from {yaml_file}: {e}")

    def _load_from_file(self, file_path: Path) -> StyleTemplate:
        """
        Load a single template from a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            StyleTemplate instance
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Map category string to enum
        category_str = data.get("category", "dramatic")
        try:
            category = TemplateCategory[category_str.upper()]
        except KeyError:
            category = TemplateCategory.DRAMATIC

        return StyleTemplate(
            id=data["id"],
            name=data["name"],
            category=category,
            description=data.get("description", ""),
            llm_provider=data.get("llm_provider", "siliconflow"),
            image_provider=data.get("image_provider", "siliconflow"),
            tts_provider=data.get("tts_provider", "siliconflow"),
            scene_duration=data.get("scene_duration", 5),
            image_style_prompt=data.get("image_style_prompt", ""),
            voice_id=data.get("voice_id", None),
            background_music=data.get("background_music", None),
            system_prompt=data.get("system_prompt", ""),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 1000),
        )

    def load(self, template_id: str) -> StyleTemplate:
        """
        Load a template by ID.

        Args:
            template_id: Template identifier

        Returns:
            StyleTemplate instance

        Raises:
            KeyError: If template not found
        """
        if template_id not in self._templates:
            available = ", ".join(self._templates.keys())
            raise KeyError(
                f"Template '{template_id}' not found. Available: {available}"
            )
        return self._templates[template_id]

    def save(self, template: StyleTemplate, file_path: str | None = None) -> None:
        """
        Save a template to a YAML file.

        Args:
            template: Template to save
            file_path: Output file path. If None, uses templates_dir/{id}.yaml
        """
        if file_path is None:
            file_path = self._templates_dir / f"{template.id}.yaml"
        else:
            file_path = Path(file_path)

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict for YAML serialization
        data = {
            "id": template.id,
            "name": template.name,
            "category": template.category.value.lower(),
            "description": template.description,
            "llm_provider": template.llm_provider,
            "image_provider": template.image_provider,
            "tts_provider": template.tts_provider,
            "scene_duration": template.scene_duration,
            "image_style_prompt": template.image_style_prompt,
            "voice_id": template.voice_id,
            "background_music": template.background_music,
            "system_prompt": template.system_prompt,
            "temperature": template.temperature,
            "max_tokens": template.max_tokens,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        # Update cache
        self._templates[template.id] = template

    def list_all(self) -> list[StyleTemplate]:
        """
        List all available templates.

        Returns:
            List of all loaded templates
        """
        return list(self._templates.values())

    def reload(self) -> None:
        """Reload all templates from disk."""
        self._templates.clear()
        self._load_all()
