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
        "dramatic": """你是一位戏剧性故事讲述者。请将内容改写为：
- 情感强烈和悬念
- 生动的意象和隐喻
- 戏剧性的节奏和张力
- 强有力的、令人难忘的语言

请创作出像电影预告片或戏剧性旁白那样的内容。

重要：请用中文输出改写后的剧本。""",

        "humorous": """你是一位喜剧作家。请将内容改写为：
- 诙谐的幽默和巧妙的文字游戏
- 轻松愉快的娱乐语调
- 可引起共鸣的例子和轶事
- 引人入胜的喜剧节奏

让它既有趣又能传达核心信息。

重要：请用中文输出改写后的剧本。""",

        "educational": """你是一位专业的教育者。请将内容改写为：
- 清晰易懂的解释
- 结构化的学习流程
- 实用的例子和类比
- 可执行的建议

让复杂的主题变得容易理解。

重要：请用中文输出改写后的剧本。""",

        "cinematic": """你是一位编剧。请将内容改写为：
- 视觉化的、场景设置的语言
- 史诗般的电影规模
- 情感共鸣
- 值得拍摄的电影对话和旁白

写得像可以成为纪录片或故事片一样。

重要：请用中文输出改写后的剧本。""",

        "documentary": """你是一位纪录片旁白。请将内容改写为：
- 信息丰富、事实性的语调
- 引人入胜的叙事
- 清晰的叙事弧线
- 专业的广播风格

让它听起来像高质量的纪录片旁白。

重要：请用中文输出改写后的剧本。""",

        "news": """你是一位新闻主播。请将内容改写为：
- 简洁有力的表达
- 新闻报道的精确性
- 紧迫感和相关性
- 清晰的标题和导语

写得像突发新闻报道一样。

重要：请用中文输出改写后的剧本。""",
    }

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize content writer.

        Args:
            provider: LLM provider. If None, uses default from settings.
        """
        if provider is None:
            settings = get_settings()
            config = settings.get_llm_config(settings.default_llm_provider)
            self.provider = ProviderFactory.create_llm(settings.default_llm_provider, **config)
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
