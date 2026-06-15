# Backend API Plan

This document captures the current backend API surface required by the
repository docs, along with a few simplifying decisions agreed during planning:

- Use a single OTP request endpoint and a single OTP verify endpoint with a
  `flow` field instead of separate signup/login OTP endpoints.
- Do not use a dedicated `profile/switch` API; clients should send `profile_id`
  on protected resource requests and the backend should validate that access.
- Normal signup creates both `PRIMARY` and `NOMINEE` profiles.
- `ADVISOR` is added separately when advisor capability is enabled.
- Nominee linking is service-driven and happens automatically after signup when
  nominee records match by phone and, when present, email.
- `AccountNomineeScope` is the canonical nominee scope and visibility table.
- Do not use nominee-specific `ProfileAccessScope` in the v1 access model.
- Reuse the main asset and document APIs for nominee access after release
  instead of introducing separate released-resource endpoints.
- Prefer service-layer jobs for trigger workflows; if HTTP trigger endpoints are
  needed, place them under `/system/...` instead of `/internal/...`.

Some of the docs in `/docs` are still placeholders, so this plan reflects the
minimum viable API set implied by the populated architecture, data model, and
workflow docs.

## Auth

### `POST /auth/otp/request`

Starts an OTP flow for a given `flow` like `SIGNUP` or `LOGIN`. Returns an
`otp_session_id`, expiry, and optionally debug OTP in local or dev.

### `POST /auth/otp/verify`

Verifies the OTP for the given `otp_session_id` and `flow`. For `LOGIN`, it can
return auth tokens directly; for `SIGNUP`, it should return a short-lived
verified signup token.

### `POST /auth/signup/complete`

Completes account creation after signup OTP verification. Stores onboarding
details, creates default profiles, attempts nominee auto-linking, and returns
access token, refresh token, and account info.

### `POST /auth/refresh`

Rotates or renews tokens using a valid refresh token. Keeps the session alive
without forcing the user to log in again.

### `POST /auth/logout`

Revokes the current session and optionally the paired refresh token. This is
the standard session termination endpoint.

### `GET /auth/me`

Returns the authenticated account identity and baseline user information.
Useful for restoring app state after refresh or relaunch.

### `GET /auth/sessions`

Lists active and recent login sessions for the account. Powers session
management and device history views.

### `POST /auth/sessions/{session_id}/revoke`

Revokes a specific session except the currently protected one if that rule is
kept. Useful for "log out of other devices" flows.

## Profiles And Access Context

### `GET /profiles`

Lists all profiles available to the authenticated human, such as `PRIMARY`,
`ADVISOR`, and `NOMINEE`. The client can choose one and send that `profile_id`
on protected resource requests.

### `GET /profiles/{profile_id}`

Returns details for one profile and its role metadata. The backend should
validate that the JWT subject is allowed to use that profile.

### `POST /profiles`

Public profile creation should allow only `ADVISOR`. `PRIMARY` and `NOMINEE`
are backend-managed defaults created during signup.

### Profile Access Service Functions

`ProfileAccess` remains part of the backend model for advisor and linked
nominee relationships to primary profiles, but its create and revoke flows can
remain service-layer operations in the first iteration.

## Assets

### `GET /assets`

Lists assets visible to the provided `profile_id`. The backend applies all
access rules here, including nominee release visibility and read-only
restrictions.

### `POST /assets`

Creates a new asset container and its typed detail payload. This is the main
write endpoint for the asset registry flow. Advisor writes are allowed when the
advisor has active `ProfileAccess` to the target primary workspace.

### `GET /assets/{asset_id}`

Returns one asset if it is visible to the requested profile context. For
nominees, the response should already be filtered by release status and
permission level.

### `PATCH /assets/{asset_id}`

Updates an asset when the active profile is allowed to edit it. Nominee
profiles should be blocked from mutation here.

### `DELETE /assets/{asset_id}`

Soft-deletes or deactivates an asset rather than physically removing it. This
is safer for audit and release workflows.

### `GET /assets/types`

Returns the supported asset container types and subtypes. The frontend can use
this to drive asset creation flows from backend metadata.

### `GET /assets/blueprint`

Returns required fields, optional fields, and document support metadata. This
is useful for form generation and validation hints.

## Documents

### `GET /assets/{asset_id}/documents`

Lists documents attached to an asset that are visible to the current profile.
The backend should enforce nominee and document visibility rules here.

### `POST /assets/{asset_id}/documents/initiate-upload`

Starts a backend-controlled encrypted upload flow. Returns upload instructions,
a draft document id, and any storage metadata required.

### `POST /assets/{asset_id}/documents/complete-upload`

Finalizes the upload after storage succeeds. Marks the document active and
links it permanently to the asset.

### `GET /documents/{document_id}`

Returns document metadata, type, size, and access status. This should not
directly stream private storage objects by default.

### `POST /documents/{document_id}/download-url`

Issues a short-lived download URL when the current profile is authorized. This
keeps storage private while still allowing controlled retrieval.

### `DELETE /documents/{document_id}`

Soft-deletes or deactivates a document. This preserves history while removing
it from normal user views.

## Nominees

### `GET /nominees`

Lists nominee records associated with the relevant primary profile. Useful for
showing nominee coverage and readiness.

### `POST /nominees`

Creates a nominee record with relationship and contact details. This is the
starting point for future nominee sharing and trigger-based release.

### `GET /nominees/{nominee_id}`

Returns a nominee's full record and lifecycle state. The response can include
whether the nominee is linked, pending, invited, or removed.

### `PATCH /nominees/{nominee_id}`

Updates nominee details before release occurs. Useful for correcting contact
info or relationship metadata.

### `DELETE /nominees/{nominee_id}`

Deactivates or removes a nominee from future release scope. Prefer soft delete
or status change for traceability.

### `GET /nominees/{nominee_id}/scope`

Returns which assets or containers the nominee may eventually access. This is
the canonical policy layer behind nominee sharing and delayed release.

### `PUT /nominees/{nominee_id}/scope`

Sets or replaces the nominee's asset visibility scope. This lets the primary
user define exactly what the nominee may access later. This works for both
linked and unlinked nominees.

### `PUT /nominees/{nominee_id}/visibility`

Manually grants or revokes visibility on all assigned nominee scope rows or on
a selected subset of `container_id` values. This is revocable and uses the same
canonical nominee scope rows as the release workflow.

### Nominee Linking

There is no public `POST /nominees/{nominee_id}/link-account` endpoint in the
first flow. The backend links nominee records automatically during signup when
the new account matches nominee phone and, when present, email.

## Release And Inactivity

### `GET /release/status`

Returns the current release and inactivity state for the relevant account or
profile context. This includes stages like reminder, escalation, verification,
hold, and released.

### `POST /release/verify-identity`

Records nominee identity verification once the release process has begun. This
is one of the mandatory gates before any visibility is unlocked.

### `POST /release/legal-declaration`

Captures the nominee's legal declaration and audit metadata. This is another
required checkpoint before hold or release.

### `POST /release/cancel`

Cancels an in-progress release if the primary user reappears or a stop
condition is met. This should prevent further visibility changes.

Release visibility should flip the nominee's existing `AccountNomineeScope`
rows rather than creating a second nominee-specific access scope layer.

## System Or Ops Triggers

### `POST /system/inactivity/run-checks`

Executes inactivity evaluation for eligible accounts. Best used by cron, job
runners, or admin tooling if it is exposed over HTTP.

### `POST /system/inactivity/send-reminders`

Sends reminder notifications for accounts crossing the first inactivity
threshold. Should be idempotent so retries do not duplicate communication.

### `POST /system/inactivity/send-escalations`

Sends escalation notifications for accounts crossing the later inactivity
threshold. This advances the workflow but does not release anything yet.

### `POST /system/release/initiate-verification`

Starts nominee verification for accounts that have crossed the release trigger
threshold. This opens the release workflow without exposing assets.

### `POST /system/release/start-hold`

Starts the 7-day hold period after verification prerequisites are satisfied.
Visibility should still remain locked during this stage.

### `POST /system/release/complete`

Completes the release and makes allowed resources visible to nominee profiles.
Asset and document APIs should then naturally reflect that visibility.

In the first implementation these workflow operations can remain service-layer
functions even if HTTP wrappers are documented for future ops usage.
