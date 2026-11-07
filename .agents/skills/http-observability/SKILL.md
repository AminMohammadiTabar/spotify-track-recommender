---
name: http-observability
description: Implement and review safe JSON HTTP request tracing, client IP handling, correlation IDs, action audit events, and Swagger UI access for the three independent video KYC services.
---
# HTTP observability and safe logging — Video KYC

Read `logging-patterns`, `security-audit`, `test-quality`, the `docs/LOGGING_AND_SWAGGER_FA.md` contract and `AGENTS.md` before editing logging code.

- Every HTTP request (even 401/403 and Swagger) must be logged on entry and once on completion with status/duration and correlation ID; preserve MDC cleanup and async safety.
- Emit native Boot Logstash JSON to console and rotating files. Do not introduce a shared Maven module or require external ELK infrastructure.
- `X-Request-ID` must be validated before propagation and be present on responses; do not log full URL query strings or bodies.
- Do not log passwords, cookies, Authorization/CSRF headers, video bytes, session IDs, personal email addresses or full user-submitted filenames.
- For IP addresses, trust Forwarded/X-Forwarded-For only when the **direct socket address** is in an explicit trusted proxy list AND the ingress strips spoofable headers.
- Record domain actions with stable action/outcome identifiers, safe entity IDs and the request correlation ID. Logs are *not* a durable compliance audit trail.
- Keep Swagger UI anonymous-accessible in AUTH when enabled, without weakening authentication/role checks on non-docs endpoints. Swagger is disabled by default outside local development.
- Add tests that exercise status codes, actor capture, IP spoofing, MDC, correlation header and no-login Swagger routing; report what was actually run.
