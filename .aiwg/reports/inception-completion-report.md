# Inception Phase Completion Report — Night Chess

**Document Type**: Phase Completion Report
**Project**: Night Chess — Chess Puzzle Platform
**Phase Completed**: Inception
**Date**: 2026-02-27
**Author**: Project Manager
**Profile**: Solo Developer, 4-6 Week MVP

---

## 1. Milestone Achievement Summary

All 17 Inception artifacts were produced and validated. The Lifecycle Objective Milestone is met.

| Artifact | Path | Status | Quality Signal |
|----------|------|--------|----------------|
| Vision Document | requirements/vision-document.md | Complete | 10 sections; 7 KPIs with measurement methods |
| Business Case | management/business-case.md | Complete | ROM $97-$192/yr; GO with 3 named conditions |
| Risk List | risks/risk-list.md | Complete | 10 risks; R-001 CRITICAL with 5-step mitigation |
| UC-001 Solve Random Puzzle | requirements/use-case-briefs/UC-001-solve-random-puzzle.md | Complete | 7 success criteria; 3 alternative flows |
| UC-002 Register and Track Progress | requirements/use-case-briefs/UC-002-register-track-progress.md | Complete | 8 success criteria; 4 alternative flows |
| UC-003 Import Puzzle Database | requirements/use-case-briefs/UC-003-import-puzzle-database.md | Complete | 8 success criteria; 4 alternative flows |
| UC-004 Render Interactive Chessboard | requirements/use-case-briefs/UC-004-render-chessboard.md | Complete | 11 success criteria; 4 alternative flows |
| Data Classification | security/data-classification.md | Complete | 9 data types; 4 classification levels with controls |
| Privacy Impact Assessment | security/privacy-impact-assessment.md | Complete | GDPR rights table; cookie policy; action items |
| Architecture Sketch | architecture/architecture-sketch.md | Complete | Full schema SQL; 3 sequence diagrams; 2 deployment options |
| ADR-001 Authentication | architecture/adr/ADR-001-authentication-approach.md | Accepted | 3 alternatives evaluated; token flow documented |
| ADR-002 Chess Rendering Library | architecture/adr/ADR-002-chess-rendering-library.md | Accepted | 3 alternatives evaluated; critical constraint documented |
| ADR-003 Random Puzzle Selection | architecture/adr/ADR-003-random-puzzle-selection.md | Proposed | Sprint 0 validation plan defined; benchmarks queued |
| Scope Boundaries | planning/scope-boundaries.md | Complete | 10 in-scope features; 13 out-of-scope; 4 governance rules |
| Project Intake | intake/project-intake.md | Complete | Full greenfield intake with architecture and risk |
| Solution Profile | intake/solution-profile.md | Complete | MVP profile; coverage overrides; improvement roadmap |
| Option Matrix | intake/option-matrix.md | Complete | 3 options scored; Option A recommended at 4.00/5.00 |

**Artifact completion rate: 17/17 (100%)**

---

## 2. Key Decisions Made

### Decision 1 — Architecture: Separate FastAPI + Next.js (Option Matrix)

**Decision**: Option A — FastAPI backend + Next.js frontend as two separately deployed services,
sharing a managed PostgreSQL database.

**Score**: 4.00/5.00 (vs Option B at 3.90, Option C at 3.10)

**Why it matters**: This decision locks in Flutter v2 compatibility from day one. The FastAPI
backend exposes versioned endpoints (`/api/v1/`) with clean OpenAPI schemas that the mobile
client can consume without backend changes. Choosing Option B (full-stack Next.js) would have
required a rewrite before v2 could start.

**Deployment**: Render (FastAPI + PostgreSQL) + Vercel (Next.js). Total monthly cost $1-$15
at MVP scale.

---

### Decision 2 — Authentication: JWT + HttpOnly Cookies (ADR-001)

**Decision**: JWT access tokens (15-minute TTL, stored in memory) combined with refresh tokens
(7-day TTL, stored in HttpOnly/Secure/SameSite=Lax cookie). bcrypt at cost factor 12 for
passwords. Server-side refresh token revocation via `refresh_tokens` table.

**Why it matters**: This eliminates localStorage exposure (XSS risk), provides transparent
token refresh without user friction, enables instant refresh token revocation on logout, and
is designed for Flutter mobile reuse from the start (mobile clients store the refresh token
in secure device storage, not a browser cookie).

**Alternatives rejected**: Server-side sessions (adds Redis dependency), OAuth (over-engineered
for MVP), Magic links (email infrastructure dependency + latency).

---

### Decision 3 — Chess Rendering: react-chessboard + chess.js (ADR-002)

**Decision**: react-chessboard (SVG board, React-native, 100K weekly downloads) for rendering;
chess.js (complete chess rules implementation, 1M+ weekly downloads) for all move validation.
Zero custom chess logic anywhere in the codebase — non-negotiable architectural constraint.

**Why it matters**: Chess correctness is the CRITICAL risk (R-001) and the make-or-break quality
dimension. chess.js has been exercised against millions of real games. Using it exclusively
eliminates the largest category of product-killing bugs. This constraint is documented in both
ADR-002 and the risk register and must be enforced in code review.

**Alternatives rejected**: chessground (React integration friction), cm-chessboard (smaller
community, less mature), custom SVG renderer (weeks of work, not justified for a puzzle platform).

---

### Decision 4 — Random Puzzle Selection: TABLESAMPLE + Fallback (ADR-003, Proposed)

**Decision (pending Sprint 0 validation)**: Use PostgreSQL `TABLESAMPLE SYSTEM(0.01)` as the
primary random selection mechanism. `ORDER BY RANDOM()` on 3.5M rows is O(n) and estimated at
500ms-2s per query, which violates the p95 < 300ms target. TABLESAMPLE operates at the page
level, avoiding full table scan. Fallback uses a cached row count with random OFFSET.

**Why it matters**: Every guest page load and every "Next Puzzle" click hits this query. If
it is slow, the core experience is degraded before any other code runs. This must be benchmarked
in Sprint 0 — not assumed to be fast enough.

**Sprint 0 action**: Run benchmarks documented in ADR-003 Section "Validation Plan" against the
full 3.5M row local dataset. Update ADR-003 status to Accepted or Superseded.

---

### Decision 5 — Profile Selection: MVP (Solution Profile)

**Decision**: MVP profile with targeted overrides — test coverage raised from the standard 30%
floor to 50% overall and 80% on critical paths (auth, data pipeline, puzzle fetch, progress API).

**Why it matters**: The standard MVP floor (30%) is insufficient given that the auth system
handles PII and the data pipeline handles 3.5M rows of puzzle data. The override is documented
with rationale, preventing the coverage target from being silently reduced later.

---

## 3. Risk Summary

### Critical Risk

| ID | Title | Score | Mitigation Status |
|----|-------|-------|-------------------|
| R-001 | Chess Move Validation Correctness | CRITICAL | Mitigated — chess.js mandated, ADR-002 accepted, CI gate required, 100+ puzzle manual test pre-launch |

R-001 is the only Show Stopper in the register. Its mitigation is the most detailed in the
corpus: 5 numbered steps, CI blocking gate, manual play-through requirement, and a launch
blocker policy. This risk must be treated as a first-class constraint throughout construction.

### High Risks

| ID | Title | Score | Key Mitigation |
|----|-------|-------|----------------|
| R-002 | Lichess Data Pipeline Reliability | HIGH | Prototype in Sprint 0 — Sprint 1 is blocked until 10k subset import succeeds |
| R-003 | Solo Developer Bottleneck + Timeline | HIGH | Scope locked by scope-boundaries.md; 5-day feature ceiling; weekly self-check cadence |

R-002 and R-003 are coupled: if the pipeline prototype fails and consumes Sprint 0 entirely,
Sprint 1 must not start. The Sprint 0 gate enforces this explicitly.

### Medium Risks (Monitor)

| ID | Title | Score | Key Mitigation |
|----|-------|-------|----------------|
| R-004 | Framework Learning Curve | MEDIUM | Weeks 1-2 budgeted for ramp-up; prototype patterns before production code |
| R-005 | Random Puzzle Query Performance | MEDIUM | ADR-003 TABLESAMPLE approach; Sprint 0 benchmark validation |
| R-006 | JWT Auth Implementation Security | MEDIUM | ADR-001 compliance table; follow single reference implementation |

### Low Risks (Review Schedule)

R-007 through R-010 are LOW. Monitor at weekly self-check; escalate if any trigger indicator fires.

**Risk register next review**: End of week 2 (approximately 2026-03-13) or when any trigger
indicator fires, whichever comes first.

---

## 4. Financial Summary

All figures from business-case.md Section 4.

### Monthly Infrastructure (Steady State)

| Service | Tier | Cost |
|---------|------|------|
| Vercel (Next.js frontend) | Hobby (free) | $0 |
| Render (FastAPI backend) | Free or Starter | $0 - $7 |
| Render PostgreSQL | Free (90-day) then Starter | $0 - $7 |
| Sentry (error tracking) | Free | $0 |
| Domain (amortized) | ~$12/year | ~$1 |
| **Monthly total** | | **$1 - $15** |

### First-Year Projection

| Period | Cost |
|--------|------|
| Months 1-3 (free tiers cover most) | ~$15 - $45 |
| Months 4-12 (Render Starter if limits hit) | ~$70 - $135 |
| Domain registration | $12 |
| **First-year total** | **~$97 - $192** |

**Accuracy**: ROM, +/-50%

**Critical budget note**: The Render free PostgreSQL tier has a 90-day limit. Before day 90,
plan and execute the migration to Render Starter ($7/month). Do not let this expire without a
plan — losing database access would require emergency migration under pressure.

**Budget guardrail**: If monthly infrastructure exceeds $20, stop and review tier choices
before upgrading. Do not absorb cost increases silently.

---

## 5. Sprint Plan Recommendation

This plan is calibrated for a solo developer working full-time on a 4-6 week timeline.
The order is intentional: highest-risk items first, scope cuts come from the end.

---

### Sprint 0 — Foundation and Risk Validation (Days 1-3)

**Goal**: Validate the two highest-risk items before writing any feature code. If either fails,
the timeline must be reassessed before Sprint 1 begins.

**Gate**: Sprint 1 does not start until both Sprint 0 deliverables are confirmed.

**Deliverables**:

1. **Lichess data pipeline prototype** (2 days)
   - Set up local Docker PostgreSQL
   - Download `lichess_db_puzzle.csv.zst` from database.lichess.org
   - Write import script: decompress, validate CSV header, insert 10,000 row subset via COPY
   - Confirm row count, spot-check 5 puzzles against lichess.org/training
   - If subset succeeds: run full 3.5M row import overnight
   - Record result in Sprint 0 validation log; update ADR-003 status

2. **Dev environment setup** (1 day, parallel with pipeline if possible)
   - Initialize FastAPI project (`pyproject.toml`, virtual env, FastAPI, SQLAlchemy, Alembic)
   - Initialize Next.js project (`package.json`, TypeScript, eslint, tailwind if desired)
   - GitHub Actions CI: lint + test steps (no deploy yet)
   - Docker Compose for local dev (FastAPI + PostgreSQL)
   - Run Alembic migration for the 4-table schema from architecture-sketch.md

3. **ADR-003 benchmarks** (part of day 2)
   - Run the 4 EXPLAIN ANALYZE queries from ADR-003 validation plan
   - Record results; update ADR-003 to Accepted or Superseded

**Sprint 0 exit gate**:
- [ ] 10k puzzle subset imported successfully (row count verified, 5 spot-checks passed)
- [ ] Full 3.5M import completed or in progress and on track
- [ ] Dev environment boots: FastAPI returns 200 on /health, Next.js starts, DB schema applied
- [ ] ADR-003 status updated based on benchmark results

---

### Sprint 1 — Puzzle API + Chessboard + Guest Flow (Week 1-2)

**Goal**: End of Sprint 1, a guest can visit the site, get a real puzzle from the live database,
attempt to solve it on an interactive chessboard, and click Next Puzzle. No account required.

**Must Have deliverables**:

1. **FastAPI puzzle endpoint** (2 days)
   - `GET /api/v1/puzzles/random` using TABLESAMPLE strategy from ADR-003
   - Response schema: `{id, fen, moves, rating, themes}`
   - Benchmark endpoint locally: confirm p95 < 300ms on full 3.5M row dataset
   - Unit tests: valid response schema, rating is integer, FEN is non-empty

2. **React chessboard component** (3-4 days — highest effort item in the sprint)
   - Install `react-chessboard` and `chess.js`
   - PuzzleBoard component: accepts `{fen, moves}` props, renders board, handles moves
   - chess.js validates legality; illegal moves snap back silently
   - Solution sequence checking: correct move advances puzzle, incorrect triggers feedback
   - Opponent auto-reply after correct move (500ms delay)
   - Special move handling: castling, en passant, pawn promotion modal (Q/R/B/N)
   - `onPuzzleComplete` fires exactly once when last solution move is played
   - Integration tests: manually solve 10+ real Lichess puzzles covering castling, en passant,
     promotion, checkmate — all must work correctly before this component is declared done

3. **Guest puzzle page** (1 day)
   - Next.js page at `/` and `/puzzle`
   - Fetches from `GET /api/v1/puzzles/random` on load
   - Renders PuzzleBoard with received FEN and moves
   - "Next Puzzle" button triggers new fetch
   - Error state if API unreachable: "Could not load puzzle — try again"
   - No auth token required at any point

4. **Puzzle rating display** (half day)
   - Show Lichess rating alongside puzzle position (e.g., "Rating: 1487")
   - This is a Must Have from scope-boundaries.md

**Sprint 1 exit gate**:
- [ ] GET /puzzles/random returns a valid puzzle in < 300ms p95 (measured locally)
- [ ] Chessboard renders FEN positions correctly
- [ ] Illegal moves are rejected without error messages
- [ ] At least one castling, one en passant, and one promotion puzzle solve correctly end-to-end
- [ ] Guest can load page, solve a puzzle, click Next Puzzle, and get a different puzzle
- [ ] No authentication required at any point in the guest flow

---

### Sprint 2 — Authentication + Progress Tracking (Week 3-4)

**Goal**: End of Sprint 2, a user can register, log in, solve puzzles, and have their results
saved. Token refresh works transparently. All auth security controls from ADR-001 are implemented.

**Must Have deliverables**:

1. **FastAPI auth endpoints** (2-3 days)
   - `POST /api/v1/auth/register` — email + password; bcrypt cost 12; return 201
   - `POST /api/v1/auth/login` — verify bcrypt; issue access_token (JSON) + refresh_token (cookie)
   - `POST /api/v1/auth/refresh` — validate cookie, rotate refresh token, issue new access_token
   - `POST /api/v1/auth/logout` — revoke refresh token in DB, clear cookie
   - Rate limiting: 5/min on register, 10/min on login, per IP
   - All auth events logged with user_id (not email), IP, timestamp
   - Integration tests: happy path + duplicate email + wrong password + expired token
   - Test coverage >= 80% on auth module

2. **FastAPI progress endpoints** (1-2 days)
   - `POST /api/v1/puzzles/{id}/submit` — authenticated users save result; guests get {saved: false}
   - `GET /api/v1/users/me/progress` — paginated solve history, authenticated only
   - `GET /api/v1/users/me` — profile + aggregate stats
   - Authorization enforced: user can only read their own progress (no IDOR)
   - Test coverage >= 80% on progress module

3. **Next.js auth UI** (1-2 days)
   - `/register` page: email + password form; client-side validation; duplicate email error
   - `/login` page: credentials form; generic error message on failure
   - AuthProvider context: access token in memory; automatic refresh on 401; redirect to login
     if refresh token expired
   - API client: Bearer token on all authenticated requests; transparent refresh

4. **Progress recording integration** (1 day)
   - After each puzzle attempt (correct or give-up), call `POST /puzzles/{id}/submit`
   - Show "Saved" confirmation for authenticated users
   - Show "Sign in to save your progress" for guests

**Sprint 2 exit gate**:
- [ ] User registers with valid email and password; duplicate email returns actionable error
- [ ] Passwords stored as bcrypt hash (cost 12); never returned by any endpoint
- [ ] Login issues access token (15 min) + refresh token (7 day httpOnly cookie)
- [ ] Token refresh works transparently on 401 — user does not see a login prompt
- [ ] Each puzzle solve result is saved and associated with the correct user
- [ ] Users cannot access another user's progress (403 on cross-user request)
- [ ] Rate limiting blocks 6th login attempt within 1 minute per IP
- [ ] Auth test coverage >= 80%

---

### Sprint 3 — Dashboard + GDPR + Polish + Deploy (Week 5-6)

**Goal**: End of Sprint 3, the application is deployed, publicly accessible, and meets all
Should Have criteria from scope-boundaries.md. Launch gate passed.

**Should Have deliverables**:

1. **Progress dashboard** (1-2 days)
   - `/dashboard` page — authenticated only; redirect to /login if not
   - Display: total puzzles attempted, total solved, solve rate (%)
   - Recent puzzle list: puzzle ID, outcome (solved/failed), timestamp
   - Pagination for users with many attempts

2. **Account deletion (GDPR)** (half day)
   - `DELETE /api/v1/users/me` endpoint — authenticated
   - Triggers CASCADE delete: users, user_progress, refresh_tokens
   - Frontend: settings page at `/settings` with "Delete Account" button and confirmation dialog
   - Return 204 on success; redirect to homepage

3. **Privacy policy page** (half day)
   - Static Next.js page at `/privacy`
   - Covers: data collected, why, storage, retention, user rights (access + deletion now; portability v2)
   - No legal review required for MVP; plain language acceptable

4. **Launch gate — chessboard correctness test** (1 day)
   - Manually solve 100+ real Lichess puzzles covering all required special move types
   - At minimum: 10 castling puzzles (both sides, both colors), 10 en passant, 10 promotions
     (all four piece types), 10 multi-move sequences, 10 checkmate-in-one
   - Record results; any failure is a launch blocker — fix before proceeding

5. **Production deployment** (1-2 days)
   - Configure Render web service: Docker build, environment variables, Sentry DSN
   - Configure Render PostgreSQL: connection string, TLS, daily backups confirmed
   - Configure Vercel: Next.js deployment, environment variables for API URL
   - Run data pipeline import on production PostgreSQL (full 3.5M rows)
   - Smoke test all critical paths on production: guest flow, register, login, solve, dashboard,
     delete account

6. **Polish and monitoring** (remaining time)
   - Sentry integration verified (test error appears in Sentry dashboard)
   - Error states polished: API unavailable, invalid FEN, network timeout
   - Mobile web sanity check: chessboard usable on iOS Safari and Android Chrome
     (full mobile support is v2; confirm it is not completely broken)
   - README: setup, development, deployment instructions

**Sprint 3 exit gate**:
- [ ] 100+ real Lichess puzzles tested manually; zero chess correctness failures
- [ ] DELETE /api/v1/users/me removes account, progress, and refresh tokens
- [ ] Privacy policy page live at /privacy before any public link sharing
- [ ] Application deployed and reachable on production URL
- [ ] Sentry receives at least one test error; monitoring confirmed active
- [ ] All smoke tests pass on production

---

## 6. Go/No-Go Decision

**DECISION: GO**

### Rationale

The Inception phase has produced a cohesive, internally consistent artifact set that answers
all questions a developer needs to start coding:

- **What to build**: Vision document + use cases define the product surface precisely
- **How to build it**: Architecture sketch + ADRs eliminate all major architectural uncertainty
- **What not to build**: Scope boundaries enforce this with governance rules
- **What can go wrong**: Risk register with mitigation plans for all 10 identified risks
- **What it costs**: ROM documented; budget guardrails specified
- **Security and privacy**: Data classification + PIA + ADR-001 provide a coherent control set

The financial exposure is low enough ($97-$192 first year) that the cost of proceeding and
finding a problem is less than the cost of additional planning.

### Conditions on GO

| Condition | Deadline | Consequence if Not Met |
|-----------|----------|------------------------|
| Sprint 0 data pipeline prototype succeeds (10k subset) | Day 3 | Sprint 1 blocked; timeline must be reassessed |
| ADR-003 updated after Sprint 0 benchmarks | End of Sprint 0 | Random puzzle selection approach is unconfirmed; proceed with uncertainty |
| Launch gate: 100+ Lichess puzzle manual test | Before any public access | Public access blocked; fix chess correctness bug first |
| BACKLOG.md created | Start of Sprint 1 | Scope creep has no formal destination; ideas may enter the sprint |

---

## 7. Next Steps

Immediate actions to take before starting Sprint 0:

1. **Create BACKLOG.md** at `/home/baongoc/workspaces/night-chess/.aiwg/planning/BACKLOG.md`
   Put "v2 Flutter app" and any post-MVP ideas already in mind into it. The file needs to exist
   before Sprint 1 so there is always a ready destination for mid-sprint ideas.

2. **Set up the git repository** with the structure implied by the architecture sketch:
   - `backend/` — FastAPI application
   - `frontend/` — Next.js application
   - `backend/scripts/` — data import script
   - `.github/workflows/` — GitHub Actions CI
   - `docker-compose.yml` — local development environment

3. **Start Sprint 0** — see sprint plan above. The first command to run is:
   ```
   mkdir -p backend/scripts data
   pip install python-zstandard psycopg2-binary
   ```
   Then download the Lichess file and run the 10k subset import before writing any other code.

4. **Start Elaboration phase** alongside Sprint 0 — the SDLC framework's Elaboration phase
   produces detailed implementation specifications that can be drafted while the pipeline
   prototype runs. Key Elaboration outputs: database migration scripts, API contract tests,
   test plan for chess move validation coverage.

5. **Update the vision document Outstanding Decisions section** — mark JWT storage and hosting
   provider as Resolved (decisions made in ADR-001 and architecture sketch). Leave Next.js
   rendering strategy and email verification as Open for week 2.

---

## 8. Handoff Checklist

This is the complete list of what the developer needs to start coding today.

### Architecture Reference

- [ ] Read architecture-sketch.md Section 2.3 (database schema) — implement this exactly via Alembic
- [ ] Read ADR-001 (auth) — follow the token flow diagram; do not improvise JWT implementation
- [ ] Read ADR-002 (chess rendering) — chess.js only; zero custom chess logic; bookmark the constraint
- [ ] Read ADR-003 (random selection) — run the Sprint 0 benchmarks before choosing the final approach

### Environment

- [ ] Python 3.11+ installed
- [ ] Node.js 20.x installed
- [ ] Docker Desktop running
- [ ] PostgreSQL accessible locally (Docker Compose)
- [ ] GitHub repository created; GitHub Actions enabled
- [ ] Sentry account created; DSN captured in `.env.example`
- [ ] Render account created; Vercel account created (can use free tiers to start)

### Sprint 0 Checklist (Do Before Anything Else)

- [ ] Download `lichess_db_puzzle.csv.zst` from https://database.lichess.org/
- [ ] Run import script with 10,000 row subset; verify row count and 5 spot-checks
- [ ] Run the 4 ADR-003 benchmark queries; record results; update ADR-003
- [ ] Run full 3.5M row import (allow 4-10 hours); verify final count
- [ ] Dev environment up: FastAPI returns 200, Next.js starts, schema applied via Alembic
- [ ] Create BACKLOG.md at .aiwg/planning/BACKLOG.md

### Non-Negotiable Quality Gates (Print and Post)

These four constraints cannot be traded for timeline under any circumstances:

1. Chess move validation: chess.js only. Zero custom chess logic.
2. Password hashing: bcrypt at cost factor >= 12. Not 10. Not the default.
3. Sprint 0 data pipeline gate: Sprint 1 does not start until 10k subset import passes.
4. Launch gate: 100+ real Lichess puzzles manually tested before any public access.

### Scope Lock

The IN SCOPE table in scope-boundaries.md is the complete v1 deliverable. When a new idea
surfaces (and it will), write it in BACKLOG.md. Do not open a new branch for it. Do not
implement it "just quickly." BACKLOG.md is where good ideas go to wait.

The weekly self-check template:
- What did I plan to finish this week?
- What did I actually finish?
- Did anything exceed the 5-day ceiling?
- Did any out-of-scope work creep in?
- What is the explicit priority for next week?

---

*Phase: Inception — COMPLETE*
*Next phase: Elaboration*
*Milestone: Lifecycle Architecture Milestone (LAM) — target end of Sprint 1*
