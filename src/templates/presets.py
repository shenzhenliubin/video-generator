"""
Preset Style Templates

Built-in style templates included with the application.
Templates are now loaded from YAML files in the templates/ directory,
with fallback to these hardcoded definitions if needed.
"""

from src.core.models import StyleTemplate, TemplateCategory

# Fallback preset templates (used if YAML files are not available)
FALLBACK_TEMPLATES: dict[str, StyleTemplate] = {
    "dramatic": StyleTemplate(
        id="dramatic",
        name="Dramatic",
        category=TemplateCategory.DRAMATIC,
        description="High-impact, cinematic storytelling with emotional depth",
        llm_provider="siliconflow",
        image_provider="siliconflow",
        tts_provider="siliconflow",
        scene_duration=5,
        image_style_prompt="cinematic, dramatic lighting, high contrast",
        voice_id="charles",
        system_prompt="You are a dramatic storyteller. Create engaging narratives with emotional impact.",
        temperature=0.8,
    ),
    "humorous": StyleTemplate(
        id="humorous",
        name="Humorous",
        category=TemplateCategory.HUMOROUS,
        description="Light, funny, entertaining content",
        llm_provider="siliconflow",
        image_provider="siliconflow",
        tts_provider="siliconflow",
        scene_duration=4,
        image_style_prompt="colorful, animated style, fun and playful",
        voice_id="diana",
        system_prompt="You are a humorous writer. Create entertaining, lighthearted content.",
        temperature=0.9,
    ),
    "educational": StyleTemplate(
        id="educational",
        name="Educational",
        category=TemplateCategory.EDUCATIONAL,
        description="Clear, informative, academic presentation",
        llm_provider="siliconflow",
        image_provider="siliconflow",
        tts_provider="siliconflow",
        scene_duration=6,
        image_style_prompt="clean diagrams, educational illustrations, clear visuals",
        voice_id="claire",
        system_prompt="You are an educator. Create clear, informative explanations.",
        temperature=0.5,
    ),
}


# Backwards compatibility - use FALLBACK_TEMPLATES as PRESET_TEMPLATES
PRESET_TEMPLATES = FALLBACK_TEMPLATES


def get_template(template_id: str) -> StyleTemplate:
    """
    Get a template by ID, loading from YAML files if available.

    Args:
        template_id: Template identifier

    Returns:
        StyleTemplate instance
    """
    # Try loading from TemplateManager (YAML files)
    try:
        from src.templates.manager import TemplateManager

        manager = TemplateManager()
        return manager.load(template_id)
    except Exception:
        # Fallback to hardcoded templates
        if template_id in FALLBACK_TEMPLATES:
            return FALLBACK_TEMPLATES[template_id]
        raise KeyError(f"Template '{template_id}' not found")


def list_templates() -> list[StyleTemplate]:
    """
    List all available templates, loading from YAML files if available.

    Returns:
        List of all available templates
    """
    # Try loading from TemplateManager (YAML files)
    try:
        from src.templates.manager import TemplateManager

        manager = TemplateManager()
        templates = manager.list_all()
        if templates:
            return templates
    except Exception:
        pass

    # Fallback to hardcoded templates
    return list(FALLBACK_TEMPLATES.values())
