# Privacy Impact Assessment (Lightweight) -- Night Chess

**Project**: Night Chess -- Chess Puzzle Platform
**Date**: 2026-02-27
**Assessment Type**: Lightweight PIA (MVP scope)
**Assessor**: Security Architect

---

## 1. Personal Data Inventory

### What PII is collected?

| Data Element | Purpose | Legal Basis | Required? |
|-------------|---------|-------------|-----------|
| Email address | Account identifier for login | Legitimate interest (service delivery) | Yes, for registered users. Guests provide no PII. |
| Password | Authentication | Legitimate interest (service delivery) | Yes, for registered users |

**Note**: Guests can use the platform (solve random puzzles) without providing any personal data. PII collection occurs only when a user voluntarily registers to track progress.

### What is NOT collected (MVP)?

- No real name
- No physical address
- No phone number
- No payment information
- No device fingerprinting
- No third-party analytics that collects PII (evaluate before adding any)
- No social login (no data shared with OAuth providers)

---

## 2. Data Storage and Protection

### How is PII stored?

| Data | Storage | Protection |
|------|---------|-----------|
| Email | PostgreSQL (managed, e.g., RDS or Render) | Encrypted at rest (managed DB encryption). Transmitted over TLS. |
| Password | PostgreSQL, as bcrypt hash | bcrypt with cost factor >= 12. Original password never stored. Hash never returned by API. |
| Progress data | PostgreSQL, linked by user ID | User-scoped access control. Not PII itself but user-specific. |

### Where is data processed?

- **Application server**: FastAPI backend (cloud-hosted, single region for MVP)
- **Database**: Managed PostgreSQL (same region as application)
- **Frontend**: Next.js (Vercel or same cloud provider). No PII stored client-side except JWT in cookie.

### Data flow

```
User browser --> [HTTPS/TLS] --> Next.js frontend --> [HTTPS/TLS] --> FastAPI backend --> [TLS] --> PostgreSQL
                                                                           |
                                                                    JWT issued on login
                                                                    (httpOnly cookie)
```

---

## 3. Access Control

### Who has access to PII?

| Actor | Access Level | Justification |
|-------|-------------|---------------|
| The user themselves | Their own email and progress | Self-service via authenticated dashboard |
| Application backend | All user records (programmatic) | Required for authentication and data serving |
| Database administrator | All data (direct DB access) | Infrastructure management. Solo dev for MVP. |

### Who does NOT have access?

- No admin panel exists in MVP. No staff UI to browse user data.
- No third-party services receive PII (no analytics, no email marketing for MVP).
- Other users cannot see another user's email or progress.

---

## 4. Retention and Deletion

| Data | Retention Period | Deletion Trigger |
|------|-----------------|------------------|
| Email + password hash | Active account lifetime | User requests account deletion |
| User progress | Active account lifetime | CASCADE delete with account |
| Application logs | 90 days rolling | Automatic rotation |

### Account deletion process (MVP)

- Provide a `DELETE /api/users/me` endpoint (authenticated)
- Hard delete user record, progress records, and any associated data
- Return confirmation response
- No soft-delete for MVP (simplicity over recoverability)

---

## 5. GDPR Rights Compliance

Assessment of GDPR data subject rights for MVP scope.

| Right | Status | Implementation | Timeline |
|-------|--------|---------------|----------|
| **Right to access** (Art. 15) | Supported | User views their profile and progress via authenticated dashboard | MVP (v1) |
| **Right to erasure** (Art. 17) | Supported | `DELETE /api/users/me` endpoint removes account and all associated data | MVP (v1) |
| **Right to data portability** (Art. 20) | Deferred | Export endpoint for progress data (JSON/CSV download) | v2 |
| **Right to rectification** (Art. 16) | Deferred | Email change endpoint with re-verification | v2 |
| **Right to restrict processing** (Art. 18) | Not applicable | No automated profiling or marketing. User can delete account entirely. | N/A for MVP |
| **Right to object** (Art. 21) | Not applicable | No direct marketing, no profiling | N/A for MVP |
| **Automated decision-making** (Art. 22) | Not applicable | No automated decisions with legal effect. Puzzle selection is random. | N/A |

### GDPR gap analysis

**Acceptable for MVP launch**:
- Right to portability and rectification are deferred but not legally blocking for a small-scale MVP with minimal PII (email only).
- No data processing agreements needed (no third-party processors handle PII in MVP).

**Must address before scaling**:
- If adding email notifications (SendGrid/SMTP): execute Data Processing Agreement with provider.
- If adding analytics (e.g., PostHog, Mixpanel): evaluate whether PII is shared; prefer privacy-first tools.
- If serving EU users at scale: appoint a data protection contact and publish one.

---

## 6. Consent and Legal Basis

### Legal basis for processing

**Legitimate interest** (GDPR Art. 6(1)(f)) -- processing is necessary to deliver the service the user explicitly signed up for. Justification:

- User voluntarily creates an account to track puzzle progress
- Only the minimum data needed (email + password) is collected
- No secondary use of data (no marketing, no profiling, no sharing)
- User can delete their account and all data at any time

### Consent requirements

- No explicit consent checkbox needed for account creation (legitimate interest covers service delivery)
- If email marketing is added later: explicit opt-in consent required (separate checkbox, not pre-ticked)
- Cookie consent: see Section 8 below

---

## 7. Privacy Policy

A basic privacy policy page is required before public launch. It should cover:

- [ ] What data is collected (email, password hash, progress history)
- [ ] Why it is collected (account creation, progress tracking)
- [ ] How it is stored (encrypted database, bcrypt for passwords)
- [ ] Who has access (only the user and system administrators)
- [ ] How long it is retained (account lifetime, deleted on request)
- [ ] User rights (access, deletion; portability and rectification planned)
- [ ] Contact information for privacy inquiries
- [ ] Cookie/token usage explanation

**Action item**: Generate privacy policy content and add a `/privacy` page to the Next.js frontend before public launch.

---

## 8. Cookie and Token Policy

### Decision: JWT in httpOnly cookie

**Recommended approach**: Store JWT in an **httpOnly, Secure, SameSite=Lax** cookie.

| Attribute | Value | Rationale |
|-----------|-------|-----------|
| `httpOnly` | `true` | Prevents JavaScript access, mitigates XSS token theft |
| `Secure` | `true` | Cookie only sent over HTTPS |
| `SameSite` | `Lax` | Prevents CSRF on cross-origin POST requests while allowing normal navigation |
| `Path` | `/api` | Limits cookie scope to API routes |
| `Max-Age` | `900` (15 min for access token) | Short-lived access token |

### Why not localStorage?

| Factor | httpOnly Cookie | localStorage |
|--------|----------------|-------------|
| XSS resistance | Token inaccessible to JavaScript | Token readable by any XSS payload |
| CSRF risk | Requires SameSite + CSRF token for state-changing requests | No CSRF risk (token not auto-sent) |
| Implementation complexity | Slightly higher (cookie config, CSRF consideration) | Simpler |
| **Recommendation** | **Preferred for MVP** | Avoid |

### CSRF mitigation

With `SameSite=Lax`, CSRF protection is handled for POST/PUT/DELETE requests. For additional safety:
- Verify `Origin` header on state-changing requests
- Consider a lightweight CSRF token if `SameSite` browser support is a concern (low risk for modern browsers)

### Cookie consent

- The JWT cookie is **strictly necessary** for authentication (no consent required under ePrivacy Directive)
- If analytics cookies are added later: cookie consent banner required
- For MVP with auth-only cookies: no consent banner needed, but document cookie usage in privacy policy

---

## 9. Risk Summary

| Risk | Likelihood | Impact | Mitigation | Status |
|------|-----------|--------|-----------|--------|
| Email addresses exposed via API bug (IDOR) | Medium | Medium | User-scoped queries, parameterized SQL, JWT user ID enforcement | Control defined |
| Password hash leak via logging | Low | High | Never log password fields, never return hash in API responses | Control defined |
| JWT token theft via XSS | Low | Medium | httpOnly cookie, CSP headers, input sanitization | Control defined |
| No account deletion endpoint at launch | Medium | Low | Implement `DELETE /api/users/me` in MVP | Action item |
| No privacy policy page | High | Low | Generate content and add `/privacy` route | Action item |

---

## 10. Action Items

| Priority | Item | Owner | Target |
|----------|------|-------|--------|
| **Must** (MVP) | Implement `DELETE /api/users/me` endpoint | Dev | Before launch |
| **Must** (MVP) | Publish basic privacy policy at `/privacy` | Dev | Before launch |
| **Must** (MVP) | Verify bcrypt cost factor >= 12 | Dev | During auth implementation |
| **Must** (MVP) | Configure JWT as httpOnly/Secure/SameSite cookie | Dev | During auth implementation |
| **Should** (pre-scale) | Add data export endpoint (right to portability) | Dev | v2 |
| **Should** (pre-scale) | Add email change endpoint (right to rectification) | Dev | v2 |
| **Should** (pre-scale) | Evaluate DPA requirements if adding email service | Dev | Before adding SendGrid/SMTP |

---

## Review Schedule

- **Next review**: Before public launch
- **Trigger for full PIA**: Adding payment processing, third-party analytics, social features, or mobile app with device-level data collection
