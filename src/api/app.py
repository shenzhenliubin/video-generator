"""
FastAPI Application - Video Generator Web API

Main application that brings together all API routes and middleware.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import channels, system, templates, videos
from src.config.settings import get_settings
from src.scheduler import get_scheduler
from src.storage.database import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for the FastAPI app.

    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    db = Database(settings.database_url)

    # Create database tables
    db.create_tables()

    print("✓ Database initialized")

    # Start background scheduler
    scheduler = get_scheduler()
    await scheduler.start()

    print(f"✓ API running on http://0.0.0.0:{settings.api_port}")

    yield

    # Shutdown
    await scheduler.stop()
    print("Shutting down API...")


# Create FastAPI app
app = FastAPI(
    title="Video Generator API",
    description="YouTube content repurposing pipeline - automated video generation from subtitles",
    version="0.2.0",
    lifespan=lifespan,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(templates.router)
app.include_router(channels.router)
app.include_router(videos.router)
app.include_router(system.router)


# Root endpoint
@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Video Generator API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": f"Internal server error: {str(exc)}",
        },
    )
