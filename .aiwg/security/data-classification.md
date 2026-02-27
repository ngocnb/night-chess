# Data Classification -- Night Chess

**Project**: Night Chess -- Chess Puzzle Platform
**Date**: 2026-02-27
**Classification Authority**: Security Architect
**Scope**: MVP (v1) data types only

---

## Classification Levels

| Level | Definition | Examples |
|-------|-----------|----------|
| **Public** | No confidentiality requirement. Freely available or intended for public consumption. | Lichess puzzle data |
| **Internal** | Low sensitivity. Should not be publicly exposed but compromise causes minimal harm. | User progress, application logs |
| **Confidential** | Contains PII or business-sensitive data. Unauthorized access causes material harm. | User email addresses |
| **Restricted** | Credential material or secrets. Exposure directly enables account compromise or system breach. | Password hashes, JWT tokens, API keys |

---

## Data Inventory

| Data Type | Classification | Rationale |
|-----------|---------------|-----------|
| Lichess puzzles (FEN, moves, rating, themes, game URL) | **Public** | Open source, CC0 license from Lichess database. No confidentiality requirement. |
| User email | **Confidential (PII)** | Personal identifier under GDPR. Used for account creation and login. |
| Password hash (bcrypt) | **Restricted** | Credential material. Even hashed, exposure enables offline brute-force attacks. Must never leave the database. |
| JWT access tokens | **Restricted** | Short-lived session credentials. Bearer token grants full user access until expiry. |
| JWT refresh tokens | **Restricted** | Longer-lived credential. Compromise enables persistent session hijacking. |
| User progress (puzzle results, timestamps, time spent) | **Internal** | User-specific behavioral data. Not high sensitivity but should be access-controlled. |
| Application logs | **Internal** | May contain request metadata (IPs, user agents, request paths). Should not contain PII if logging is configured correctly. |
| Database connection strings | **Restricted** | Infrastructure credential. Exposure grants direct database access. |
| Environment variables / secrets | **Restricted** | May contain API keys, database URLs, JWT signing keys. |

---

## Controls by Classification Level

### Public

| Control | Requirement |
|---------|------------|
| **Encryption at rest** | Not required. |
| **Encryption in transit** | HTTPS recommended (served via TLS regardless since all traffic goes through HTTPS). |
| **Access control** | None. Available to all users including unauthenticated guests. |
| **Retention** | Indefinite. Refreshed when Lichess releases updated puzzle database. |
| **Disposal** | Standard deletion. No special procedures. |
| **Backup** | Re-downloadable from source. Backup optional. |

### Internal

| Control | Requirement |
|---------|------------|
| **Encryption at rest** | Managed PostgreSQL encryption (RDS default or Render managed). No additional application-level encryption needed for MVP. |
| **Encryption in transit** | Required. TLS for all API traffic. Database connections over TLS. |
| **Access control** | User-scoped. Users access only their own progress data. No cross-user access. Enforced at the API layer via JWT user ID claim. |
| **Retention** | Active account lifetime. Delete when user deletes account. Logs: 90 days rolling retention. |
| **Disposal** | CASCADE delete with user account. Logs: automatic rotation/expiry. |
| **Logging** | Sanitize logs to exclude PII. Log puzzle IDs and user IDs (opaque), not emails. |

### Confidential

| Control | Requirement |
|---------|------------|
| **Encryption at rest** | Required. Managed database encryption (RDS encryption at rest or equivalent). |
| **Encryption in transit** | Required. TLS everywhere. Never transmit email in URL parameters or query strings. |
| **Access control** | User can view their own email via authenticated profile endpoint. No admin panel exposes user emails in MVP. No bulk export. |
| **Retention** | Active account lifetime. Must be deletable on user request (GDPR right to erasure). |
| **Disposal** | Hard delete from database on account deletion. Purge from backups within 30 days (acceptable for MVP; document as known gap if backup purge is not automated). |
| **Minimization** | Collect only email. No name, address, phone, or other PII for MVP. |

### Restricted

| Control | Requirement |
|---------|------------|
| **Encryption at rest** | Required. Password hashes stored via bcrypt (cost factor >= 12). JWT signing key stored in environment variable or secrets manager, never in code or version control. |
| **Encryption in transit** | Required. TLS. JWT tokens transmitted only in httpOnly cookies or Authorization headers. Never in URL parameters. |
| **Access control** | Password hashes: never returned by any API endpoint, never included in any response payload, never logged. JWT tokens: issued only to authenticated users. Signing key: accessible only to the application process. |
| **Retention** | Password hashes: account lifetime, replaced on password change. JWT access tokens: 15-minute expiry (recommended). Refresh tokens: 7-day expiry with rotation. |
| **Disposal** | Password hashes: hard delete with account. JWT tokens: short-lived, expire naturally. Implement token revocation list if refresh tokens are stored server-side. |
| **Incident response** | If password hashes are exposed: force password reset for all affected users. If JWT signing key is compromised: rotate key immediately, invalidating all active sessions. |

---

## Implementation Checklist (MVP)

- [ ] bcrypt cost factor >= 12 for password hashing
- [ ] JWT signing key loaded from environment variable, not hardcoded
- [ ] No password hash or JWT token appears in any API response body
- [ ] No PII (email) in application logs
- [ ] All database connections use TLS
- [ ] All API traffic served over HTTPS
- [ ] User progress queries filtered by authenticated user ID (no IDOR)
- [ ] Parameterized queries via SQLAlchemy ORM (no raw SQL string concatenation)
- [ ] `.env` file in `.gitignore`

---

## Review Schedule

- **Next review**: Before public launch or at end of MVP development (whichever comes first)
- **Trigger for re-classification**: Adding payment processing, health data, social features, or third-party integrations that handle user data
