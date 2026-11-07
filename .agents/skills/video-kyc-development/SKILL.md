---
name: video-kyc-development
description: Design or modify AUTH, DMS, or WORKFLOW in this independent Spring Boot workspace, preserving agreed phase boundaries.
---
# Video KYC development contract

Read `AGENTS.md` / `CLAUDE.md` at the workspace root and the affected service `pom.xml`, `application*.yml`, Flyway scripts, existing tests and controllers before editing.

## Non-negotiable architecture
- Three independent Maven/Spring Boot projects in sibling directories: auth (8080), dms (8081), workflow (8082).
- No shared parent POM, Java API invocation, module dependency, entity reuse, or cross-schema FK. External inter-service communication is a later phase.
- AUTH MVC/Mustache/Spring Security; it shows a disabled video upload button and never sends file bytes in this phase.
- AUTH workflow statuses are a hard-coded enum only. WORKFLOW is a scaffold: do not invent a state machine implementation.
- DMS owns files and metadata. Store under SUBSYSTEM/YYYY/MM/DD/OWNER_ID/UUID.extension; never use submitted path names.
- PostgreSQL/Flyway are authoritative; H2 separate migrations for development, never mix DB migrations.
- springdoc Swagger UI/API contracts must remain accurate for all services and disabled by default in production.

## Implementation loop
1. Read relevant `architecture-review`, `spring-boot-patterns`, `security-audit`, and `api-contract-review` skills.
2. Implement minimal correct change, keeping public DTOs and persistence entities separate.
3. Test success, invalid input, unauthorized access, and concurrency/file rollback cases when applicable.
4. Run `python scripts/verify_workspace.py` from the workspace root; run each project's `./mvnw clean verify` when Java 25 and dependencies are available.
5. Record actual outcomes (never claim unrun tests passed), residual risks, and source code changes in `docs/QUALITY_REVIEW_FA.md`.
