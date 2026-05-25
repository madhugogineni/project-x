# Contributing Workflow

This repo is a monorepo for Project X. The fastest way to stay productive is to treat the root as the control plane and the service folders as implementation surfaces.

## How To Start

1. Create local env files if you do not already have them.

```bash
make env
```

2. Install service dependencies when needed.

```bash
cd app && npm install
cd site && npm install
cd backend && uv sync --extra dev
```

3. Start the local stack.

```bash
make up
```

4. Verify the stack.

```bash
make smoke
```

The default `Makefile` profile is `local`. For the non-reload container mode, use `PROFILE=deployed`.

```bash
make PROFILE=deployed up
```

## Where To Change What

### `app/`

Use this folder for:

- authenticated user flows
- onboarding
- asset and document UI
- nominee and advisor UI
- product-shell interactions

### `backend/`

Use this folder for:

- API routes
- validation and schemas
- profile isolation rules
- asset and document domain logic
- database access and service-layer changes
- request logging and backend observability

### `site/`

Use this folder for:

- landing pages
- product education
- marketing messaging
- public-facing copy

### `docs/`

Use this folder for:

- architecture notes
- domain rules
- workflow descriptions
- implementation context that should survive code changes

## Common Commands

### Stack control

```bash
make up
make down
make restart
make ps
```

### Logs

```bash
make logs
make logs-app
make logs-backend
make logs-site
make logs-db
```

### Verification

```bash
make smoke
make test
make test-ui
make lint
make format
```

### Git hooks

```bash
make hooks-install
make hooks-run
```

## Testing Expectations

- Backend changes should keep `backend/tests` green.
- App changes should preserve or extend the Playwright UI coverage in `app/tests/ui`.
- Site changes do not currently require UI automation unless the scope expands.
- After Docker or env changes, run `make smoke`.
- Use `cd backend && uv run python -m pytest` if you need to invoke backend tests directly.

## Environment Ownership

Each service owns its own env file:

- `app/.env`
- `backend/.env`
- `site/.env`

Do not introduce a root `.env` for service runtime configuration.

## Notes On Observability

- Backend request and lifecycle logs are structured and emitted to container stdout.
- Use `make logs-backend` first when API behavior is unclear.
- The smoke test checks database connectivity, site, app, health, and readiness in one pass.
