# Night Chess — Backlog

Ideas that surfaced during planning but are explicitly out of scope for v1.
When a new idea comes up mid-sprint, write it here — do not open a branch for it.

**Rule**: Nothing moves from here into the current sprint without removing another item.

---

## V2 — Mobile

| Idea | Notes |
|------|-------|
| Flutter Android app | Reuses FastAPI backend unchanged; needs `/api/v1/` endpoints to stay stable |
| Flutter iOS app | Same Flutter codebase as Android |
| Mobile-specific UX | Larger touch targets for piece moves; swipe for next puzzle |
| Deep links | Open a specific puzzle from a share URL on mobile |

---

## Puzzle Experience

| Idea | Notes |
|------|-------|
| Filter by theme | e.g. mateIn1, fork, pin, skewer — Lichess `themes` column is already imported |
| Filter by rating range | Already in API design as optional query params; just needs frontend UI |
| Spaced repetition | Surface puzzles the user previously failed; requires tracking failure timestamps |
| Streak tracking | Daily puzzle streak counter; needs a `last_active_date` field on users |
| Puzzle hints | Reveal first move of solution after user requests it |
| Puzzle explanation | Text explanation of why the solution works — requires content generation or Lichess API |
| Bookmark puzzles | Save a puzzle to review later; needs a `bookmarks` table |
| Retry failed puzzles | Dedicated "retry" queue from user_progress where result = 'failed' |
| Opening explorer | Show the opening name if `opening_tags` is populated on the puzzle |
| Puzzle of the day | Fixed daily puzzle, same for all users; share link |

---

## User Account

| Idea | Notes |
|------|-------|
| Email verification | Confirm email on registration; requires SMTP/SendGrid setup |
| Password reset | Forgot password flow; requires email sending |
| Email change | Allow users to update their email address |
| Data export (GDPR portability) | Download all progress as CSV/JSON; deferred from v1 PIA |
| Username / display name | Optional display name separate from email |
| OAuth / social login | Google or GitHub sign-in as an alternative to email+password |
| Avatar / profile picture | Low priority; purely cosmetic |

---

## Progress & Stats

| Idea | Notes |
|------|-------|
| Rating graph | Plot user's average puzzle rating over time |
| Accuracy by theme | Show solve rate broken down by puzzle theme |
| Solve time analysis | Average time per puzzle, trend over sessions |
| Weekly/monthly reports | Email summary of puzzle activity (requires email setup) |
| Leaderboard | Global or friends-based ranking by puzzles solved or accuracy |

---

## Social & Community

| Idea | Notes |
|------|-------|
| Share a puzzle | Generate a share URL for a specific puzzle |
| Challenge a friend | Send a specific puzzle to another user |
| Public profile | Opt-in shareable progress page |
| Comments on puzzles | Community discussion on a puzzle — significant moderation surface |

---

## Performance & Infrastructure

| Idea | Notes |
|------|-------|
| Redis puzzle cache | Pre-generate random puzzle ID batches; add when p95 exceeds 300ms under real load |
| CDN for static assets | Cloudflare free tier in front of nginx for Next.js static files |
| pgBouncer | Connection pooling; add when PostgreSQL connection count becomes a bottleneck |
| Multi-server deploy | Add a second server + load balancer if single server CPU/RAM is saturated |
| Periodic Lichess DB sync | Re-import updated puzzle database when Lichess releases a new dump |
| Read replica | Separate read replica for progress queries; add at >10k active users |

---

## Compliance & Security

| Idea | Notes |
|------|-------|
| Full GDPR compliance | Data portability, rectification endpoints — add before EU marketing campaign |
| CCPA compliance | If California user base grows significantly |
| SOC2 | Only if enterprise or institutional partnerships develop |
| Penetration testing | Schedule before any significant scale or public promotion |
| Admin panel | Puzzle management, user management — needed if moderation becomes necessary |

---

## Developer Experience

| Idea | Notes |
|------|-------|
| OpenAPI client generation | Auto-generate TypeScript client from FastAPI OpenAPI spec for Flutter v2 |
| End-to-end tests | Playwright suite for critical user flows; add at Production profile |
| Load testing | k6 scripts for puzzle fetch and auth endpoints; run before any public promotion |
| Staging environment | Second Docker Compose stack on same or separate server for pre-prod testing |

---

*Last updated: 2026-02-27*
*Owner: Developer*
