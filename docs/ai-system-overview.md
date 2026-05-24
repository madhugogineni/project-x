
# System Overview

Continuum is a fintech SaaS platform designed to ensure financial information continuity.

The system helps families discover financial assets when a user becomes inactive or passes away.

The platform does not move money or execute financial transactions.

Instead, it organizes structured information.

---

## System Components

Frontend Application

Used by users to register assets and upload documents.

Backend API

Handles authentication, encryption, asset management, and trigger workflows.

Database

Stores encrypted asset data.

Document Storage

Stores encrypted documents.

Trigger Engine

Detects inactivity and initiates nominee verification workflows.

---

## Lifecycle

User registers assets.

User uploads supporting documents.

System monitors inactivity.

If inactivity threshold passes:

User receives reminders.

If no response:

Nominee verification workflow begins.

After verification and hold window:

Nominee gains read-only access.
