# Project X Agent Guide

This repository is the monorepo for Project X, a financial continuity platform. Older architectural and backend materials may still use the historical name Continuum.

## Mission

Help families recover financial information after prolonged inactivity or death by organizing:

- structured asset records
- encrypted supporting documents
- nominee relationships
- release workflows

The system is about information continuity, not financial execution.

## Non-Negotiable Product Constraints

- Never store bank passwords, private keys, crypto seed phrases, or live institution credentials.
- Never build money movement, trading, transaction execution, or executor-like behavior into the product.
- Nominee release is read-only.
- Profile isolation must be preserved at all times.
- Sensitive values and documents must be encrypted before storage.

## Naming Guidance

- Prefer `Project X` in product-facing UI copy and new implementation notes.
- Expect older docs and some package metadata to still say `Continuum`.
- Do not rewrite historical references unless the task is explicitly about renaming or documentation cleanup.

## Repository Map

- `app/`: authenticated operational product UI
- `backend/`: API, business rules, profile boundaries, persistence, and workflow logic
- `site/`: public marketing site
- `docs/`: product, data model, architecture, and workflow context
- `infrastructure/`: deployment-oriented notes
- `tasks/`: scoped implementation prompts and backlog material

## Canonical Local Workflow

Use the root `docker-compose.yml` as the single container entry point for the repo.

Profiles:

- `local`: bind mounts plus live reload for `app`, `backend`, and `site`
- `deployed`: built images without source mounts or autoreload

Commands:

```bash
docker compose --profile local up --build
docker compose --profile deployed up --build
```

Use one profile at a time because the modes publish the same ports.

Environment ownership:

- `app/.env` belongs to the app
- `backend/.env` belongs to backend and local database settings
- `site/.env` belongs to the marketing site

Do not move service env configuration into a root `.env` file.

## Service Boundaries

### `app`

Owns:

- onboarding UX
- asset management UX
- document upload UX
- nominee and advisor management UX
- profile-aware authenticated flows
- user-facing asset entry and review surfaces

Does not own:

- direct database access
- secret storage
- backend-only business rules

Technology and rendering:

- Next.js
- React
- TypeScript
- non-SSR application surface

Product and UX expectations:

- use `Project X` in current product-facing copy, examples, and implementation notes
- keep app and site language, branding, and theming aligned unless a task explicitly separates them
- keep the app as the operational authenticated surface while `site` remains the public SSR surface
- prefer simple language
- avoid legalistic tone in default UI copy
- prioritize clear explanations for onboarding, assets, documents, nominees, and advisor sharing

Frontend safety rules:

- never expose sensitive data
- always call backend APIs for protected operations
- never store secrets in the frontend

### `backend`

Owns:

- API contracts
- profile isolation
- asset and profile persistence
- trigger workflow logic
- encryption and storage boundaries
- authentication flows
- audit-oriented business rules

Implementation expectations:

- use clear service layers
- keep domain logic out of route handlers
- use Pydantic models and dependency injection patterns
- treat advisor and nominee access as restricted overlays on primary data

Technology stack:

- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic

Backend security rules:

- never store plaintext sensitive data
- use envelope encryption
- database values must be encrypted where the domain requires it
- documents stored in S3 must be encrypted
- private buckets and least-privilege access are the default

Domain rules:

- assets belong to a primary profile
- assets belong to asset containers
- assets may have supporting documents
- nominees may only read assets after trigger-based release
- advisors cannot modify protected primary data unless explicitly modeled otherwise

Storage guidance:

- documents must be encrypted before upload
- S3 buckets must be private

### `site`

Owns:

- landing pages
- public product explanations
- public education and positioning
- pricing and marketing-oriented public content

Should not own:

- account systems
- application data entry
- backend domain logic
- financial data storage

Technology and design expectations:

- Next.js SSR
- warm tone
- family safety messaging
- non-technical language

Do not implement authenticated application concerns in the public site. Those belong in `app` and `backend`.

## Domain Model Summary

Core concepts from `docs/`:

- Account: the underlying authenticated human identity
- Profile: the active operational context
- Profile types: primary, advisor, nominee
- Asset container: an institutional relationship such as a bank, broker, insurer, or property grouping
- Asset: a specific account, holding, policy, property, or liability inside a container
- Document: encrypted supporting evidence associated with assets

Important workflow rules:

- inactivity reminders start before nominee escalation
- nominee verification is required before release
- a hold window exists before data becomes available
- access after release is read-only

## Engineering Guardrails

- Preserve the separation between public site, authenticated app, and backend service.
- Keep user-facing claims aligned with the actual implemented workflow.
- Avoid shortcuts that weaken profile scoping, auditability, or encryption boundaries.
- When making Compose or environment changes, keep the root repo workflow authoritative.
- Prefer updating docs when a behavioral or structural change affects how contributors work.
- Prefer this root `AGENTS.md` as the canonical instruction file for the monorepo. Do not recreate duplicated service-level guides unless there is a strong reason to split them again.

## Documentation Sources

The highest-signal project context lives in:

- [README.md](/Users/madhugogineni/Documents/projects/personal/project-x/README.md)
- [docs/ai-system-overview.md](/Users/madhugogineni/Documents/projects/personal/project-x/docs/ai-system-overview.md)
- [docs/architecture/profile-system.md](/Users/madhugogineni/Documents/projects/personal/project-x/docs/architecture/profile-system.md)
- [docs/data-model/asset-containers.md](/Users/madhugogineni/Documents/projects/personal/project-x/docs/data-model/asset-containers.md)
- [docs/workflows/inactivity-trigger.md](/Users/madhugogineni/Documents/projects/personal/project-x/docs/workflows/inactivity-trigger.md)

Use this file as the repo-level contract for all services unless a future task intentionally reintroduces a justified service-specific guide.
