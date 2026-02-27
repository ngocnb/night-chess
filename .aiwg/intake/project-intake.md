# Project Intake Form

**Document Type**: Greenfield Project
**Generated**: 2026-02-27
**Source**: Project description + requirements.md + codebase analysis

## Metadata

- **Project name**: Night Chess — Chess Puzzle Platform
- **Requestor/owner**: Project Team (ngocnb)
- **Date**: 2026-02-27
- **Stakeholders**:
  - Engineering (core delivery team)
  - Product/Owner (feature prioritization)
  - Operations (deployment and monitoring)
  - Security (authentication and data handling)

## System Overview

**Purpose**: Night Chess is a dedicated chess puzzle platform that allows users to solve curated puzzles sourced from the Lichess open database. Guests can immediately start solving random puzzles without registration, while authenticated users can track and save their progress over time.

**Current Status**: Planning — no application code written yet. AIWG SDLC framework is installed and ready.

**Users**: External users (chess enthusiasts); guests (anonymous) and registered users (progress tracking).

**Tech Stack** (specified + inferred):
- **Languages**: Python (backend), TypeScript/JavaScript (frontend), Dart (mobile v2)
- **Frontend**: Next.js (React-based SSR/SSG)
- **Backend**: Python FastAPI (REST API)
- **Database**: PostgreSQL (user accounts, progress, puzzle metadata)
- **Mobile (v2)**: Flutter (Android + iOS)
- **Deployment**: Docker + cloud provider (AWS or Render)
- **Data Source**: Lichess puzzle database (CSV compressed, `.zst` format)

## Problem and Outcomes

**Problem Statement**: Chess enthusiasts lack a focused, no-friction puzzle-solving experience. Existing platforms (Lichess, Chess.com) bundle puzzles inside feature-heavy products. Night Chess provides a distraction-free puzzle app using the same high-quality Lichess puzzle dataset, with the option to track progress via a lightweight account system.

**Target Personas**:
- **Primary**: Chess players (beginner to intermediate) who want daily puzzle practice with minimal friction — guests who want to jump in immediately without signing up
- **Secondary**: Dedicated practitioners who want to track improvement over time — registered users who save progress across sessions

**Success Metrics (KPIs)**:
- **User adoption**: 500 puzzle solves in month 1; 50 registered users by month 2
- **Performance**: p95 puzzle load latency < 300ms; API response < 200ms for puzzle fetch
- **Puzzle engagement**: Average session > 3 puzzles solved per visit
- **Uptime**: 99% availability for web app
- **Data pipeline**: Full Lichess puzzle database imported and queryable within 24 hours of first deploy

## Current Scope and Features

**Core Features** (in-scope for v1 — web application):
- **Random puzzle serving**: Any guest can request and view a random chess puzzle without authentication
- **Puzzle rendering**: Interactive chessboard displaying puzzle position (FEN) with move validation
- **Lichess data pipeline**: Import and parse the Lichess `.zst` compressed CSV puzzle database
- **User authentication**: Register/login system (email + password, JWT-based)
- **Progress tracking**: Authenticated users can save solved/failed puzzle history
- **Puzzle rating system**: Display puzzle difficulty rating (sourced from Lichess data)

**Out-of-Scope** (v1 — deferred to v2 or later):
- Mobile applications (Android/iOS via Flutter) — planned v2
- Puzzle themes or category filtering — defer until puzzle base is validated
- Social features (leaderboards, friend challenges) — complexity not justified for MVP
- Custom puzzle creation — scope creep, not part of core value
- Spaced repetition / training algorithms — post-MVP if user engagement validates need
- Puzzle commentary or explanations — content complexity, defer

**Future Considerations** (post-MVP):
- Flutter mobile app (Android + iOS) — v2 milestone
- Puzzle filtering by theme, rating, or opening
- Spaced repetition system for improvement tracking
- Streak system and gamification
- Social/competitive features

## Architecture (Proposed)

**Architecture Style**: Separated Client-Server (API + Frontend as distinct services)

**Chosen**: Separate FastAPI backend + Next.js frontend — **Rationale**: Explicitly specified in requirements; this pattern cleanly separates concerns, allows the backend to serve both the web frontend and future Flutter mobile clients without modification, and is standard for modern web+mobile products.

**Components**:
- **FastAPI Backend** (Python): REST API serving puzzle data, handling authentication (JWT), and managing user progress. Connects to PostgreSQL. Exposes `/puzzles/random`, `/auth`, `/users/progress` endpoints.
- **Next.js Frontend** (TypeScript): SSR/SSG web application. Renders chess puzzles using a chessboard library (e.g., `react-chessboard` or `chess.js`). Calls FastAPI for puzzle data and auth.
- **PostgreSQL Database**: Stores user accounts, puzzle records (imported from Lichess), and user progress/solve history.
- **Data Import Service** (Python script): One-time (or periodic) job that downloads and decompresses the Lichess `.zst` puzzle CSV and bulk-imports into PostgreSQL.
- **Flutter Mobile App** (v2): Cross-platform mobile client consuming the same FastAPI backend. Not in v1 scope.

**Data Models** (estimated):
- **Puzzle**: `puzzle_id`, `fen` (position), `moves` (solution move sequence), `rating`, `rating_deviation`, `popularity`, `themes`, `game_url`, `created_at`
- **User**: `user_id`, `email`, `password_hash`, `created_at`, `last_login`
- **UserProgress**: `progress_id`, `user_id`, `puzzle_id`, `result` (solved/failed), `solved_at`, `time_spent_ms`

**Integration Points**:
- **Lichess Puzzle Database**: https://database.lichess.org/lichess_db_puzzle.csv.zst — public download, no API key required, bulk import on setup

## Scale and Performance (Target)

**Target Capacity**:
- **Initial users**: 100–500 (friends, early adopters, product hunt launch)
- **6-month projection**: 2,000–5,000 registered users; 10,000–20,000 guest sessions
- **2-year vision**: 50,000+ users if chess community adoption (revisit architecture at 10k)

**Performance Targets**:
- **Latency**: p95 < 300ms for puzzle fetch (PostgreSQL indexed query); p95 < 100ms for auth token validation
- **Throughput**: 50 concurrent users initially; auto-scaling threshold at 200 concurrent
- **Availability**: 99% uptime (MVP acceptable; upgrade to 99.9% post-launch)

**Performance Strategy**:
- **Puzzle query**: PostgreSQL with indexed `rating` and `themes` columns; random puzzle via `TABLESAMPLE` or `ORDER BY RANDOM()` with caching fallback
- **Caching**: Redis cache layer for random puzzle batches (reduce DB random scan cost at scale)
- **CDN**: Static Next.js assets served via CDN (Vercel/CloudFront)
- **Data volume**: Lichess puzzle database is ~3.5M puzzles (~800 MB uncompressed); fits comfortably in PostgreSQL

## Security and Compliance (Requirements)

**Security Posture**: Baseline

**Rationale**: The platform handles user credentials (email, password) and progress data — classified as Confidential (PII). No payment data, no health data, no regulatory compliance required for MVP. Baseline security controls are appropriate and proportionate to risk.

**Data Classification**:
- **Puzzle data**: Public (sourced from Lichess open database — CC0/public domain)
- **User account data**: Confidential (email, password hash — PII)
- **User progress data**: Internal (puzzle solve history — not high sensitivity but should be protected)

**Security Controls** (required for MVP):
- **Authentication**: JWT-based (short-lived access tokens + refresh tokens); bcrypt password hashing
- **Authorization**: User-scoped data access (users can only access their own progress)
- **Data Protection**: TLS in transit (HTTPS enforced); password hashing (bcrypt, cost factor ≥ 12); no plaintext secrets
- **Secrets Management**: Environment variables for development; cloud secrets manager (AWS Secrets Manager or equivalent) for production
- **Input Validation**: FastAPI Pydantic models for all request validation; parameterized queries (SQLAlchemy ORM, no raw SQL)
- **Rate Limiting**: Basic rate limiting on auth endpoints to prevent brute-force

**Compliance Requirements**:
- **GDPR awareness**: If EU users are served, implement account deletion endpoint and privacy policy. Not blocking for MVP launch but should be added pre-public-launch.
- **No HIPAA**: No health data
- **No PCI-DSS**: No payment processing
- **General security**: OWASP Top 10 awareness; dependency scanning (pip-audit, npm audit)

## Team and Operations (Planned)

**Team Size**: Small (estimated 1–3 developers, full-stack capable)
**Team Skills**:
- **Backend**: Python, FastAPI, PostgreSQL, SQLAlchemy
- **Frontend**: TypeScript, React, Next.js
- **DevOps**: Docker, basic cloud deployment
- **Mobile (v2)**: Dart/Flutter

**Development Velocity** (target):
- **Sprint length**: 1–2 weeks
- **Release frequency**: Weekly for MVP (continuous deployment post-setup)

**Process Maturity** (planned):
- **Version Control**: Git with feature branches (main + feature/*)
- **Code Review**: PR required (even solo development for quality gate)
- **Testing**: 40–60% coverage target for MVP; critical paths (auth, puzzle fetch, data import) at 80%+
- **CI/CD**: GitHub Actions (lint, test, build, deploy)
- **Documentation**: README, API docs (FastAPI auto-generates OpenAPI spec)

**Operational Support** (planned):
- **Monitoring**: Structured logs + basic metrics (request count, latency, errors)
- **Logging**: JSON structured logs; centralized via cloud provider (CloudWatch or equivalent)
- **Alerting**: Email alerts for 5xx error rate spikes and downtime
- **On-call**: Business hours for MVP; revisit at 1k+ users

## Dependencies and Infrastructure

**Third-Party Services**:
- **Lichess Puzzle Database**: https://database.lichess.org/ — public data, no API key, bulk download
- **Email**: SMTP or SendGrid for account verification emails (optional for MVP, enable for production)
- **File Storage**: Not required (no user-generated file uploads)
- **Monitoring**: Sentry (error tracking, free tier sufficient for MVP)

**Infrastructure** (proposed):
- **Hosting**: AWS (EC2 or ECS for backend, RDS for PostgreSQL) or Render (simpler managed deployment for MVP)
- **Deployment**: Docker containers (Docker Compose for local dev; ECS/Render for production)
- **Database**: Managed PostgreSQL (AWS RDS or Render PostgreSQL)
- **Caching**: Redis (optional for MVP, add at >1k concurrent users)
- **CDN**: Vercel for Next.js frontend (optimal for Next.js deployment)

## Known Risks and Uncertainties

**Technical Risks**:
- **Lichess data import complexity**: The `.zst` compressed CSV is ~800 MB uncompressed with 3.5M+ rows. Import performance and schema design need careful planning. Mitigation: prototype import script early; use PostgreSQL COPY for bulk insert performance.
- **Chess move validation**: Implementing correct chess move validation on the frontend (legal move checking, puzzle completion detection) requires a reliable chess library. Mitigation: use battle-tested `chess.js` library.
- **Random puzzle performance at scale**: `ORDER BY RANDOM()` on 3.5M rows is slow. Mitigation: pre-generate random puzzle ID batches via background job; cache results in Redis.

**Integration Risks**:
- **Lichess data format changes**: The puzzle CSV schema could change. Mitigation: pin to known schema version; add schema validation in import script; monitor Lichess database release notes.

**Timeline Risks**:
- **Scope for v1**: Puzzle rendering (chessboard + move validation) is non-trivial UX work. If timeline is tight, simplify to static position display first, add interactivity in iteration 2.

**Team Risks**:
- **Full-stack depth**: FastAPI + Next.js + Flutter is a wide stack. For v1, focus entirely on FastAPI + Next.js. Defer Flutter until v1 is stable.

## Why This Intake Now?

**Context**: New project kickoff — starting from a clean repository with requirements documented but no application code written.

**Goals**:
- Establish clear architecture and scope before development begins
- Identify technical risks early (data pipeline, chess rendering, auth)
- Enable structured SDLC process (Inception → Elaboration → Construction → Transition)
- Align on MVP boundaries to avoid scope creep

**Triggers**:
- New project kickoff with AIWG SDLC framework installed and ready to use
- Requirements documented, ready to transition from planning to implementation

## Attachments

- Solution profile: `.aiwg/intake/solution-profile.md`
- Option matrix: `.aiwg/intake/option-matrix.md`

## Next Steps

**Your intake documents are now complete and ready for the next phase!**

1. **Review** generated intake files for accuracy
2. **Proceed directly to Inception** using natural language or explicit commands:
   - Natural language: "Start Inception" or "Let's transition to Inception"
   - Explicit command: `/flow-concept-to-inception .`

**Note**: You do NOT need to run `/intake-start` — the `intake-wizard` command produces validated intake ready for immediate use.
