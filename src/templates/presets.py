"""
Preset Style Templates

Built-in style templates included with the application.
"""

from src.core.models import StyleTemplate, TemplateCategory

# Preset templates
PRESET_TEMPLATES: dict[str, StyleTemplate] = {
    "dramatic": StyleTemplate(
        id="dramatic",
        name="Dramatic",
        category=TemplateCategory.DRAMATIC,
        description="High-impact, cinematic storytelling with emotional depth",
        llm_provider="openai",
        image_provider="openai",
        tts_provider="elevenlabs",
        scene_duration=5,
        image_style_prompt="cinematic, dramatic lighting, high contrast",
        system_prompt="You are a dramatic storyteller. Create engaging narratives with emotional impact.",
        temperature=0.8,
    ),
    "humorous": StyleTemplate(
        id="humorous",
        name="Humorous",
        category=TemplateCategory.HUMOROUS,
        description="Light, funny, entertaining content",
        llm_provider="openai",
        image_provider="openai",
        tts_provider="elevenlabs",
        scene_duration=4,
        image_style_prompt="colorful, animated style, fun and playful",
        system_prompt="You are a humorous writer. Create entertaining, lighthearted content.",
        temperature=0.9,
    ),
    "educational": StyleTemplate(
        id="educational",
        name="Educational",
        category=TemplateCategory.EDUCATIONAL,
        description="Clear, informative, academic presentation",
        llm_provider="openai",
        image_provider="openai",
        tts_provider="elevenlabs",
        scene_duration=6,
        image_style_prompt="clean diagrams, educational illustrations, clear visuals",
        system_prompt="You are an educator. Create clear, informative explanations.",
        temperature=0.5,
    ),
}
