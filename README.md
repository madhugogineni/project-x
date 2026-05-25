# Project X Monorepo

Project X is the working monorepo for a financial continuity platform whose older docs still refer to the product as Continuum.

The product helps families recover critical financial information after prolonged inactivity or death. It organizes structured asset records, nominee relationships, and encrypted supporting documents. It does not transfer money, store passwords, or act as an executor.

## Product Scope

The platform exists to preserve information continuity across fragmented financial relationships such as:

- Bank accounts
- Brokerage and demat accounts
- Mutual funds
- Retirement accounts
- Insurance policies
- Real estate records
- Government savings schemes
- Business ownership records
- Loans
- Crypto account references

Core modules:

1. Structured asset registry
2. Encrypted document vault
3. Inactivity detection workflow
4. Nominee release guidance

## Core Domain Rules

- The platform stores information only. It does not move funds or execute transactions.
- Never store bank passwords, private keys, crypto seed phrases, or live institutional credentials.
- Profiles are isolated operational contexts. A person may act as a primary user, advisor, or nominee.
- Cross-profile access is prohibited unless explicitly modeled through shared access rules.
- Nominee release is read-only and only happens after inactivity checks, verification, and a hold window.

## Repository Layout

- `app/`: primary product UI for onboarding, asset management, documents, nominees, and profile-aware workflows
- `backend/`: FastAPI service, profile logic, asset APIs, database access, and platform workflows
- `site/`: public SSR marketing site
- `docs/`: architecture, workflow, and product context
- `infrastructure/`: infrastructure notes and deployment-oriented documentation
- `tasks/`: implementation notes and backlog-style prompts

Contributor and agent guidance is centralized in the root [AGENTS.md](/Users/madhugogineni/Documents/projects/personal/project-x/AGENTS.md).

## Architecture Summary

- `site` explains the product and routes users into the application.
- `app` is the operational interface for authenticated users.
- `backend` exposes the API, enforces profile boundaries, and owns the business rules.
- `db` stores structured application data.
- External document storage and encryption integrations are planned behind the backend boundary.

The current workflow described in `docs/` is:

1. Users register assets and supporting documents.
2. The system monitors inactivity.
3. Reminder and escalation stages fire over time.
4. Nominee verification begins after threshold conditions are met.
5. A hold window passes before read-only release.

## Local Development With Docker Compose

The root [docker-compose.yml](/Users/madhugogineni/Documents/projects/personal/project-x/docker-compose.yml) is now the single Compose entry point for the whole repo.

For day-to-day development, prefer the root [Makefile](/Users/madhugogineni/Documents/projects/personal/project-x/Makefile) and [CONTRIBUTING.md](/Users/madhugogineni/Documents/projects/personal/project-x/CONTRIBUTING.md) over memorizing raw commands.

Setup:

```bash
make env
```

Hot-reload local stack:

```bash
make up
```

This starts:

- `site` on `http://localhost:3020`
- `app` on `http://localhost:3021`
- `backend` on `http://localhost:8020`
- `db` on `localhost:5432`

Behavior in local mode:

- `app`, `backend`, and `site` use bind mounts
- frontend services run dev servers
- backend runs `uvicorn --reload`
- source edits are reflected without rebuilding containers
- dependency changes still require a rebuild

Deployed-style stack without source reload:

```bash
make PROFILE=deployed up
```

Behavior in deployed mode:

- production images are built from each service Dockerfile
- no source bind mounts are used
- frontend services run built Next.js servers
- backend runs the image default command without autoreload

Use one profile at a time because both modes publish the same ports.

## Environment Model

Each service owns its own env file:

- [app/.env.example](/Users/madhugogineni/Documents/projects/personal/project-x/app/.env.example)
- [backend/.env.example](/Users/madhugogineni/Documents/projects/personal/project-x/backend/.env.example)
- [site/.env.example](/Users/madhugogineni/Documents/projects/personal/project-x/site/.env.example)

The intended split is:

- `app/.env`: app public URL and backend API base URL
- `backend/.env`: PostgreSQL credentials plus backend `CONTINUUM_*` settings
- `site/.env`: site public URL plus app URL

Inside Docker Compose, the backend database URL is overridden to point at the `db` service instead of localhost.

Frontend display naming is now environment-driven through `NEXT_PUBLIC_PRODUCT_NAME`, and backend service naming is driven by `CONTINUUM_PROJECT_NAME`.

## Service Responsibilities

### `app`

- User onboarding
- Asset entry and review
- Document upload flows
- Nominee management
- Profile-aware product workflows

### `backend`

- API routing
- Profile and access rules
- Asset and document domain logic
- Trigger workflow orchestration
- Encryption and secure storage boundaries

### `site`

- Marketing pages
- Product education
- Public positioning and conversion flows

The public site should not grow into an authenticated app surface.

## Technical Stack

- Frontend: Next.js, React, TypeScript
- Backend: FastAPI, SQLAlchemy, Pydantic Settings
- Database: PostgreSQL
- Python tooling: `uv`
- Container workflow: Docker Compose

## Current Naming State

- Product-facing implementation should prefer `Project X` for now.
- Some domain docs and package metadata still use `Continuum`.
- When changing user-facing copy, prefer the current product name unless a file is explicitly historical or architectural context.
