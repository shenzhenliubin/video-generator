"""
Analyzer Stage - Content Analysis

Uses LLM to analyze subtitle content and extract main points, summary, and topics.
"""

import json
from typing import Any

from src.api.base import LLMProvider
from src.api.factory import ProviderFactory
from src.config.settings import get_settings
from src.core.models import ContentAnalysis, ParsedContent


class ContentAnalyzer:
    """
    Analyze subtitle content using LLM.

    Extracts main points, summary, topics, and sentiment from content.
    """

    # System prompt for content analysis
    SYSTEM_PROMPT = """You are a content analysis expert. Your task is to analyze video subtitles and extract:

1. Main Points: 3-5 key takeaways or arguments from the content
2. Summary: A concise 2-3 sentence summary of what the content is about
3. Topics: Relevant topics/tags (e.g., "technology", "business", "health")
4. Sentiment: Overall emotional tone (positive, negative, neutral, inspirational, etc.)

Respond ONLY in valid JSON format:
{
  "main_points": ["point 1", "point 2", "point 3"],
  "summary": "Concise summary here.",
  "topics": ["topic1", "topic2", "topic3"],
  "sentiment": "neutral"
}

Keep main points under 20 words each. Keep summary under 50 words.
Topics should be lowercase, single words or short phrases.
Sentiment should be one word: positive, negative, neutral, inspirational, warning, or humorous."""

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize content analyzer.

        Args:
            provider: LLM provider. If None, uses default from settings.
        """
        if provider is None:
            settings = get_settings()
            config = settings.get_llm_config(settings.default_llm_provider)
            self.provider = ProviderFactory.create_llm(settings.default_llm_provider, **config)
        else:
            self.provider = provider

    async def analyze(self, content: ParsedContent) -> ContentAnalysis:
        """
        Analyze parsed subtitle content.

        Args:
            content: Parsed content from Parser stage

        Returns:
            ContentAnalysis with main points, summary, topics, sentiment

        Raises:
            AnalysisError: If analysis fails
        """
        try:
            # Prepare the user prompt with content
            user_prompt = self._prepare_prompt(content)

            # Call LLM - use generate_text method
            full_prompt = f"{self.SYSTEM_PROMPT}\n\n{user_prompt}"
            response = await self.provider.generate_text(
                prompt=full_prompt,
                max_tokens=500,
                temperature=0.3,  # Lower temperature for more focused analysis
            )

            # Parse the JSON response
            analysis_data = self._parse_response(response)

            return ContentAnalysis(
                video_id=content.video_id,
                main_points=analysis_data.get("main_points", []),
                summary=analysis_data.get("summary", ""),
                topics=analysis_data.get("topics", []),
                sentiment=analysis_data.get("sentiment"),
            )

        except Exception as e:
            raise AnalysisError(f"Failed to analyze content for {content.video_id}: {e}") from e

    def _prepare_prompt(self, content: ParsedContent) -> str:
        """
        Prepare user prompt with content.

        Args:
            content: Parsed content

        Returns:
            Formatted prompt string
        """
        # Use clean text, but truncate if too long
        text_to_analyze = content.clean_text

        # Truncate to ~3000 characters to stay within token limits
        if len(text_to_analyze) > 3000:
            text_to_analyze = text_to_analyze[:3000] + "..."

        return f"""Analyze the following video subtitle content:

Video ID: {content.video_id}
Language: {content.language}
Word Count: {content.word_count}

Content:
{text_to_analyze}

Provide analysis in JSON format as specified."""

    def _parse_response(self, response: str) -> dict[str, Any]:
        """
        Parse LLM response as JSON.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed dictionary with analysis data

        Raises:
            AnalysisError: If response cannot be parsed as JSON
        """
        # Try to extract JSON from response
        # LLM might wrap JSON in markdown code blocks
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
        except json.JSONDecodeError as e:
            # Try to find JSON object in response
            try:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    return json.loads(json_str)
            except Exception:
                pass

            raise AnalysisError(f"Failed to parse LLM response as JSON: {e}")


class AnalysisError(Exception):
    """Raised when content analysis fails."""
    pass


# Convenience function for backward compatibility
async def analyze_content(content: ParsedContent) -> ContentAnalysis:
    """
    Analyze subtitle content.

    This is a convenience function that maintains backward compatibility
    with the original analyzer.py design.

    Args:
        content: Parsed content from Parser stage

    Returns:
        ContentAnalysis with extracted insights

    Raises:
        AnalysisError: If analysis fails
    """
    analyzer = ContentAnalyzer()
    return await analyzer.analyze(content)


# Batch analysis for multiple videos
class MultiVideoAnalyzer:
    """
    Analyze content for multiple videos.

    Processes multiple parsed contents efficiently.
    """

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize multi-video analyzer.

        Args:
            provider: LLM provider. If None, uses default from settings.
        """
        self._analyzer = ContentAnalyzer(provider)

    async def analyze_multiple(
        self,
        contents: dict[str, ParsedContent],
    ) -> dict[str, ContentAnalysis]:
        """
        Analyze multiple contents.

        Args:
            contents: Dictionary mapping video_id to ParsedContent

        Returns:
            Dictionary mapping video_id to ContentAnalysis
        """
        results = {}
        errors = []

        for video_id, content in contents.items():
            try:
                analysis = await self._analyzer.analyze(content)
                results[video_id] = analysis
            except AnalysisError as e:
                errors.append((video_id, str(e)))

        # If all analyses failed, raise an error
        if not results and errors:
            raise AnalysisError(
                f"Failed to analyze all {len(contents)} videos. "
                f"Errors: {errors}"
            )

        return results
