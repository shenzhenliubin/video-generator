# Video Generator - Project Context

## Project Overview

**Goal:** Build an automated pipeline that repurposes YouTube content into new videos.

**Core Value:** Lower the barrier to high-quality video creation by automating the entire workflow from subtitle extraction to video generation.

**Status:** Early Development - Project initialization phase

## Technology Stack

- **Language:** Python 3.11+
- **Video Processing:** MoviePy
- **AI/ML:** OpenAI (GPT/DALL-E), Anthropic (Claude), Replicate (Stability AI)
- **TTS:** ElevenLabs, pyttsx3 (fallback)
- **Data:** Pydantic, SQLAlchemy
- **Async:** asyncio, aiohttp

## Architecture

### 8-Stage Pipeline

```
Watcher → Fetcher → Parser → Analyzer → Writer → Director → Artist/Voice → Renderer
```

1. **Watcher** - Monitors YouTube channels for new videos
2. **Fetcher** - Downloads subtitle files
3. **Parser** - Cleans and segments subtitle text
4. **Analyzer** - Extracts main points using LLM
5. **Writer** - Rewrites content in target style using LLM
6. **Director** - Creates storyboard with scene descriptions
7. **Artist** - Generates images for each scene
8. **Voice** - Generates audio for narration
9. **Renderer** - Combines images and audio into video

### Provider Abstraction Layer

**CRITICAL:** All external API integrations use Strategy + Factory patterns.

- **Base classes:** `LLMProvider`, `ImageProvider`, `TTSProvider` in `src/api/base.py`
- **Factory:** `ProviderFactory` in `src/api/factory.py`
- **Implementations:** `src/api/llm/`, `src/api/image/`, `src/api/tts/`

**Adding a new provider:**
1. Create a class implementing the base interface
2. Register it in `ProviderFactory`
3. No code changes needed in application logic

### Data Flow

```
YouTube Video → Subtitle → Analysis → Rewrite → Storyboard → Images + Audio → Video
```

Each stage saves checkpoints for recovery from failures.

## Code Organization

### Module Structure

```
src/
├── main.py              # CLI entry point (Click framework)
├── config/
│   ├── settings.py      # Pydantic Settings for config
│   └── secrets.py       # Secret management (gitignored)
├── core/
│   ├── pipeline.py      # Pipeline orchestrator
│   └── models.py        # Pydantic data models
├── stages/              # One file per processing stage
├── api/                 # Provider abstraction layer
├── templates/           # Style template system
├── utils/               # Helper functions
└── storage/             # Database, checkpoints, files
```

### Key Files

- `src/core/models.py` - All Pydantic models (VideoMetadata, Transcript, ContentAnalysis, Storyboard, etc.)
- `src/api/factory.py` - Provider instantiation
- `src/core/pipeline.py` - Main pipeline orchestration with checkpoint recovery

## Design Patterns

### Strategy + Factory Pattern

Used for provider abstraction. See `src/api/base.py` for interfaces and `src/api/factory.py` for factory.

### Pipeline Pattern

Each stage is independent, with input/output contracts defined by Pydantic models.

### Template Method

Style templates in `src/templates/` define reusable configurations.

## Conventions

### Code Style

- **Line length:** 100 characters
- **Formatter:** Black
- **Linter:** Ruff
- **Type checking:** mypy (strict mode)

### File Naming

- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

### Testing

- **Framework:** pytest
- **Async:** pytest-asyncio
- **Coverage:** pytest-cov
- **Target:** 100% coverage for critical paths

### Error Handling

- Use specific exception classes
- Log full context on errors
- Implement retry with exponential backoff for external API calls
- Never silently catch exceptions

## Important Constraints

### Open-Closed Principle

Providers MUST be extensible without modifying existing code. Always use the factory pattern, never instantiate providers directly in application code.

### Async-First

All I/O operations use async/await. Synchronous libraries are wrapped in async helpers.

### Checkpoint Recovery

Every stage saves its output. On failure, pipeline resumes from last successful checkpoint.

### Fallback Strategy

Primary provider failure → Try backup provider → Degrade gracefully → Log for monitoring

## Development Workflow

### Adding a New Feature

1. Define data models in `src/core/models.py`
2. Create/implement stage in `src/stages/`
3. Add to pipeline in `src/core/pipeline.py`
4. Write tests in `tests/`
5. Update documentation

### Adding a New Provider

1. Create class implementing the appropriate base interface in `src/api/{type}/`
2. Register in `ProviderFactory.{type}_registry`
3. Add tests
4. Update `.env.example` with any new config

## Environment Variables

Required for development:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (at least one LLM)
- `ELEVENLABS_API_KEY` (for TTS)
- `DATABASE_URL` (default: sqlite:///./video_generator.db)

See `.env.example` for full list.

## Documentation

- **Architecture:** `docs/ARCHITECTURE.md` - Complete system design
- **Product Design:** `docs/design/product-design.md` - Problem statement, approach, success criteria
- **Test Plan:** `docs/design/test-plan.md` - Test strategy and edge cases
- **CEO Plan:** `docs/design/ceo-plan.md` - Strategic vision and roadmap
- **Design System:** `DESIGN.md` - UI/UX design system, colors, typography, components

## Design System

**Always read DESIGN.md before making any visual or UI decisions.**

All font choices, colors, spacing, and aesthetic direction are defined in the design system.

### Frontend Stack (Phase 2)
- **Framework:** React 18 + Next.js 14 (App Router)
- **UI Library:** shadcn/ui (copy-paste components, full customization)
- **Styling:** Tailwind CSS v4+
- **Icons:** Lucide React
- **State:** Zustand (client) + React Query (server)
- **Forms:** React Hook Form + Zod
- **Language:** TypeScript

### Key Design Principles
1. **Modern SaaS Professional** — Clean, Linear/Vercel-inspired aesthetics
2. **Indigo Primary** — `#6366f1` (avoid purple gradients common in AI tools)
3. **Comfortable Density** — Generous spacing for long work sessions
4. **Dark Mode First** — Video creators prefer dark interfaces

Do not deviate from DESIGN.md without explicit user approval.

## Strategic Vision

### Phase 1: Personal Tool (Current)
- Individual YouTube channels
- CLI interface
- Local SQLite database

### Phase 2: Platform Product
- Multi-user support
- Web UI
- Cloud database (PostgreSQL)
- Content asset library
- Template marketplace

## Current Sprint Focus

Project initialization - setting up the foundation for implementation.

## Gotchas

1. **MoviePy only works with Python** - no alternative languages
2. **YouTube API quotas** - implement rate limiting
3. **Image generation costs** - DALL-E ~$0.04/image, track usage
4. **TTS rate limits** - ElevenLabs has strict limits, implement queuing
5. **Checkpoint file size** - clean up old checkpoints to avoid disk bloat

## Contact

For questions about architecture decisions, refer to `docs/ARCHITECTURE.md`.
