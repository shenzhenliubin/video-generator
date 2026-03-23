"""
Template Routes - Style Template Management API

Endpoints for creating, reading, updating, and deleting style templates.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.models import (
    APIResponse,
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
)
from src.config.settings import get_settings
from src.core.models import StyleTemplate, TemplateCategory
from src.storage.database import Database
from src.templates.manager import TemplateManager

router = APIRouter(prefix="/api/templates", tags=["templates"])


def get_db() -> Database:
    """Get database instance."""
    settings = get_settings()
    return Database(settings.database_url)


@router.get("", response_model=list[TemplateResponse])
async def list_templates() -> list[TemplateResponse]:
    """
    List all available style templates.

    Returns templates from both YAML files and database.
    """
    try:
        manager = TemplateManager()
        templates = manager.list_all()

        return [
            TemplateResponse(
                id=t.id,
                name=t.name,
                category=t.category.value,
                description=t.description,
                llm_provider=t.llm_provider,
                llm_model=getattr(t, "llm_model", None),
                image_provider=t.image_provider,
                image_model=getattr(t, "image_model", None),
                tts_provider=t.tts_provider,
                tts_model=getattr(t, "tts_model", None),
                scene_duration=t.scene_duration,
                image_style_prompt=t.image_style_prompt,
                voice_id=t.voice_id,
                system_prompt=t.system_prompt,
                temperature=t.temperature,
                max_tokens=getattr(t, "max_tokens", 1000),
            )
            for t in templates
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {e}",
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str) -> TemplateResponse:
    """Get a specific style template by ID."""
    try:
        manager = TemplateManager()
        template = manager.load(template_id)

        return TemplateResponse(
            id=template.id,
            name=template.name,
            category=template.category.value,
            description=template.description,
            llm_provider=template.llm_provider,
            llm_model=getattr(template, "llm_model", None),
            image_provider=template.image_provider,
            image_model=getattr(template, "image_model", None),
            tts_provider=template.tts_provider,
            tts_model=getattr(template, "tts_model", None),
            scene_duration=template.scene_duration,
            image_style_prompt=template.image_style_prompt,
            voice_id=template.voice_id,
            system_prompt=template.system_prompt,
            temperature=template.temperature,
            max_tokens=getattr(template, "max_tokens", 1000),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {e}",
        )


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(template: TemplateCreate) -> TemplateResponse:
    """
    Create a new style template.

    Creates a new YAML file for the template in the templates directory.
    """
    try:
        manager = TemplateManager()

        # Check if template ID already exists
        if manager.exists(template.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Template with ID '{template.id}' already exists. Please use a different ID or update the existing template.",
            )

        # Validate category
        try:
            category = TemplateCategory(template.category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {template.category}",
            )

        # Create StyleTemplate model
        style_template = StyleTemplate(
            id=template.id,
            name=template.name,
            category=category,
            description=template.description,
            llm_provider=template.llm_provider,
            image_provider=template.image_provider,
            tts_provider=template.tts_provider,
            scene_duration=template.scene_duration,
            image_style_prompt=template.image_style_prompt,
            voice_id=template.voice_id,
            system_prompt=template.system_prompt,
            temperature=template.temperature,
            max_tokens=template.max_tokens,
        )

        # Save template via manager
        manager = TemplateManager()
        manager.save(style_template)

        return TemplateResponse(
            id=style_template.id,
            name=style_template.name,
            category=style_template.category.value,
            description=style_template.description,
            llm_provider=style_template.llm_provider,
            llm_model=template.llm_model,
            image_provider=style_template.image_provider,
            image_model=template.image_model,
            tts_provider=style_template.tts_provider,
            tts_model=template.tts_model,
            scene_duration=style_template.scene_duration,
            image_style_prompt=style_template.image_style_prompt,
            voice_id=style_template.voice_id,
            system_prompt=style_template.system_prompt,
            temperature=style_template.temperature,
            max_tokens=style_template.max_tokens,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {e}",
        )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, template: TemplateUpdate) -> TemplateResponse:
    """
    Update an existing style template.

    Updates the YAML file for the template.
    """
    try:
        manager = TemplateManager()
        existing = manager.load(template_id)

        # Update fields
        if template.name is not None:
            existing.name = template.name
        if template.category is not None:
            try:
                existing.category = TemplateCategory(template.category)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {template.category}",
                )
        if template.description is not None:
            existing.description = template.description
        if template.llm_provider is not None:
            existing.llm_provider = template.llm_provider
        if template.image_provider is not None:
            existing.image_provider = template.image_provider
        if template.tts_provider is not None:
            existing.tts_provider = template.tts_provider
        if template.scene_duration is not None:
            existing.scene_duration = template.scene_duration
        if template.image_style_prompt is not None:
            existing.image_style_prompt = template.image_style_prompt
        if template.voice_id is not None:
            existing.voice_id = template.voice_id
        if template.system_prompt is not None:
            existing.system_prompt = template.system_prompt
        if template.temperature is not None:
            existing.temperature = template.temperature
        if template.max_tokens is not None:
            existing.max_tokens = template.max_tokens

        # Save updated template
        manager.save(existing)

        return TemplateResponse(
            id=existing.id,
            name=existing.name,
            category=existing.category.value,
            description=existing.description,
            llm_provider=existing.llm_provider,
            llm_model=template.llm_model or getattr(existing, "llm_model", None),
            image_provider=existing.image_provider,
            image_model=template.image_model or getattr(existing, "image_model", None),
            tts_provider=existing.tts_provider,
            tts_model=template.tts_model or getattr(existing, "tts_model", None),
            scene_duration=existing.scene_duration,
            image_style_prompt=existing.image_style_prompt,
            voice_id=existing.voice_id,
            system_prompt=existing.system_prompt,
            temperature=existing.temperature,
            max_tokens=existing.max_tokens,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update template: {e}",
        )


@router.delete("/{template_id}", response_model=APIResponse)
async def delete_template(template_id: str) -> APIResponse:
    """
    Delete a style template.

    Removes the YAML file for the template.
    """
    try:
        manager = TemplateManager()
        manager.delete(template_id)

        return APIResponse(
            success=True,
            message=f"Template '{template_id}' deleted successfully",
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {e}",
        )
