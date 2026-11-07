---
name: auth-security-mvc
description: Review or implement AUTH user signup/login/logout, MVC Mustache, roles, CSRF, password encoding, and user account endpoints.
---
# AUTH security + MVC

Read `security-audit`, `spring-boot-patterns`, `java-code-review`, `test-quality` and current AUTH security chains.

- Distinguish application login authentication (Spring Security sessions) from future video identity verification.
- Never expose password hashes, credentials, CSRF tokens in logs or user-visible error internals.
- Validate registration input at service and web boundaries; normalize email; hash with BCrypt; enforce unique email in DB.
- User self-registration always receives `ROLE_USER`. Bootstrap ADMIN only with explicit environment config.
- Keep CSRF protection for session-backed forms and JSON registration. Restrict roles in SecurityFilterChain, not only UI links.
- Display disabled video selector only; never simulate completed identity verification or upload in this phase.
- Swagger's security documentation must match real HTTP behavior; Swagger UI and `/v3/api-docs/**` are anonymous-accessible when enabled, while business APIs remain protected. Production docs disabled by default. Preserve `http-observability` logging and secret-redaction rules.
