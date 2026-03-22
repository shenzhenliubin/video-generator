"""
SiliconFlow Image Generation Provider

SiliconFlow (硅基流动) 提供多种文生图模型，完全兼容 OpenAI 接口格式。

支持的模型:
- FLUX.1-dev: 高质量图像生成
- FLUX.1-schnell: 快速图像生成
- Kolors: 快手出品，中文优化

API Documentation: https://docs.siliconflow.cn/cn/userguide/capabilities/images
Base URL: https://api.siliconflow.cn/v1
"""

import os
from typing import Any

import httpx
from openai import AsyncOpenAI

from src.api.base import ImageProvider


def _create_httpx_client() -> httpx.AsyncClient:
    """
    Create an httpx client with proxy disabled.

    This avoids SOCKS proxy errors when proxy is configured in environment.
    """
    # Temporarily clear proxy environment variables
    proxy_vars = [
        "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
        "all_proxy", "ALL_PROXY", "socks_proxy", "socks5_proxy"
    ]
    original_env = {}
    for var in proxy_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]

    try:
        # Create client without proxy
        return httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    finally:
        # Restore original environment
        for var, value in original_env.items():
            os.environ[var] = value


class SiliconFlowImage(ImageProvider):
    """
    SiliconFlow image generation provider implementation.

    Uses OpenAI-compatible interface with SiliconFlow's base URL.
    Supports FLUX.1 and Kolors models.
    """

    DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"

    # Aspect ratio to size mapping
    ASPECT_RATIO_SIZES = {
        "1:1": "1024x1024",
        "16:9": "1024x576",
        "9:16": "576x1024",
        "4:3": "1024x768",
        "3:4": "768x1024",
        "21:9": "1024x440",
    }

    # Supported models
    POPULAR_MODELS = {
        "flux-dev": "black-forest-labs/FLUX.1-dev",
        "flux-schnell": "black-forest-labs/FLUX.1-schnell",
        "kolors": "Kwai-Kolors/Kolors",
    }

    # Supported styles
    SUPPORTED_STYLES = [
        "realistic",
        "cinematic",
        "anime",
        "digital-art",
        "oil-painting",
        "watercolor",
        "3d-render",
        "photography",
        None,  # No style
    ]

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        http_client: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize SiliconFlow image provider.

        Args:
            api_key: SiliconFlow API key from https://cloud.siliconflow.cn
            base_url: API base URL (default: https://api.siliconflow.cn/v1)
            model: Model identifier (default: black-forest-labs/FLUX.1-schnell)
            http_client: Custom httpx client (optional)
            **kwargs: Additional OpenAI client parameters
        """
        self._api_key = api_key
        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._model = model or self.DEFAULT_MODEL

        # Create httpx client without proxy if not provided
        if http_client is None:
            http_client = _create_httpx_client()

        # Initialize AsyncOpenAI client with SiliconFlow endpoint
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            http_client=http_client,
            **kwargs,
        )

    @property
    def model(self) -> str:
        """Get the current model identifier."""
        return self._model

    def _apply_style_to_prompt(self, prompt: str, style: str | None) -> str:
        """
        Apply style modifier to prompt.

        Args:
            prompt: Original prompt
            style: Style to apply

        Returns:
            Modified prompt with style
        """
        if style is None or style not in self.SUPPORTED_STYLES:
            return prompt

        style_prompts = {
            "realistic": "hyperrealistic, photorealistic, highly detailed, 8k",
            "cinematic": "cinematic lighting, dramatic atmosphere, movie scene",
            "anime": "anime style, manga art, vibrant colors",
            "digital-art": "digital art, trending on artstation",
            "oil-painting": "oil painting, classical art style",
            "watercolor": "watercolor painting, soft colors",
            "3d-render": "3d render, octane render, highly detailed",
            "photography": "professional photography, dslr, sharp focus",
        }

        style_prompt = style_prompts.get(style, "")
        if style_prompt:
            return f"{prompt}, {style_prompt}"
        return prompt

    def _get_size_for_aspect_ratio(self, aspect_ratio: str) -> str:
        """
        Get image size for aspect ratio.

        Args:
            aspect_ratio: Aspect ratio string (e.g., "16:9")

        Returns:
            Size string (e.g., "1024x576")
        """
        return self.ASPECT_RATIO_SIZES.get(aspect_ratio, "1024x1024")

    async def generate_image(
        self,
        prompt: str,
        style: str | None = None,
        aspect_ratio: str = "16:9",
        **kwargs: Any,
    ) -> bytes:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image
            style: Optional style modifier (realistic, cinematic, anime, etc.)
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4, 21:9)
            **kwargs: Provider-specific parameters (num_inference_steps, seed, etc.)

        Returns:
            Image data as bytes
        """
        # Apply style to prompt
        enhanced_prompt = self._apply_style_to_prompt(prompt, style)

        # Get size for aspect ratio
        size = self._get_size_for_aspect_ratio(aspect_ratio)

        # Extract additional parameters
        num_inference_steps = kwargs.get("num_inference_steps", 20)
        seed = kwargs.get("seed", None)

        # Build extra body parameters
        extra_body: dict[str, Any] = {
            "step": num_inference_steps,
        }
        if seed is not None:
            extra_body["seed"] = seed

        # Generate image
        response = await self._client.images.generate(
            model=self._model,
            prompt=enhanced_prompt,
            size=size,
            n=1,
            extra_body=extra_body,
        )

        # Get image URL and download
        image_url = response.data[0].url
        if image_url is None:
            raise ValueError("No image URL returned from API")

        # Download image data
        async with httpx.AsyncClient(timeout=30.0) as client:
            image_response = await client.get(image_url)
            image_response.raise_for_status()
            return image_response.content

    def get_supported_styles(self) -> list[str]:
        """
        Get list of supported style names.

        Returns:
            List of style identifiers
        """
        return [s for s in self.SUPPORTED_STYLES if s is not None]

    @classmethod
    def get_available_models(cls) -> dict[str, str]:
        """
        Get mapping of model aliases to full model identifiers.

        Returns:
            Dictionary mapping short names to full model paths
        """
        return cls.POPULAR_MODELS.copy()

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"SiliconFlowImage(model={self._model!r}, base_url={self._base_url!r})"
