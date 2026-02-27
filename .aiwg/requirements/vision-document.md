# Night Chess — Vision Document

**Document Type**: Vision Document
**Status**: Active
**Created**: 2026-02-27
**Author**: Vision Owner
**Profile**: MVP (Solo Developer, 4-6 weeks)

---

## 1. Vision Statement

Night Chess is a distraction-free chess puzzle platform that gives players instant access to high-quality puzzles — no account required, no clutter. For players who want more, a lightweight account system lets them track progress and measure improvement over time. The platform proves that a focused single-purpose tool beats a bloated all-in-one product for daily puzzle practice.

---

## 2. Problem Statement

Chess enthusiasts who want daily puzzle practice are forced to use feature-heavy platforms (Lichess, Chess.com) that bury puzzles inside dashboards, social feeds, and upsell flows. The friction is real: account walls before your first puzzle, notifications, ads, and interfaces optimized for retention rather than focused practice.

The Lichess puzzle database — 3.5 million high-quality, community-rated puzzles — is openly available under a permissive license. No dedicated platform exploits this to deliver a clean, zero-friction puzzle experience. Night Chess fills that gap.

**What's broken today:**
- Guest users cannot solve a single puzzle on most platforms without creating an account
- Puzzle-focused practice is buried inside general chess products not designed for it
- The best freely available puzzle dataset (Lichess) has no dedicated standalone app

---

## 3. Target Personas

### Persona 1 — Guest Puzzle Solver ("Just give me a puzzle")

**Who**: Casual to intermediate chess player. Opens a browser tab during a break. Has no patience for onboarding.

**Goal**: Solve a puzzle right now without signing up or clicking through anything.

**Pain points**: Account walls, email verification before first interaction, platform noise.

**What Night Chess gives them**: A chessboard with a puzzle, immediately. No account. No friction. They can close the tab and come back tomorrow.

**Success signal**: They solve 3+ puzzles per visit. They return without having registered.

### Persona 2 — Registered Practitioner ("I want to see my progress")

**Who**: Dedicated player doing daily puzzle work to improve their rating. Practices consistently and wants data to validate effort.

**Goal**: Track which puzzles they've solved, see their solve rate, and know their practice streak is being recorded.

**Pain points**: Starting over every session, not knowing if they're improving, solving the same puzzle twice.

**What Night Chess gives them**: A lightweight account with a solve history dashboard. Persistent progress without the overhead of a full chess platform account.

**Success signal**: They return daily. Their solve history grows. They refer others.

---

## 4. Success Metrics

| KPI | Target | Timeframe | Measurement |
|-----|--------|-----------|-------------|
| Puzzle solves (guest + auth) | 500 total solves | Month 1 post-launch | Database count |
| Registered users | 50 accounts | Month 2 post-launch | User table count |
| Session depth | avg 3+ puzzles per visit | Ongoing | Session analytics |
| Puzzle load latency | p95 < 300ms | From day 1 | Server-side timing logs |
| API response time (auth endpoints) | p95 < 200ms | From day 1 | Server-side timing logs |
| Availability | 99% uptime | Ongoing | Uptime monitor |
| Data pipeline readiness | Full DB imported and queryable | Within 24h of first deploy | Manual verification |

**North Star**: A returning guest who registers because they want to save progress — that conversion signals the core loop is working.

---

## 5. Core Value Proposition

**Night Chess vs. Lichess**: Lichess is a full chess platform. Puzzles are one tab among many. Night Chess does one thing. The entire product surface is the puzzle experience.

**Night Chess vs. Chess.com**: Chess.com is freemium and ad-supported. The free puzzle experience is gated and interrupt-driven. Night Chess has no ads, no upsells, no premium tier blocking features.

**The unique position**: Free, open data (Lichess CC0 puzzles) + single-purpose UX + zero friction for guests. No platform in this niche combines all three.

**If we do this right**: Night Chess is the answer to "I just want to do some puzzles" — a URL someone bookmarks and returns to daily without friction.

---

## 6. Scope

### In-Scope for v1

- **Random puzzle serving**: Any visitor gets a puzzle immediately, no account required
- **Puzzle rendering**: Interactive chessboard with FEN display, legal move enforcement, and puzzle completion detection
- **Move validation**: Client-side chess logic (chess.js) ensuring only legal moves are accepted; puzzle solution checking
- **Lichess data pipeline**: One-time import of the Lichess `.zst` compressed CSV (~3.5M puzzles) into PostgreSQL
- **Puzzle difficulty display**: Show Lichess rating alongside each puzzle
- **User authentication**: Email + password registration and login; JWT access + refresh tokens
- **Progress tracking**: Authenticated users see their solve history (solved/failed per puzzle, timestamp)
- **Basic progress dashboard**: List of solved puzzles with outcome and date

### Explicitly Out-of-Scope for v1

- Mobile app (Flutter/Android/iOS) — v2
- Puzzle filtering by theme, rating range, or opening — post-MVP
- Spaced repetition or adaptive training algorithms — post-MVP
- Social features: leaderboards, friend challenges, sharing — post-MVP
- Puzzle commentary, hints, or explanations — post-MVP
- Custom puzzle creation or uploads — never (scope creep)
- Gamification: streaks, badges, XP — post-MVP
- Redis caching layer — add only if performance degrades under real load
- E2E tests (Playwright) — post-MVP
- Payment processing — not in product vision

---

## 7. Constraints

| Constraint | Detail |
|------------|--------|
| Team size | Solo developer — every architectural decision must account for single-person maintenance |
| Timeline | 4-6 weeks to working MVP — aggressive; scope must be protected |
| Framework experience | Strong developer fundamentals; new to FastAPI and Next.js specifically — budget ramp-up time in weeks 1-2 |
| GDPR | Awareness-level only for MVP; account deletion endpoint required before any EU marketing campaign |
| Budget | Not specified; target low-cost managed services (Render or AWS free tier) |
| Test coverage | 50% overall minimum; 80%+ on auth + data pipeline (non-negotiable given PII handling) |

**Key constraint implication**: The solo developer constraint means features must be cut ruthlessly before timeline is cut. The scope above is the minimum; it cannot grow without pushing timeline.

---

## 8. Key Assumptions

1. **Lichess data is stable**: The puzzle CSV schema at https://database.lichess.org/ does not change significantly during v1 development. If it does, the import script requires rework before launch.

2. **chess.js is sufficient**: The `chess.js` library correctly handles FEN parsing, legal move generation, and game state for all puzzle positions in the Lichess dataset. Edge cases (unusual promotions, en passant puzzles) are handled correctly by the library without custom logic.

3. **React-chessboard integrates cleanly with chess.js**: The `react-chessboard` + `chess.js` combination is the established standard for React chess UIs; integration friction is low.

4. **Guest traffic dominates**: Most users will be guests. Registered users are the minority in v1. This means the unauthenticated puzzle flow is the critical path, not the auth flow.

5. **PostgreSQL can handle random puzzle selection at MVP scale**: `ORDER BY RANDOM()` on a 3.5M row table is acceptable at <50 concurrent users. Redis pre-caching is not needed for MVP launch.

6. **No EU marketing at MVP launch**: GDPR account deletion endpoint can be deferred until before any targeted EU user acquisition. This assumption must be revisited before any marketing spend.

7. **Render or similar managed hosting is available**: Solo developer cannot manage raw EC2; managed deployment (Render, Railway, or Fly.io) is assumed for initial hosting.

---

## 9. Dependencies

| Dependency | Type | Risk | Notes |
|------------|------|------|-------|
| Lichess Puzzle Database | Data source | Medium | Public CC0 data at database.lichess.org; ~800 MB uncompressed; no API key required; schema change would require import rework |
| chess.js | Frontend library | Low | Mature, battle-tested chess logic library; handles FEN, move validation, game state |
| react-chessboard | Frontend library | Low | Standard React chessboard UI component; pairs with chess.js |
| FastAPI | Backend framework | Low-Medium | Stable Python framework; developer is new to it — learning curve in week 1 |
| Next.js | Frontend framework | Low-Medium | Stable React framework; developer is new to it — SSR/SSG concepts need ramp-up |
| PostgreSQL | Database | Low | Standard relational DB; well-documented; managed via Render/RDS |
| SQLAlchemy | ORM | Low | Standard Python ORM; pairs with FastAPI via databases or async SQLAlchemy |
| JWT (python-jose or PyJWT) | Auth library | Low | Standard JWT implementation for Python |
| bcrypt | Security | Low | Password hashing; cost factor ≥ 12 required |
| GitHub Actions | CI/CD | Low | Free tier sufficient for solo project |
| Sentry | Error monitoring | Low | Free tier sufficient for MVP error tracking |

---

## 10. Risks Summary

### Risk 1 — Chess UX Correctness (CRITICAL)

**What could go wrong**: The interactive chessboard accepts illegal moves, fails to detect puzzle completion, or mishandles unusual positions (promotions, en passant, castling rights from FEN). A chess bug is visible immediately to any chess player and destroys credibility.

**Likelihood**: Medium — chess.js handles most cases, but FEN edge cases exist in 3.5M puzzles.

**Impact**: High — this is the make-or-break quality dimension. Wrong chess = product failure.

**Mitigation**:
- Use chess.js exclusively for all move validation (no custom logic)
- Test the puzzle flow against a sample of 100+ real Lichess puzzles covering promotions, en passant, and checkmate patterns before launch
- Display puzzle solution validation server-side as a secondary check
- Treat any chess correctness bug as a launch blocker, not a post-launch fix

### Risk 2 — Data Pipeline Failure (HIGH)

**What could go wrong**: The Lichess `.zst` CSV import fails, takes too long, produces corrupt data, or the schema differs from expectations. Without the puzzle data, there is no product.

**Likelihood**: Medium — the format is documented, but decompression + 3.5M row bulk insert is non-trivial.

**Impact**: High — no puzzle data means no product launch.

**Mitigation**:
- Prototype the import script in Sprint 0 before any other backend work — this is the first thing to validate
- Use PostgreSQL `COPY` for bulk insert, not row-by-row ORM inserts
- Add schema validation at import time; fail loudly on unexpected columns
- Test with a 10,000 row subset before running the full 3.5M import
- Pin to a known-good Lichess database release date; monitor release notes for schema changes

### Risk 3 — Framework Learning Curve Kills Timeline (HIGH)

**What could go wrong**: FastAPI and Next.js are both new to the developer. Time spent on framework fundamentals (routing, middleware, SSR concepts, auth integration) compresses the available time for feature delivery. The 4-6 week timeline becomes 8-10 weeks.

**Likelihood**: Medium-High — both frameworks have learning curves; combining them with a data pipeline and chess UI is ambitious.

**Impact**: Medium — timeline slips, not product failure. But for a solo project, timeline slip often means project abandonment.

**Mitigation**:
- Reserve weeks 1-2 explicitly for framework ramp-up (hello-world to working auth endpoint)
- Use FastAPI and Next.js official tutorials/docs as the first step, not Stack Overflow and guesswork
- Build the simplest possible version of each component before adding features (static chessboard before interactive, hardcoded puzzle before API-connected)
- If timeline is at risk by end of week 3, cut the progress dashboard from v1 — not the puzzle flow or auth

---

## Outstanding Decisions

| Decision | Owner | Target Date | Status |
|----------|-------|-------------|--------|
| Hosting provider (Render vs AWS vs Fly.io) | Developer | Before week 3 | Open |
| Next.js rendering strategy (SSR vs SSG vs CSR for puzzle page) | Developer | Week 2 | Open |
| JWT storage approach (httpOnly cookie vs localStorage) | Developer | Week 2 | Open — security-sensitive, prefer httpOnly cookie |
| Email verification at registration (yes/no for MVP) | Developer | Week 1 | Open — recommend skip for MVP, add pre-EU-launch |
| GDPR deletion endpoint timing | Developer | Before any EU marketing | Open |

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-02-27 | Initial vision document — created from intake form and solution profile |
