# Continuum

Continuum is a Digital Financial Continuity Platform designed to help families discover and organize financial assets after the unexpected death of a family member.

The system stores structured financial information and encrypted supporting documents.

It does NOT transfer assets, manage passwords, or act as an executor.

Its purpose is information continuity.

---

## Core Problem

Financial assets in India are fragmented across banks, brokers, insurance providers, retirement accounts, property registries, and government savings schemes.

Families often do not know:

- Which accounts exist
- Which institutions hold assets
- Whether nominees exist
- Where documents are stored

When sudden death occurs, families struggle to reconstruct the financial picture.

Continuum solves this by allowing users to store structured financial information and documents.

---

## Core Product Modules

1. Structured Asset Registry  
2. Encrypted Document Vault  
3. Inactivity Detection Engine  
4. Nominee Claim Guidance System  

---

## Repository Structure

continuum-web  
Marketing and public facing SSR website.

continuum-app  
Main user application for managing financial assets.

continuum-api  
Backend services, database models, encryption, and business logic.

---

## Architecture Overview

Users create accounts and manage financial asset records organized into asset containers.

If prolonged inactivity is detected, the system begins a verification workflow before granting nominees access to the stored asset information.

---

## Important Constraints

The platform NEVER stores:

- Bank passwords
- Crypto seed phrases
- Private keys
- Live API connections to institutions

It stores information only.

---

## Key Domain Concepts

Account  
Represents a human identity.

Profile  
Represents an operational context.

Profiles types:
- Primary
- Advisor
- Nominee

Asset Container  
Represents an institutional relationship such as a bank or broker.

Asset  
Represents a specific account or holding within a container.

Document  
Encrypted file associated with an asset.

---

## Technology Stack

Frontend
Next.js

Backend
FastAPI

Database
PostgreSQL

Storage
Amazon S3

Hosting
AWS EC2

CDN
Cloudflare

---

## Development Philosophy

The system prioritizes:

Security  
Clarity  
Legal defensibility  
Data integrity  

All sensitive data must be encrypted.
