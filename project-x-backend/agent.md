# Backend Agent Guide

This repository contains the backend service for Continuum.

Technology stack

FastAPI
PostgreSQL
SQLAlchemy
Pydantic

---

## Responsibilities

Authentication
Profile management
Asset registry
Document encryption
Trigger workflows
Audit logs

---

## Security Rules

Never store plaintext sensitive data.

Use envelope encryption.

Database values must be encrypted.

Documents stored in S3 must be encrypted.

---

## Asset Model

Assets belong to a Primary profile.

Assets belong to asset containers.

Assets may have supporting documents.

---

## Document Storage

Documents must be encrypted before upload.

S3 buckets must be private.

---

## Access Control

Profile isolation must be enforced.

Nominees may only read assets after trigger release.

Advisors cannot modify assets.

---

## Coding Standards

Use Pydantic models.

Use dependency injection.

Write clear service layers.
