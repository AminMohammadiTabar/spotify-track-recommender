---
name: dms-file-safety
description: Implement or review DMS file uploads, downloads, physical deletion, soft deletion, storage paths and their tests.
---
# DMS file safety

Read `security-audit`, `concurrency-review`, `test-quality`, and `api-contract-review` before changing DMS.

- Validate subsystem and owner types/identifiers server-side. System registration key is `SYSTEM-AUTH-REGISTER`.
- Generate UUID storage names. Never expose filesystem paths in API DTOs or logs.
- Store bytes outside web root. Reject path traversal/symlinks and limit payload length and accepted signatures/extensions.
- Logical deletion must prevent download. Purge requires DELETED state; retain metadata and support retry after a crash.
- Filesystem and database aren't one atomic transaction. Preserve compensation/recovery behavior and record limitations.
- DMS is a separate service using HTTP Basic for the MVP; require HTTPS for network exposure. No AUTH→DMS integration yet.
- Add/adjust integration tests (including malformed media and invalid owners); do not invent results.
