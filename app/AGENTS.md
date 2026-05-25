# Application Agent Guide

This repository contains the main user application.

Technology

Next.js
React
TypeScript

Rendering model

Non-SSR application surface

---

## Naming

Do not use the old product name in product copy, examples, or implementation
notes.

Use "Project X" for now.

---

## Relationship To project-x-site

The app and the site should share the same product language, branding, and
theming unless the user asks otherwise.

The main architectural distinction is that `project-x-app` should be treated as
the non-SSR product application, while `project-x-site` is the SSR public site.

---

## Responsibilities

User onboarding
Asset entry UI
Document uploads
Nominee management
Advisor sharing

---

## UI Principles

Simple
Non legal language
Clear explanations

---

## Security

Never expose sensitive data.

Always call backend APIs.

Never store secrets in frontend.
