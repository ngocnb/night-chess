# Risk List — Night Chess

**Document Type**: Risk Register
**Project**: Night Chess — Chess Puzzle Platform
**Version**: 1.0
**Date**: 2026-02-27
**Owner**: Developer (solo)
**Status**: Active

---

## Risk Matrix Summary

The matrix below scores each risk using a 3x4 likelihood-impact grid. Scores are ordinal indicators
(SS = Show Stopper).

| ID    | Title                                      | Likelihood | Impact        | Score     | Status |
|-------|--------------------------------------------|------------|---------------|-----------|--------|
| R-001 | Chess Move Validation Correctness          | Medium     | Show Stopper  | CRITICAL  | Open   |
| R-002 | Lichess Data Pipeline Reliability          | Medium     | High          | HIGH      | Open   |
| R-003 | Solo Developer Bottleneck + Timeline       | High       | High          | HIGH      | Open   |
| R-004 | Framework Learning Curve                   | Medium     | Medium        | MEDIUM    | Open   |
| R-005 | Random Puzzle Query Performance            | Medium     | Medium        | MEDIUM    | Open   |
| R-006 | JWT Auth Implementation Security           | Low        | High          | MEDIUM    | Open   |
| R-007 | Chessboard Cross-Browser Rendering         | Low        | Medium        | LOW       | Open   |
| R-008 | Lichess CSV Schema Changes                 | Low        | Medium        | LOW       | Open   |
| R-009 | GDPR Account Deletion Complexity           | Low        | Low           | LOW       | Open   |
| R-010 | PostgreSQL Connection Management Under Load| Low        | Medium        | LOW       | Open   |

**Score Legend**:
- CRITICAL — Show Stopper impact; product cannot function correctly or launch
- HIGH — Significant delivery or quality impact; threatens MVP timeline or correctness
- MEDIUM — Manageable with proactive attention; unlikely to block launch alone
- LOW — Monitor only; low probability and/or low consequence

---

## Risk Detail Records

---

### R-001 — Chess Move Validation Correctness

**Category**: Technical
**Likelihood**: Medium
**Impact**: Show Stopper
**Risk Score**: CRITICAL
**Owner**: Developer
**Status**: Open

**Description**:
Incorrect move validation is the single most damaging technical failure for this product. If the
chessboard component accepts illegal moves, rejects legal moves, or mishandles special move types
(castling kingside/queenside, en passant, pawn promotion, promotion to under-promoted piece), the
core puzzle experience is broken. Users presented with incorrect chess logic will lose confidence
and leave immediately — the problem is visible and unambiguous to the target audience (chess
players). The risk materializes at the integration layer: chess.js is a mature and battle-tested
library, but wiring it into react-chessboard with correct FEN parsing, move-sequence validation
against Lichess puzzle solutions, and multi-move puzzle completion detection all introduce
opportunity for integration bugs that chess.js alone cannot prevent.

**Detailed Mitigation Plan**:

1. **Use chess.js exclusively — never implement custom move logic.** Every move legality check,
   turn tracking, check/checkmate/stalemate detection, and special move handling must route through
   chess.js. Zero tolerance for hand-rolled chess logic anywhere in the codebase.

2. **Write integration tests covering every special move type before wiring the UI.** Minimum test
   coverage required before the chessboard component is considered releasable:
   - Castling: kingside and queenside for both colors
   - En passant: both colors, including the edge case where the pawn that just moved is captured
   - Pawn promotion: to queen, rook, bishop, and knight (all four pieces)
   - Check detection: move into check rejected, move resolving check accepted
   - Checkmate detection: final move of puzzle recognized as game end
   - Illegal move rejection: moving into check, moving pinned piece, wrong color to move
   - Multi-move puzzle completion: confirm all moves in Lichess solution sequence are accepted
     in order and the puzzle is marked solved only after the final move

3. **Test against known Lichess puzzle solutions.** Extract a sample of 20–50 puzzles from the
   imported database. For each puzzle: load the FEN, replay the full solution move sequence via
   chess.js, assert the final position matches expected FEN, and assert all intermediate positions
   are valid. This tests the data pipeline and chess logic together.

4. **Regression gate in CI.** All chess logic tests must pass in CI before any frontend PR merges.
   Test failures on chess logic are blocking — no exceptions.

5. **Manual play-through during development.** The developer should personally solve a variety of
   puzzles including at least one of each special move type before marking the chessboard component
   complete. Human testing catches rendering edge cases automated tests cannot.

**Trigger Indicators** (risk is materializing when):
- A legal move is rejected during manual testing
- A puzzle solution replay produces a different final FEN than expected
- chess.js throws an exception on a Lichess FEN string
- Promotion modal does not appear or defaults to wrong piece
- CI chess logic tests fail after a library version update

---

### R-002 — Lichess Data Pipeline Reliability

**Category**: Technical
**Likelihood**: Medium
**Impact**: High
**Risk Score**: HIGH
**Owner**: Developer
**Status**: Open

**Description**:
The Lichess puzzle database is 3.5 million rows compressed to a `.zst` file (~800 MB uncompressed).
The data pipeline must: download the file, decompress `.zst` format (requires `python-zstandard` or
equivalent), parse a CSV with 9+ columns, validate data integrity, and bulk-import into PostgreSQL.
Any silent failure at any stage — corrupted decompression, malformed CSV rows, truncated import,
wrong column mapping — results in puzzles being served with incorrect FEN strings or wrong solution
move sequences. This failure is particularly insidious because the application may appear to work
(puzzles load and display) while silently serving incorrect chess positions. The 3.5M row scale
means a partial or corrupt import may go undetected in initial spot checks.

**Detailed Mitigation Plan**:

1. **Schema validation on every row before insert.** Define a strict Pydantic model matching the
   Lichess CSV schema (PuzzleId, FEN, Moves, Rating, RatingDeviation, Popularity, NbPlays, Themes,
   GameUrl, OpeningTags). Validate each row against this model during import. Log and skip malformed
   rows — do not silently coerce. Report total skipped row count at end of import.

2. **Row count verification.** After import completes, query `SELECT COUNT(*) FROM puzzles` and
   compare against expected row count from the CSV file. If the imported count differs by more than
   0.1% from the source row count, fail the import with an error and require manual review before
   the pipeline is considered successful.

3. **Spot-check sample against Lichess website.** After import, extract 10 random puzzle records
   from the database. For each: retrieve the corresponding puzzle from https://lichess.org/training/
   using the puzzle ID. Confirm that the FEN, moves, and rating match. This detects column mapping
   errors and encoding issues that row-count checks cannot catch.

4. **Checksum and integrity logging.** Record the SHA-256 checksum of the downloaded `.zst` file
   before decompression. Log import start time, end time, total rows processed, rows inserted, rows
   skipped, and any parse errors. Persist this import log to a `data_imports` table for auditability.

5. **Use PostgreSQL COPY for bulk insert, not row-by-row inserts.** Bulk insert via `COPY` or
   `execute_values` (psycopg2) orders of magnitude faster than individual inserts and reduces the
   window for partial-failure scenarios. Wrap the entire import in a single transaction — either all
   3.5M rows commit or none do.

6. **Prototype the pipeline in Sprint 0 before writing any other code.** The data pipeline is a
   dependency for all puzzle-related features. Discovering import failures in week 4 is a schedule
   disaster. Run the full import end-to-end on local Docker PostgreSQL in the first week.

**Trigger Indicators** (risk is materializing when):
- Import script raises a decompression error or zstandard library exception
- Row count after import is materially lower than expected (>0.1% discrepancy)
- A spot-checked puzzle FEN does not match the Lichess website
- Import takes significantly longer than estimated (>2 hours on standard hardware)
- Application serves a puzzle with a position string that fails FEN validation

---

### R-003 — Solo Developer Bottleneck + Timeline

**Category**: Resource / Schedule
**Likelihood**: High
**Impact**: High
**Risk Score**: HIGH
**Owner**: Developer
**Status**: Open

**Description**:
A 4–6 week timeline with one developer covering the full stack — FastAPI backend, Next.js frontend,
PostgreSQL schema design, Lichess data pipeline, JWT authentication, chess UI integration, CI/CD
setup, and deployment — is aggressive even for an experienced developer. The compounding factor is
that this developer is new to FastAPI and Next.js specifically, meaning framework-level questions
will consume additional time. Scope creep (adding "one small feature"), unexpected technical
blockers (a library incompatibility, a tricky bug), or underestimating the chess UI work are all
realistic paths to timeline failure. Timeline failure in this context means either: (a) the MVP
launches late, reducing motivation and momentum, or (b) quality shortcuts are taken (skipping
tests, bypassing auth, simplifying validation) that create technical debt or security problems.

**Detailed Mitigation Plan**:

1. **Define the v1 scope lock explicitly and enforce it.** The MVP scope is: random puzzle serving,
   interactive chessboard with move validation, user registration and login (JWT), and progress
   tracking (solved/failed history). Everything else is out of scope for v1. Write this on a
   whiteboard. When a new idea surfaces during development, log it in a backlog file — do not
   implement it. The discipline to say no to scope additions is the single most important schedule
   control for a solo developer.

2. **Time-box each feature to 3–5 days; treat overrun as a scope signal, not a push-harder signal.**
   Assign a maximum calendar duration to each major deliverable before starting it. If a feature
   exceeds its time box by 50% (e.g., 7+ days on a 5-day task), stop, assess whether to simplify
   the feature or cut it, and do not absorb the overrun silently. Overruns that are not acknowledged
   compound into multi-week delays.

3. **Prioritize the data pipeline and chess UI first.** These are the highest-risk, highest-effort
   items. Authentication and progress tracking are well-understood problems with mature patterns.
   The data pipeline and chess rendering are domain-specific and harder to estimate. Front-load the
   unknowns. If the chess UI takes 10 days instead of 5, it is better to know in week 2 than in
   week 5.

4. **Cut scope rather than cut quality.** If the timeline is slipping, the correct response is to
   defer lower-priority features (progress dashboard UI polish, puzzle rating display, email
   verification), not to skip tests or weaken validation. A smaller but correct and secure v1 is
   better than a larger but brittle one.

5. **Set a weekly self-check cadence.** Every Friday: review what was planned vs. completed for
   the week, update the risk register if anything has changed, and confirm the following week's
   priorities. This takes 30 minutes and prevents the "I thought I was on track" discovery in week 5.

6. **Define the hard stop date and plan backwards from it.** If the target launch is 6 weeks out,
   deployment and smoke testing require at least 3 days. That means feature-complete must be reached
   by day 39. Build the iteration plan backwards from this constraint.

**Trigger Indicators** (risk is materializing when):
- Any single feature exceeds its time box by more than 2 days without an explicit scope decision
- The developer is working on out-of-scope features (scope creep has started)
- The data pipeline prototype has not been completed by end of week 1
- Week 3 has started and the chessboard component is not yet rendering puzzles correctly
- The developer notices they are skipping test writing to "catch up"

---

### R-004 — Framework Learning Curve

**Category**: Technical / Schedule
**Likelihood**: Medium
**Impact**: Medium
**Risk Score**: MEDIUM
**Owner**: Developer
**Status**: Open

**Description**:
The developer has strong programming fundamentals but is new to FastAPI and Next.js specifically.
Framework-specific patterns — FastAPI dependency injection, Pydantic v2 model validation, SQLAlchemy
async sessions, Next.js App Router vs. Pages Router, React Server Components, and Next.js
middleware for JWT validation — each carry a non-trivial learning overhead. Individual surprises
(e.g., realizing mid-implementation that async SQLAlchemy behaves differently than sync, or that
Next.js App Router changes how environment variables are exposed) can consume 1–2 days of
re-work per incident.

**Mitigation**:
- Read the FastAPI and Next.js official documentation for the specific patterns needed (auth,
  database, routing) before writing implementation code — not during.
- Prototype the most uncertain integration points early: FastAPI + SQLAlchemy async session
  management, and Next.js JWT token storage approach. Validate the pattern with a minimal working
  example before building production features on top of it.
- Use established community templates as starting references (FastAPI full-stack template,
  Next.js with-auth examples) to understand idiomatic patterns.
- Avoid switching major architectural patterns mid-project (e.g., do not switch from Pages Router
  to App Router mid-implementation).

**Trigger Indicators**: More than 2 days spent debugging a framework-level issue; repeated
re-implementation of the same feature due to misunderstood framework behavior.

---

### R-005 — Random Puzzle Query Performance

**Category**: Technical
**Likelihood**: Medium
**Impact**: Medium
**Risk Score**: MEDIUM
**Owner**: Developer
**Status**: Open

**Description**:
`SELECT * FROM puzzles ORDER BY RANDOM() LIMIT 1` on a 3.5 million row table performs a full
table scan and sort on every request. At MVP scale (50 concurrent users) this may be acceptable,
but degradation will be visible before the user base grows significantly. The p95 < 300ms puzzle
fetch target is at risk if the random query is not addressed before load testing. Performance
problems that appear only under load are expensive to fix post-launch.

**Mitigation**:
- Replace `ORDER BY RANDOM()` with `TABLESAMPLE BERNOULLI` or a pre-generated random ID approach.
  The most reliable pattern: generate a batch of 500–1,000 random puzzle IDs using `RANDOM()` in
  an offline background job, store in a small cache table, and serve puzzle fetch requests from
  that cache. Refresh the cache batch when it falls below a threshold.
- Add an index on `puzzle_id` (primary key, already indexed) and on `rating` for future
  filtered queries.
- Benchmark the random query with `EXPLAIN ANALYZE` during local development on the full 3.5M
  row dataset before deploying. Do not assume it will be fast enough.
- Plan Redis caching for puzzle batches as the first post-MVP scaling measure, documented in the
  improvement roadmap (Phase 3).

**Trigger Indicators**: `EXPLAIN ANALYZE` shows sequential scan with >50ms query time on local
full dataset; p95 puzzle fetch latency exceeds 300ms in load testing; database CPU spikes on
puzzle endpoint under modest concurrency.

---

### R-006 — JWT Auth Implementation Security

**Category**: Security
**Likelihood**: Low
**Impact**: High
**Risk Score**: MEDIUM
**Owner**: Developer
**Status**: Open

**Description**:
JWT authentication contains several implementation traps that are easy to get wrong, especially
without prior FastAPI auth experience: storing access tokens in localStorage (XSS-vulnerable),
omitting token expiry or using excessively long TTLs, failing to validate the token signature
algorithm (the `alg: none` attack), not implementing refresh token rotation, and failing to
invalidate refresh tokens on logout. Any of these create exploitable vulnerabilities on a
user-facing application handling PII (email addresses, solve history).

**Mitigation**:
- Follow a single well-reviewed reference implementation for JWT in FastAPI (e.g., the
  FastAPI official security documentation or `fastapi-users` library) rather than assembling
  from multiple blog posts.
- Access token TTL: 15 minutes. Refresh token TTL: 7 days, stored in an HttpOnly cookie
  (not localStorage) to prevent XSS theft.
- Validate `alg` header explicitly — reject tokens not signed with the configured algorithm.
- On logout, invalidate the refresh token server-side (store token ID in a blocklist table
  or use a versioned token family approach).
- Add rate limiting on `/auth/login` and `/auth/register` endpoints (e.g., 10 requests/minute
  per IP) to prevent credential stuffing.
- Run `pip-audit` in CI to catch known CVEs in auth-related dependencies.

**Trigger Indicators**: Security review identifies tokens stored in localStorage; access tokens
with TTL > 1 hour; refresh tokens not invalidated on logout; `alg` header not validated.

---

### R-007 — Chessboard Cross-Browser Rendering

**Category**: Technical
**Likelihood**: Low
**Impact**: Medium
**Risk Score**: LOW
**Owner**: Developer
**Status**: Open

**Description**:
The `react-chessboard` library (or equivalent) renders an SVG/canvas chessboard. Cross-browser
differences in CSS layout, touch event handling, and drag-and-drop behavior (for move input) can
produce broken rendering or non-functional interaction on specific browsers or device types.
Mobile browser rendering is a particular concern if the MVP targets any mobile web users before
the Flutter app ships in v2.

**Mitigation**:
- Test the chessboard component manually in Chrome, Firefox, and Safari (desktop) before launch.
- Verify drag-and-drop move input and click-to-move both function correctly in all three browsers.
- For mobile web: test on one iOS Safari and one Android Chrome instance at minimum. If mobile
  rendering is broken and fixing it requires significant effort, explicitly document that mobile
  web is not supported in v1 (Flutter v2 covers mobile).
- Pin the `react-chessboard` library version in `package.json` and do not auto-update.

**Trigger Indicators**: Manual testing reveals pieces do not render or drag-and-drop fails in a
specific browser; CSS layout breaks at specific viewport widths.

---

### R-008 — Lichess CSV Schema Changes

**Category**: Technical
**Likelihood**: Low
**Impact**: Medium
**Risk Score**: LOW
**Owner**: Developer
**Status**: Open

**Description**:
The Lichess puzzle database is a publicly maintained dataset. While historically stable, the CSV
column schema could change (new columns added, column renamed, format changed) between the initial
import and any future re-import or incremental update. A schema change with no detection mechanism
results in silent data corruption: columns silently shift, wrong data lands in wrong fields.

**Mitigation**:
- Store the expected CSV header schema as a constant in the import script. On each run, validate
  the actual CSV header against the expected schema before importing any rows. Fail fast and loudly
  if the header does not match exactly.
- Record the Lichess database release version and download date in the `data_imports` audit log.
- Subscribe to the Lichess database releases page or GitHub repository to monitor for schema
  change announcements.

**Trigger Indicators**: Import script raises a schema mismatch error on a new download; spot-check
reveals a puzzle field contains data that belongs in a different column.

---

### R-009 — GDPR Account Deletion Complexity

**Category**: Security / Compliance
**Likelihood**: Low
**Impact**: Low
**Risk Score**: LOW
**Owner**: Developer
**Status**: Open

**Description**:
GDPR Article 17 (right to erasure) requires that user account deletion removes all personally
identifiable data on request. For Night Chess this means: deleting the user record, anonymizing
or deleting associated `user_progress` rows, and ensuring no PII is retained in backup logs or
structured log lines. The complexity is low relative to payment or health data systems, but
cascade deletes and log scrubbing can surprise a developer who has not implemented this before.
The risk is relevant if any EU users are served — which is likely for a chess platform.

**Mitigation**:
- Design the database schema with cascading deletes from the start: `user_progress.user_id`
  references `users.user_id` with `ON DELETE CASCADE`. Deletion of the user record automatically
  removes all progress rows.
- Implement the account deletion endpoint before any EU marketing or Product Hunt launch
  (not after).
- Audit structured log lines to confirm no PII (email addresses) appear in request logs.
  Use user IDs in log lines, not email addresses.
- Add a basic privacy policy page before public launch.

**Trigger Indicators**: User requests account deletion and progress rows remain; email addresses
visible in application log output; public launch proceeds without a privacy policy page.

---

### R-010 — PostgreSQL Connection Management Under Load

**Category**: Technical
**Likelihood**: Low
**Impact**: Medium
**Risk Score**: LOW
**Owner**: Developer
**Status**: Open

**Description**:
FastAPI is an async framework. Without proper SQLAlchemy async engine configuration and connection
pool sizing, concurrent requests can exhaust the PostgreSQL connection pool, producing `too many
connections` errors under modest load. Managed PostgreSQL instances (AWS RDS, Render) also impose
connection limits (often 25–100 on smaller tiers) that are lower than developers expect. This risk
is low at MVP scale (50 concurrent users) but becomes a real failure mode before Redis or
pgBouncer is in place.

**Mitigation**:
- Configure SQLAlchemy async engine with explicit pool settings: `pool_size=5`, `max_overflow=10`,
  `pool_timeout=30` as a starting baseline. Do not rely on defaults.
- Test connection behavior under simulated concurrency locally (e.g., `locust` or `hey`) with the
  full 3.5M row dataset present.
- Select a managed PostgreSQL tier that provides at least 25 connections. Document the connection
  limit and compare against configured pool size before deploying.
- Add pgBouncer connection pooling to the Phase 3 improvement roadmap as the first database
  scaling measure when user count approaches 1,000.

**Trigger Indicators**: `OperationalError: too many connections` in application logs; puzzle fetch
latency spikes under concurrent load testing; Sentry reports database timeout exceptions.

---

## Change Log

| Version | Date       | Author    | Change Description              |
|---------|------------|-----------|---------------------------------|
| 1.0     | 2026-02-27 | Developer | Initial risk list — 10 risks    |

---

*Risk Owner: Developer (solo project)*
*Next Review: End of week 2 (2026-03-13) or when any trigger indicator fires*
*Escalation: If R-001 or R-003 triggers materialize, halt feature work and address immediately*
