"""
Writer Stage - Content Rewriting

Rewrites content in specific styles using LLM.

Features:
- Apply different style templates (dramatic, humorous, educational, etc.)
- Generate engaging titles
- Rewrite main points into cohesive script
- Style notes and tone preservation
"""

from typing import Any

from src.api.base import LLMProvider
from src.api.factory import ProviderFactory
from src.config.settings import get_settings
from src.core.models import ContentAnalysis, RewrittenScript, StyleTemplate


class ContentWriter:
    """
    Rewrite content in specific styles using LLM.

    Transforms analyzed content into engaging scripts with different tones.
    """

    # Base style prompts for different categories
    STYLE_PROMPTS = {
        "dramatic": """You are a dramatic storyteller. Rewrite the content with:
- Emotional intensity and suspense
- Vivid imagery and metaphors
- Dramatic pacing and tension
- Powerful, memorable language

Create something that feels like a movie trailer or dramatic narration.""",

        "humorous": """You are a comedy writer. Rewrite the content with:
- Witty humor and clever wordplay
- Light-hearted, entertaining tone
- Relatable examples and anecdotes
- Engaging comedic timing

Make it funny but still convey the core message.""",

        "educational": """You are an expert educator. Rewrite the content with:
- Clear, accessible explanations
- Structured learning flow
- Practical examples and analogies
- Actionable takeaways

Make complex topics easy to understand.""",

        "cinematic": """You are a screenwriter. Rewrite the content with:
- Visual, scene-setting language
- Epic, cinematic scope
- Emotional resonance
- Film-worthy dialogue and narration

Write it like it could be a documentary or feature film.""",

        "documentary": """You are a documentary narrator. Rewrite the content with:
- Informative, factual tone
- Engaging storytelling
- Clear narrative arc
- Professional broadcast style

Make it sound like a high-quality documentary narration.""",

        "news": """You are a news anchor. Rewrite the content with:
- Concise, punchy delivery
- Journalistic precision
- Urgency and relevance
- Clear headline and lead

Write it like a breaking news segment.""",
    }

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize content writer.

        Args:
            provider: LLM provider. If None, uses default from settings.
        """
        if provider is None:
            settings = get_settings()
            self.provider = ProviderFactory.create_llm(settings.default_llm_provider)
        else:
            self.provider = provider

    async def rewrite(
        self,
        analysis: ContentAnalysis,
        template: StyleTemplate,
    ) -> RewrittenScript:
        """
        Rewrite content in the specified style.

        Args:
            analysis: Content analysis from Analyzer stage
            template: Style template to apply

        Returns:
            RewrittenScript with title and script in target style

        Raises:
            WritingError: If rewriting fails
        """
        try:
            # Get the style prompt
            style_prompt = self._get_style_prompt(template)

            # Prepare the rewrite prompt
            user_prompt = self._prepare_prompt(analysis, template)

            # Combine system and user prompts
            full_prompt = f"{style_prompt}\n\n{user_prompt}"

            # Call LLM
            response = await self.provider.generate_text(
                prompt=full_prompt,
                max_tokens=template.max_tokens,
                temperature=template.temperature,
            )

            # Parse the response
            script_data = self._parse_response(response)

            return RewrittenScript(
                original_video_id=analysis.video_id,
                template_id=template.id,
                title=script_data.get("title", ""),
                script=script_data.get("script", ""),
                style_notes=script_data.get("style_notes", ""),
            )

        except Exception as e:
            raise WritingError(
                f"Failed to rewrite content for {analysis.video_id}: {e}"
            ) from e

    def _get_style_prompt(self, template: StyleTemplate) -> str:
        """
        Get the style-specific system prompt.

        Args:
            template: Style template

        Returns:
            Style-specific prompt string
        """
        # Use custom prompt if provided, otherwise use predefined
        if template.system_prompt:
            return template.system_prompt

        category = template.category.value if hasattr(template.category, 'value') else template.category
        return self.STYLE_PROMPTS.get(
            category,
            self.STYLE_PROMPTS["documentary"]  # Default fallback
        )

    def _prepare_prompt(
        self,
        analysis: ContentAnalysis,
        template: StyleTemplate,
    ) -> str:
        """
        Prepare user prompt with analysis data.

        Args:
            analysis: Content analysis
            template: Style template

        Returns:
            Formatted prompt string
        """
        # Format main points
        main_points_text = "\n".join(
            f"{i+1}. {point}" for i, point in enumerate(analysis.main_points)
        )

        # Format topics
        topics_text = ", ".join(analysis.topics) if analysis.topics else "general"

        return f"""Rewrite the following content into an engaging script.

VIDEO ANALYSIS:
Main Points:
{main_points_text}

Summary: {analysis.summary}

Topics: {topics_text}
Sentiment: {analysis.sentiment or 'neutral'}

REQUIREMENTS:
1. Create a CATCHY TITLE (under 60 characters)
2. Write a 200-500 word script
3. Maintain the core message and key points
4. Apply the style characteristics specified above
5. End with a call-to-action or thought-provoking question

Respond in JSON format:
{{
  "title": "Your catchy title here",
  "script": "Your full script here...",
  "style_notes": "Brief note on how the style was applied"
}}

The script should be engaging, well-structured, and ready for video narration."""

    def _parse_response(self, response: str) -> dict[str, Any]:
        """
        Parse LLM response as JSON.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed dictionary with title and script

        Raises:
            WritingError: If response cannot be parsed as JSON
        """
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
            return self._extract_json(response)
        except Exception as e:
            # Fallback: try to extract title and script from plain text
            return self._extract_text_fallback(response)

    def _extract_json(self, text: str) -> dict[str, Any]:
        """
        Extract JSON from text response.

        Args:
            text: Response text

        Returns:
            Parsed dictionary
        """
        import json

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)

        raise ValueError("No valid JSON found")

    def _extract_text_fallback(self, text: str) -> dict[str, Any]:
        """
        Extract title and script from plain text fallback.

        Args:
            text: Response text

        Returns:
            Dictionary with title and script
        """
        lines = text.split("\n")

        # First line is likely the title
        title = lines[0].strip(":#* ") if lines else "Generated Script"

        # Rest is the script
        script = "\n".join(lines[1:]).strip()

        return {
            "title": title,
            "script": script,
            "style_notes": "Extracted from plain text response",
        }


class WritingError(Exception):
    """Raised when content rewriting fails."""
    pass


# Convenience function for backward compatibility
async def rewrite_content(
    analysis: ContentAnalysis,
    template: StyleTemplate,
) -> RewrittenScript:
    """
    Rewrite content in the specified style.

    This is a convenience function that maintains backward compatibility
    with the original writer.py design.

    Args:
        analysis: Content analysis from Analyzer stage
        template: Style template to apply

    Returns:
        RewrittenScript with title and script in target style

    Raises:
        WritingError: If rewriting fails
    """
    writer = ContentWriter()
    return await writer.rewrite(analysis, template)


# Batch rewriting for multiple analyses
class MultiVideoWriter:
    """
    Rewrite content for multiple videos.

    Processes multiple analyses efficiently with batch templates.
    """

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize multi-video writer.

        Args:
            provider: LLM provider. If None, uses default from settings.
        """
        self._writer = ContentWriter(provider)

    async def rewrite_multiple(
        self,
        analyses: dict[str, ContentAnalysis],
        template: StyleTemplate,
    ) -> dict[str, RewrittenScript]:
        """
        Rewrite multiple analyses with the same template.

        Args:
            analyses: Dictionary mapping video_id to ContentAnalysis
            template: Style template to apply to all

        Returns:
            Dictionary mapping video_id to RewrittenScript
        """
        results = {}
        errors = []

        for video_id, analysis in analyses.items():
            try:
                script = await self._writer.rewrite(analysis, template)
                results[video_id] = script
            except WritingError as e:
                errors.append((video_id, str(e)))

        # If all rewrites failed, raise an error
        if not results and errors:
            raise WritingError(
                f"Failed to rewrite all {len(analyses)} analyses. "
                f"Errors: {errors}"
            )

        return results

    async def rewrite_multiple_with_templates(
        self,
        analyses: dict[str, ContentAnalysis],
        templates: dict[str, StyleTemplate],
    ) -> dict[str, RewrittenScript]:
        """
        Rewrite multiple analyses with different templates per video.

        Args:
            analyses: Dictionary mapping video_id to ContentAnalysis
            templates: Dictionary mapping video_id to StyleTemplate

        Returns:
            Dictionary mapping video_id to RewrittenScript
        """
        results = {}
        errors = []

        for video_id, analysis in analyses.items():
            try:
                template = templates.get(video_id)
                if template is None:
                    # Use first template as default
                    template = next(iter(templates.values()))

                script = await self._writer.rewrite(analysis, template)
                results[video_id] = script
            except WritingError as e:
                errors.append((video_id, str(e)))

        # If all rewrites failed, raise an error
        if not results and errors:
            raise WritingError(
                f"Failed to rewrite all {len(analyses)} analyses. "
                f"Errors: {errors}"
            )

        return results
