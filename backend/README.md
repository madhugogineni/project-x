# Project X API

FastAPI backend for the Project X platform.

## Stack

- FastAPI
- SQLAlchemy 2.x
- Pydantic Settings
- PostgreSQL via `asyncpg`
- `uv` for environment and dependency management

## Getting Started

```bash
uv sync --extra dev
uv run uvicorn main:app --reload --app-dir src
```

The API runs on `http://localhost:8020` in the local Docker workflow.

## Environment

Copy `.env.example` to `.env` and adjust values for the local database, frontend origins, and storage configuration.

## Scripts

```bash
uv run uvicorn main:app --reload --app-dir src
uv run pytest
uv run ruff check .
uv run ruff format .
```
