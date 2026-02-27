# ADR-001: JWT-based Authentication with HttpOnly Cookies

**Status**: Accepted
**Date**: 2026-02-27
**Deciders**: Developer (solo)

---

## Context

Night Chess needs an authentication system that:

1. Supports the web frontend (Next.js, v1) and a future mobile client (Flutter, v2) without backend changes
2. Is stateless enough for a solo developer to operate without managing server-side session infrastructure
3. Handles PII (email, password) with baseline security appropriate for a non-payment, non-health application
4. Works with the "guest-first" design where most users never authenticate -- auth must not interfere with the unauthenticated puzzle flow

The developer is new to FastAPI and needs a pattern that is well-documented with established reference implementations.

## Decision

Use **JWT access tokens** (short-lived) combined with **refresh tokens** (longer-lived, stored as HttpOnly cookies) for web authentication.

**Specifics**:

| Parameter            | Value                                      |
|----------------------|--------------------------------------------|
| Access token TTL     | 15 minutes                                 |
| Access token storage | In-memory (JavaScript variable, not localStorage) |
| Refresh token TTL    | 7 days                                     |
| Refresh token storage| HttpOnly, Secure, SameSite=Lax cookie scoped to `/api/v1/auth` |
| Signing algorithm    | HS256 (HMAC-SHA256)                        |
| Password hashing     | bcrypt, cost factor 12 minimum             |
| Token library        | PyJWT (backend), jose (frontend if needed) |
| Refresh rotation     | Yes -- new refresh token issued on each refresh |
| Server-side revocation| Yes -- refresh_tokens table, revoked flag  |

**Token flow**:

```
Login:
  Client --> POST /auth/login (email, password)
  Server --> Verify bcrypt hash
  Server --> Issue access_token (JSON body) + refresh_token (Set-Cookie)
  Client --> Store access_token in memory (React state/context)

API Request:
  Client --> GET /puzzles/random, Authorization: Bearer <access_token>
  Server --> Validate JWT signature + expiry
  Server --> Process request

Token Refresh (when access_token expires):
  Client --> POST /auth/refresh (cookie sent automatically)
  Server --> Validate refresh_token from cookie against DB
  Server --> Revoke old refresh_token, issue new pair
  Client --> Store new access_token in memory

Logout:
  Client --> POST /auth/logout
  Server --> Revoke refresh_token in DB
  Server --> Clear cookie (Set-Cookie: Max-Age=0)
  Client --> Clear access_token from memory
```

## Alternatives Considered

### Alternative 1: Server-Side Sessions (Express-session pattern)

**How it works**: Session ID stored in cookie, session data in server-side store (Redis or PostgreSQL).

**Pros**:
- Simpler mental model -- server controls all session state
- Instant session invalidation (delete from store)
- No JWT-specific security pitfalls (algorithm confusion, token size)

**Cons**:
- Requires a session store (Redis or DB table) -- additional infrastructure for a solo dev
- Not naturally stateless -- horizontal scaling requires shared session store
- Does not transfer to Flutter mobile client without modification (mobile apps do not natively handle browser cookies/sessions the same way)
- FastAPI has less built-in session support compared to Express/Django

**Why rejected**: Adds infrastructure dependency (Redis for sessions) that is not justified at MVP scale. Does not cleanly support the v2 Flutter client without a separate auth mechanism.

### Alternative 2: OAuth2 / Social Login (Google, GitHub)

**How it works**: Delegate authentication to an identity provider. User signs in with their Google/GitHub account.

**Pros**:
- No password storage -- eliminates bcrypt, password reset, and credential stuffing concerns
- Lower friction for users who already have Google/GitHub accounts
- Well-supported by libraries (NextAuth.js, python-social-auth)

**Cons**:
- Adds third-party dependency for a core flow -- if Google OAuth is down, users cannot log in
- Configuration complexity: OAuth client IDs, redirect URIs, consent screens for each provider
- Not all chess players have or want to use Google/GitHub for a puzzle site
- Still need a local user record and progress association
- Significantly more implementation surface area for a solo developer on a 4-6 week timeline

**Why rejected**: Over-engineered for MVP. Adds third-party dependency and configuration complexity without clear user demand. Can be added as an optional sign-in method in v2 alongside email/password.

### Alternative 3: Magic Links (Passwordless Email)

**How it works**: User enters email, receives a login link, clicks it to authenticate. No password needed.

**Pros**:
- No password storage at all -- eliminates entire password security surface
- Simple UX -- just enter your email
- Growing user acceptance of this pattern

**Cons**:
- Requires email sending infrastructure (SMTP or SendGrid) -- additional service dependency
- Login flow has latency (wait for email delivery, which can take seconds to minutes)
- Poor UX for frequent logins (check email every time)
- Email deliverability issues (spam filters) can lock users out
- Not suitable for mobile client (v2) where deep linking adds complexity

**Why rejected**: Email infrastructure dependency is not justified for MVP. The latency and deliverability risks make this unsuitable as the only auth method for a daily-use puzzle app where users may log in frequently.

## Consequences

### Positive

- **Stateless verification**: Access tokens can be validated without a database query on every request (only need DB for refresh)
- **Mobile-ready**: The same JWT-issuing backend serves both web (cookie for refresh, Bearer header for access) and mobile (store refresh token in secure device storage) without code changes
- **No session infrastructure**: No Redis or session table needed for request authentication
- **Standard pattern**: Well-documented in FastAPI ecosystem; reference implementations available
- **Graceful degradation**: Guest users (no token) work identically to the authenticated flow minus progress saving

### Negative

- **Token refresh complexity**: The frontend must handle 401 responses by transparently refreshing the token and retrying the request. This adds client-side complexity in the ApiClient layer.
- **CSRF considerations**: The refresh token is sent as a cookie, which means CSRF protection is needed. Mitigated by: SameSite=Lax (blocks cross-origin POST from external sites), scoping the cookie path to `/api/v1/auth` (not sent on puzzle/progress endpoints), and the refresh endpoint only accepts POST.
- **Access token in memory is lost on page reload**: The user must re-acquire an access token via the refresh endpoint on every page load. This is a trade-off for security (no localStorage exposure to XSS).
- **Cannot instantly revoke access tokens**: If a user's account is compromised, existing access tokens remain valid for up to 15 minutes. The 15-minute TTL limits the exposure window. Refresh tokens can be revoked immediately.

## Compliance Requirements

| Requirement                     | Implementation                              |
|---------------------------------|---------------------------------------------|
| Password hashing                | bcrypt, cost factor >= 12                   |
| No plaintext secrets in code    | JWT_SECRET_KEY via environment variable only |
| Rate limiting on auth endpoints | 10 req/min login, 5 req/min register per IP |
| Token algorithm validation      | Explicitly set and validate `alg: HS256` -- reject `alg: none` |
| Refresh token rotation          | New token on each refresh; old token revoked|
| GDPR account deletion           | CASCADE delete on users removes refresh_tokens |
| Audit logging                   | Log all auth events (login, register, logout, failed attempts) with user_id, IP, timestamp |

---

## Version History

| Version | Date       | Change                     |
|---------|------------|----------------------------|
| 1.0     | 2026-02-27 | Initial decision -- accepted |
