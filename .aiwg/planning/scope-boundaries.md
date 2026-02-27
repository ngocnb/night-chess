# Night Chess — Scope Boundaries (v1)

**Document Type**: Scope Boundaries
**Status**: Active — Enforced
**Created**: 2026-02-27
**Author**: Product Strategist
**Profile**: Solo Developer, 4-6 Week MVP

---

## Purpose

This document is the scope contract for Night Chess v1. It exists to prevent scope creep and to
give the solo developer a single authoritative reference when evaluating new ideas mid-sprint.
Every feature request — including good ones — must be measured against this document before
being acted on.

The rule is simple: if it is not in the IN SCOPE table below, it does not get built in v1.
Ideas go to BACKLOG.md, not into the current sprint.

---

## IN SCOPE (v1 — 4-6 weeks)

These features constitute the complete v1 deliverable. Nothing more, nothing less.

| Feature | Priority | Sprint Target | Acceptance Criteria |
|---------|----------|---------------|---------------------|
| Lichess data import pipeline | Must Have | Sprint 0 | 3.5M puzzles imported via PostgreSQL COPY; schema validated at import time; test with 10k subset before full run; import completes within 24h of first deploy |
| Random puzzle API | Must Have | Sprint 1 | `GET /api/v1/puzzles/random` returns valid FEN + moves; p95 latency < 300ms; response schema stable for Flutter v2 reuse |
| Interactive chessboard (react-chessboard + chess.js) | Must Have | Sprint 1 | All special moves work correctly (castling, en passant, pawn promotion); illegal moves rejected; puzzle completion detected accurately |
| Guest puzzle solving flow | Must Have | Sprint 1 | Any visitor can load and attempt a puzzle with no account, no redirect, no modal; works end-to-end in browser with no auth token present |
| Puzzle difficulty display | Must Have | Sprint 1 | Lichess rating shown alongside each puzzle position |
| User registration and login | Must Have | Sprint 2 | Email + password registration; JWT access token + refresh token issued; bcrypt password hashing (cost factor >= 12); p95 auth latency < 200ms |
| Progress tracking — save results | Must Have | Sprint 2 | Authenticated user's solve/fail result saved to database per puzzle attempt; data scoped to user only |
| Progress dashboard — solve history | Should Have | Sprint 3 | Authenticated user can view their solve history (puzzle ID, outcome, timestamp); basic stats (total solved, solve rate) |
| Account deletion (GDPR) | Should Have | Sprint 3 | `DELETE /api/v1/users/me` removes all user account data and progress records; endpoint is authenticated |
| Basic privacy policy page | Should Have | Sprint 3 | Static page at `/privacy`; covers data collected (email, progress), retention, and deletion rights |

**Sprint 0 Gate**: The data pipeline acceptance criteria must be met before Sprint 1 begins.
If the pipeline prototype fails with the 10k subset, Sprint 1 is blocked — reassess before
proceeding.

**Launch Gate**: The interactive chessboard must pass a manual test of 100+ real Lichess puzzles
covering promotions, en passant, castling, and checkmate patterns before any public access is
enabled. A chess correctness bug is a launch blocker, not a post-launch fix.

---

## OUT OF SCOPE (v1 — explicitly excluded)

These features are not eligible for v1 development under any circumstances. If a feature from this
list is proposed during a sprint, it must be declined and added to BACKLOG.md.

| Feature | Reason Excluded | When to Revisit |
|---------|-----------------|-----------------|
| Flutter mobile app (Android + iOS) | V2 milestone; FastAPI API designed for mobile reuse from day one but mobile client is out of v1 scope | After v1 launch + user engagement validation (target: Month 3) |
| Puzzle filtering by theme, rating range, or opening | Scope creep risk; random puzzle serving validates the core loop without filtering | Post-MVP, if session depth > 5 puzzles/visit suggests users want curation |
| Spaced repetition or adaptive training algorithms | Significant algorithm complexity; not part of core value proposition for v1 | Post-MVP if registered users exceed 200 and express repetition preference |
| Social features (leaderboards, friend challenges, sharing) | Scope creep; increases surface area without validating the solo practice core loop | Post-MVP; revisit only after core loop is validated |
| Gamification (streaks, badges, XP, achievements) | Engagement mechanics are secondary to getting the puzzle experience right | Post-MVP if session return rate signals users need motivation hooks |
| Custom puzzle creation or uploads | Not in product vision; would require moderation and validation logic | Never for v1; only if clear external demand emerges post-launch |
| Puzzle hints, commentary, or explanations | Content complexity and editorial effort not justified for MVP | Post-MVP if users explicitly request it |
| Admin panel or backoffice UI | Solo developer does not need a UI for admin tasks; psql and direct API calls are sufficient | Post-MVP if team grows or moderation needs emerge |
| OAuth or social login (Google, GitHub, Discord) | JWT email/password authentication is sufficient for MVP; OAuth adds complexity without user-facing value at this scale | Post-MVP if registration conversion is low and OAuth would reduce friction |
| Email notifications (verification, reminders, marketing) | Not required for MVP; email verification can be skipped at launch (revisit before EU marketing) | Add email verification before any EU marketing campaign |
| Redis caching layer | Not needed at MVP scale (<50 concurrent users); add only when PostgreSQL random selection becomes a measured bottleneck | Add when p95 puzzle load latency exceeds 300ms under real load |
| Internationalization (i18n / l10n) | English-only is sufficient for MVP launch | Only if non-English adoption reaches >20% of registered users |
| E2E tests (Playwright or Cypress) | Unit and integration tests cover critical paths; E2E setup time is not justified for MVP timeline | Post-MVP for regression safety before Flutter v2 launch |
| Payment processing or premium tiers | Not in product vision; Night Chess is free, no premium tier | Never for v1 |
| Puzzle rating adjustment or Elo system | The Lichess rating on each puzzle is sufficient; a user Elo system requires significant design | Post-MVP if user demand is clear |
| Periodic Lichess database sync | One-time bulk import is sufficient for v1; the dataset is large and stable | Post-MVP; reassess at 6 months if Lichess releases significant new puzzle batches |

---

## Scope Change Rules

These four rules govern scope changes for the duration of v1 development. They exist because
solo developers on aggressive timelines are the most vulnerable to scope creep — a good idea
at the wrong moment is a project-killing distraction.

### Rule 1 — No additions without removals

No feature may be added to the IN SCOPE table without removing a feature of equivalent or greater
complexity. Adding to scope without removing from scope is not permitted. If a new Must Have is
identified, a current Should Have must be cut or deferred.

### Rule 2 — Five-day ceiling on individual features

If a feature is taking more than 5 working days, it is either more complex than understood or
the design needs rethinking. Stop. Diagnose whether to simplify, split, or cut. Do not continue
adding complexity to a feature that is already over budget. The recovery action is:
STOP > SIMPLIFY > REDESIGN > PROCEED or CUT.

### Rule 3 — Cut scope, not quality

If the 4-6 week timeline is under pressure, the response is to cut features from the Should Have
tier — not to skip tests, weaken acceptance criteria, or bypass the Sprint 0 gate. A smaller
product that works correctly is better than a larger product with chess bugs or auth vulnerabilities.

The following are non-negotiable regardless of timeline pressure:
- Chess move validation correctness (chess.js only, no shortcuts)
- Password hashing with bcrypt at cost factor >= 12
- The Sprint 0 data pipeline gate
- The pre-launch chessboard correctness test (100+ real Lichess puzzles)

### Rule 4 — Ideas go to BACKLOG.md, not the sprint

Any feature idea that arises during v1 development — regardless of how compelling it is — goes
to `/home/baongoc/workspaces/night-chess/.aiwg/planning/BACKLOG.md`. It does not enter the
current sprint. The backlog is a holding area for v2 and beyond, not a queue that feeds v1.

---

## Scope Integrity Check

Use this checklist at the start of each sprint to verify scope has not drifted:

- [ ] No new features have been added to the IN SCOPE table without a corresponding removal
- [ ] No OUT OF SCOPE feature has been partially implemented under a different name
- [ ] The Sprint 0 data pipeline gate has been met (or Sprint 1 has not started)
- [ ] All active work traces to a Must Have or Should Have in the IN SCOPE table
- [ ] Any new ideas from the past sprint are captured in BACKLOG.md, not in the sprint board

---

## Related Documents

| Document | Path | Relationship |
|----------|------|-------------|
| Vision Document | `/home/baongoc/workspaces/night-chess/.aiwg/requirements/vision-document.md` | Source of scope decisions; KPIs and success metrics |
| Business Case | `/home/baongoc/workspaces/night-chess/.aiwg/management/business-case.md` | Justification for scope decisions; ROI context |
| Project Intake | `/home/baongoc/workspaces/night-chess/.aiwg/intake/project-intake.md` | Original feature list and risk register |
| Option Matrix | `/home/baongoc/workspaces/night-chess/.aiwg/intake/option-matrix.md` | Architecture decisions informing scope choices |
| Backlog | `/home/baongoc/workspaces/night-chess/.aiwg/planning/BACKLOG.md` | Post-MVP ideas; v2 candidates |

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-02-27 | Initial scope boundaries — established from intake, vision document, and option matrix |
