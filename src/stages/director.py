"""
Director Stage - Storyboard Creation

Creates storyboards with scene descriptions from rewritten scripts.

Features:
- Break scripts into logical scenes
- Generate visual descriptions for each scene
- Handle multiple video types (narrative, educational, cinematic)
- Batch storyboard generation for multiple videos
"""

from typing import Any

from src.api.base import LLMProvider
from src.api.factory import ProviderFactory
from src.config.settings import get_settings
from src.core.models import RewrittenScript, Scene, Storyboard, StyleTemplate


class VideoDirector:
    """
    Create storyboards with scene descriptions from scripts.

    Transforms rewritten scripts into visual storyboards with
    scene-by-scene descriptions for video generation.
    """

    # System prompt for storyboard creation
    SYSTEM_PROMPT = """You are a video director and storyboard artist. Your task is to break down a script into individual scenes with narration and visual descriptions.

For each scene, provide:
1. **scene_number**: Sequential number starting from 1
2. **narration**: The voiceover text for this scene (portion of the script)
3. **visual_description**: A detailed visual description of what should be shown on screen
4. **duration**: How long this scene should last in seconds (typically 3-10)
5. **camera_movement**: Camera movement (e.g., "static", "panning", "zoom in", "tracking shot")
6. **mood**: The emotional tone of the scene (e.g., "neutral", "dramatic", "peaceful", "tense")

Respond ONLY in valid JSON format:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "The narration text for this scene...",
      "visual_description": "Visual description of what appears on screen...",
      "duration": 5,
      "camera_movement": "static",
      "mood": "neutral"
    }}
  ],
  "total_duration": 45
}}

Guidelines:
- Each scene should be 3-10 seconds long
- Break the script into 5-10 scenes total
- Distribute the script across scenes as narration
- Visual descriptions should be detailed enough for image generation
- Vary camera movements for visual interest
- Match mood to the content of each scene
- Total video should be 30-90 seconds"""

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize video director.

        Args:
            provider: LLM provider. If None, uses default from settings.
        """
        if provider is None:
            settings = get_settings()
            self.provider = ProviderFactory.create_llm(settings.default_llm_provider)
        else:
            self.provider = provider

    async def create_storyboard(
        self,
        script: RewrittenScript,
        template: StyleTemplate | None = None,
    ) -> Storyboard:
        """
        Create a storyboard from a rewritten script.

        Args:
            script: Rewritten script from Writer stage
            template: Optional style template for scene duration reference

        Returns:
            Storyboard with scene descriptions

        Raises:
            DirectorError: If storyboard creation fails
        """
        try:
            # Prepare the user prompt
            user_prompt = self._prepare_prompt(script, template)

            # Combine system and user prompts
            full_prompt = f"{self.SYSTEM_PROMPT}\n\n{user_prompt}"

            # Call LLM
            response = await self.provider.generate_text(
                prompt=full_prompt,
                max_tokens=1500,
                temperature=0.7,  # Higher temperature for creative variety
            )

            # Parse the response
            storyboard_data = self._parse_response(response)

            # Create Scene objects
            scenes = [
                Scene(
                    scene_number=scene_data.get("scene_number", idx + 1),
                    narration=scene_data.get("narration", ""),
                    visual_description=scene_data.get("visual_description", ""),
                    duration=scene_data.get("duration", 5),
                    camera_movement=scene_data.get("camera_movement", "static"),
                    mood=scene_data.get("mood", "neutral"),
                )
                for idx, scene_data in enumerate(storyboard_data.get("scenes", []))
            ]

            # Generate script_id from original video ID and template ID
            script_id = f"{script.original_video_id}_{script.template_id}"

            return Storyboard(
                script_id=script_id,
                scenes=scenes,
                total_duration=storyboard_data.get("total_duration", sum(s.duration for s in scenes)),
            )

        except Exception as e:
            raise DirectorError(
                f"Failed to create storyboard for {script.original_video_id}: {e}"
            ) from e

    def _prepare_prompt(
        self,
        script: RewrittenScript,
        template: StyleTemplate | None = None,
    ) -> str:
        """
        Prepare user prompt with script data.

        Args:
            script: Rewritten script
            template: Optional style template

        Returns:
            Formatted prompt string
        """
        scene_duration_hint = "5-7 seconds per scene"
        if template and template.scene_duration:
            scene_duration_hint = f"~{template.scene_duration} seconds per scene"

        return f"""Create a storyboard for the following video script:

TITLE: {script.title}

SCRIPT:
{script.script}

REQUIREMENTS:
- Target {scene_duration_hint} per scene
- Create 5-10 scenes total
- Total video should be 30-90 seconds
- Distribute the script text as narration across scenes
- Visual descriptions should be detailed for image generation
- Match the tone and style of the script

Create the storyboard JSON as specified in the system prompt."""

    def _parse_response(self, response: str) -> dict[str, Any]:
        """
        Parse LLM response as JSON.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed dictionary with storyboard data

        Raises:
            DirectorError: If response cannot be parsed as JSON
        """
        import json

        # Try to extract JSON from response
        response = response.strip()

        # Remove markdown code blocks if present
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)

        raise DirectorError("Failed to parse LLM response as JSON")


class DirectorError(Exception):
    """Raised when storyboard creation fails."""
    pass


# Convenience function for backward compatibility
async def create_storyboard(
    script: RewrittenScript,
    template: StyleTemplate | None = None,
) -> Storyboard:
    """
    Create a storyboard from a rewritten script.

    This is a convenience function that maintains backward compatibility
    with the original director.py design.

    Args:
        script: Rewritten script from Writer stage
        template: Optional style template for scene duration reference

    Returns:
        Storyboard with scene descriptions

    Raises:
        DirectorError: If storyboard creation fails
    """
    director = VideoDirector()
    return await director.create_storyboard(script, template)


# Batch storyboard creation for multiple videos
class MultiVideoDirector:
    """
    Create storyboards for multiple videos.

    Processes multiple scripts efficiently with batch templates.
    """

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize multi-video director.

        Args:
            provider: LLM provider. If None, uses default from settings.
        """
        self._director = VideoDirector(provider)

    async def create_multiple(
        self,
        scripts: dict[str, RewrittenScript],
        template: StyleTemplate | None = None,
    ) -> dict[str, Storyboard]:
        """
        Create storyboards for multiple scripts with the same template.

        Args:
            scripts: Dictionary mapping video_id to RewrittenScript
            template: Optional style template to apply to all

        Returns:
            Dictionary mapping video_id to Storyboard
        """
        results = {}
        errors = []

        for video_id, script in scripts.items():
            try:
                storyboard = await self._director.create_storyboard(script, template)
                results[video_id] = storyboard
            except DirectorError as e:
                errors.append((video_id, str(e)))

        # If all storyboard creations failed, raise an error
        if not results and errors:
            raise DirectorError(
                f"Failed to create all {len(scripts)} storyboards. "
                f"Errors: {errors}"
            )

        return results

    async def create_multiple_with_templates(
        self,
        scripts: dict[str, RewrittenScript],
        templates: dict[str, StyleTemplate],
    ) -> dict[str, Storyboard]:
        """
        Create storyboards for multiple scripts with different templates per video.

        Args:
            scripts: Dictionary mapping video_id to RewrittenScript
            templates: Dictionary mapping video_id to StyleTemplate

        Returns:
            Dictionary mapping video_id to Storyboard
        """
        results = {}
        errors = []

        for video_id, script in scripts.items():
            try:
                template = templates.get(video_id)
                storyboard = await self._director.create_storyboard(script, template)
                results[video_id] = storyboard
            except DirectorError as e:
                errors.append((video_id, str(e)))

        # If all storyboard creations failed, raise an error
        if not results and errors:
            raise DirectorError(
                f"Failed to create all {len(scripts)} storyboards. "
                f"Errors: {errors}"
            )

        return results
