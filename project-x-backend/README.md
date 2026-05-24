# Continuum API

FastAPI backend for the Continuum platform.

## Stack

- FastAPI
- SQLAlchemy 2.x
- Pydantic Settings
- PostgreSQL via `asyncpg`
- `uv` for environment and dependency management

## Getting Started

```bash
uv sync --extra dev
uv run uvicorn continuum_api.main:app --reload
```

The API runs on `http://localhost:8000`.

## Environment

Copy `.env.example` to `.env` and adjust values for the local database, frontend origins, and storage configuration.

## Scripts

```bash
uv run uvicorn continuum_api.main:app --reload
uv run pytest
uv run ruff check .
```
