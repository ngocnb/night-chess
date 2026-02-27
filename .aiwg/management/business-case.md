# Night Chess — Business Case (Lightweight)

**Document Type**: Lightweight Business Case
**Status**: Approved — GO
**Created**: 2026-02-27
**Author**: Product Strategist
**Profile**: Solo Developer, 4-6 Week MVP

---

## 1. Executive Summary

Night Chess is a dedicated chess puzzle platform built on the Lichess open puzzle database (3.5 million
community-rated puzzles, CC0 license). It exists because chess players who want focused daily puzzle
practice have no lightweight alternative — every existing platform buries puzzles inside feature-heavy
products with account walls, ads, and social noise. The platform is built as a FastAPI backend plus
Next.js frontend by a single developer targeting a working MVP in 4-6 weeks. Cost is personal time
only; infrastructure runs on a dedicated server already owned by the developer, with domain and optional extras totaling under $30 in the first year.

---

## 2. Problem Statement

### The Core Problem

Chess enthusiasts who want daily puzzle practice must use platforms that were not designed for it.
Lichess and Chess.com are full chess platforms — puzzles are one tab among many, and first-time
visitors cannot solve a single puzzle without creating an account or clicking through multiple screens.

### Specific Gaps

| Gap | Current State | Night Chess Response |
|-----|--------------|---------------------|
| Guest access | Most platforms require account before first puzzle | Puzzle loads immediately, no signup |
| Focus | Puzzles buried inside social/game interfaces | Puzzle-only product surface |
| Open data | Lichess publishes 3.5M puzzles with CC0 license | No dedicated standalone platform uses this data |
| Cost | Chess.com premium gates better puzzle tools | Free, no ads, no premium tier |

### What Is Not a Problem

This is not a problem caused by lack of puzzle content — the Lichess dataset is the best freely
available puzzle database in the world. The problem is entirely UX and focus: nobody has built
a simple, zero-friction interface on top of it.

---

## 3. Value Proposition

### For the Guest Puzzle Solver ("Just give me a puzzle")

A chess player opens Night Chess and immediately sees a puzzle on an interactive chessboard.
No account prompt. No modal. No tour. They solve it and click next. When they close the tab,
nothing was required of them. If the experience was good, they bookmark it and return.

### For the Registered Practitioner ("I want to see my progress")

A player doing daily puzzle work registers because they want their history preserved across
sessions. The account is lightweight — email and password, no profile setup, no onboarding
sequence. Their solve history and statistics are waiting every time they return.

### Competitive Differentiation

| Platform | Puzzle Access | Ads/Upsell | Focus |
|----------|--------------|------------|-------|
| Lichess | Requires account | No ads, but full-platform noise | Full chess platform |
| Chess.com | Requires account, gated by tier | Ads + premium upsell | Full chess platform |
| Night Chess | Immediate, no account | None | Puzzles only |

The unique position is the combination: Lichess-quality puzzle data plus single-purpose UX
plus zero friction for guests. No existing platform combines all three.

---

## 4. ROM Cost Estimate (Rough Order of Magnitude, +/- 50%)

This is a personal project with no paid development cost. All estimates cover infrastructure only.

### Monthly Infrastructure (Steady State)

All services run on a dedicated server already owned by the developer (Docker Compose + nginx).
The server cost is a sunk cost — no incremental monthly charge from this project.

| Service | Notes | Monthly Cost |
|---------|-------|-------------|
| Dedicated server | Already owned; Docker Compose + nginx + PostgreSQL | $0 (sunk cost) |
| Sentry (error tracking) | Free tier (5k events/month) | $0 |
| Domain name (amortized) | ~$12/year | ~$1 |
| Let's Encrypt TLS | Free, auto-renewed via certbot | $0 |
| **Monthly total** | | **~$1** |

### First-Year Cost Projection

| Item | Cost Estimate |
|------|--------------|
| Domain registration | ~$12 |
| Server (sunk cost, not attributed to this project) | $0 |
| **First-year total** | **~$12** |

**Development cost**: Solo developer personal time — 4-6 weeks. No salary or contractor cost.

**Budget guardrail**: No ongoing infrastructure cost to manage. If the dedicated server is
decommissioned or traffic outgrows it, migrate to Render + Vercel or AWS (see ADR-004 migration
path). Docker images built for self-hosted deploy to any container platform without modification.

---

## 5. Expected Benefits

### Portfolio and Skill Development (Immediate)

- Demonstrates full-stack capability: Python/FastAPI backend, TypeScript/Next.js frontend,
  PostgreSQL data pipeline, JWT authentication, chess domain logic
- Real production deployment handling 3.5M rows of puzzle data
- GitHub-presentable open source project with complete SDLC artifact trail

### Market Validation (3-6 Months)

- Chess is a large and engaged online audience — puzzle practice has clear daily-use behavior
- If 500 puzzle solves occur in Month 1, that is a signal the guest flow works
- If 50 registered users are achieved by Month 2, that validates the progress tracking loop
- Either outcome informs whether to invest in Flutter v2 mobile

### Foundation for Mobile (6-12 Months)

- The FastAPI backend is designed from day one with versioned endpoints (`/api/v1/`) and clean
  OpenAPI response schemas suitable for Flutter consumption
- V2 mobile (Android + iOS via Flutter) requires no backend rework if v1 API design is clean

### Open Source Contribution Potential

- The Lichess data import pipeline (Python, PostgreSQL COPY, .zst decompression) could be
  extracted as a reusable open source library for other chess applications
- The project itself can be open sourced to attract community contributions after launch

---

## 6. Success Metrics

Full metric definitions live in the Vision Document
(`/home/baongoc/workspaces/night-chess/.aiwg/requirements/vision-document.md`, Section 4).

| KPI | Target | Timeframe | Signal |
|-----|--------|-----------|--------|
| Puzzle solves (guest + auth) | 500 total | Month 1 post-launch | Guest flow is working |
| Registered users | 50 accounts | Month 2 post-launch | Progress loop has pull |
| Session depth | avg 3+ puzzles/visit | Ongoing | Core engagement is real |
| Puzzle load latency | p95 < 300ms | From day 1 | Technical target met |
| Auth API latency | p95 < 200ms | From day 1 | Technical target met |
| Availability | 99% uptime | Ongoing | Reliability baseline |
| Data pipeline | Full DB imported + queryable | Within 24h of first deploy | Foundation is sound |

**North Star Metric**: A returning guest who registers because they want to save progress.
That single conversion event confirms the core loop — guest experience earns trust,
progress tracking earns commitment.

**Flutter v2 Go Signal**: If registered users exceed 200 and session depth holds at 3+ puzzles
per visit by Month 3, the Flutter v2 investment is justified.

---

## 7. Key Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Chess UX correctness bug (illegal moves, broken puzzles) | Medium | High — visible to any chess player | Use chess.js exclusively; test 100+ edge-case puzzles before launch |
| Lichess data pipeline failure (import corrupt or slow) | Medium | High — no data = no product | Prototype import script in Sprint 0; test with 10k subset first |
| Framework learning curve extends timeline | Medium-High | Medium — timeline slips, not failure | Weeks 1-2 dedicated to ramp-up; cut features before cutting timeline |
| Server hardware failure | Low | High — all services on one machine | Set up automated pg_dump backups before launch; keep Docker images in GHCR for fast redeploy on new server |

---

## 8. Go / No-Go Recommendation

**Recommendation: GO**

### Rationale

- **Near-zero financial risk**: ~$12 first-year cost (domain only); no paid development; server already owned
- **Low technical risk**: All dependencies are mature, well-documented, and widely used;
  the Lichess dataset is public domain with a stable format
- **Validated demand**: Chess puzzle practice is a well-established daily behavior for millions
  of players; the gap (zero-friction, puzzle-only experience) is real and demonstrable
- **High learning return**: Even if adoption is modest, the project builds demonstrable
  full-stack skills with a real dataset and real deployment
- **Clear exit criteria**: If 500 puzzle solves do not occur in Month 1, the guest flow has
  a problem worth diagnosing — but the cost of that diagnosis is already paid

### Conditions on GO

1. Sprint 0 Lichess data pipeline prototype must succeed before Sprint 1 begins — if the
   import cannot be validated with a 10k puzzle subset, the project is blocked and the timeline
   must be reassessed
2. Chess move validation must pass a manual test against 100+ real Lichess puzzles (covering
   castling, en passant, promotions, checkmate) before any soft launch
3. Infrastructure costs that exceed $20/month require a written decision before upgrading tiers

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-02-27 | Initial business case — created from intake, vision document, and option matrix |
