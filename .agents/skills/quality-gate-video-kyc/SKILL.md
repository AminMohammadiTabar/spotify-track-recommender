---
name: quality-gate-video-kyc
description: Run evidence-based pre-release code review for the three Video KYC services and report verified test results and residual risks.
---
# Quality gate

Apply `architecture-review`, `java-code-review`, `security-audit`, `concurrency-review`, `test-quality`, `api-contract-review`, and `maven-dependency-audit` relevant sections.

Assess issues by evidence; never invent vulnerabilities to satisfy a mandatory-finding instruction in a generic third-party skill.

## Checks
- Dependencies: three sibling Maven projects, no cross-project dependencies, independent startup classes and ports.
- Database: each service owns its schema/migrations, H2-only for local, PostgreSQL for production.
- Security: CSRF/session auth, role separation, deny-by-default routes, private storage, protected DMS API, Swagger dev/prod gating.
- Reliability: upload cleanup on DB failures, retryable purge, optimistic/pessimistic concurrency as implemented.
- Contracts: HTTP verb, URL, example schema, error code, and actual implemented behavior agree with OpenAPI.
- Tests: negative cases, role checks, path traversal, missing file, duplicate signup.

## Output
Update `docs/QUALITY_REVIEW_FA.md`: (1) checked files; (2) findings with severity/evidence; (3) fixes and unaddressed limitations; (4) precise commands and PASS/FAIL/NOT RUN. A structural check is never a Maven build or an integration-test run.
