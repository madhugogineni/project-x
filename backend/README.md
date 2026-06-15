# Project X API

FastAPI backend for Project X.

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

The API runs on `http://localhost:8020` in the root Docker Compose workflow.

## Environment

`.env.example` contains the required application settings. Set `DATABASE_URL` to whichever Postgres instance you want the backend to use.

- JWT issuer, audience, and secret key
- Optional AWS Secrets Manager bootstrap via `AWS_REGION` and `AWS_SECRETS_MANAGER_SECRET_ID`
- OTP settings, including `LOCAL_OTP` for fixed OTP verification when `ENVIRONMENT=local`
- App ports and local CORS defaults
- An example Postgres connection string you can replace for local, Docker, or hosted databases

The root `docker-compose.yml` owns local and deployed service startup. It passes backend settings from `backend/.env`, so the API works with any external Postgres instance as long as `DATABASE_URL` is set correctly.

## Auth API

- `POST /api/v1/auth/otp/request`
- `POST /api/v1/auth/otp/verify`
- `POST /api/v1/auth/signup/complete`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

## Scripts

```bash
uv run uvicorn main:app --reload --app-dir src
uv run pytest
uv run ruff check .
```
