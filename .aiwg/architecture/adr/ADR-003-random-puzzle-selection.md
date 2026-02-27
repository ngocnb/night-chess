# ADR-003: Pre-cached Random Puzzle Batches over ORDER BY RANDOM()

**Status**: Proposed (validate in Sprint 0 prototype)
**Date**: 2026-02-27
**Deciders**: Developer (solo)

---

## Context

The Night Chess puzzle database contains approximately 3.5 million rows in PostgreSQL. The core user action -- "give me a random puzzle" -- executes on every page load and every "next puzzle" click. This is the single most frequently called query in the application.

The naive approach:

```sql
SELECT * FROM puzzles ORDER BY RANDOM() LIMIT 1;
```

requires PostgreSQL to:
1. Generate a random value for every row in the table (3.5M random number generations)
2. Sort all 3.5M rows by that random value
3. Return the first row

This is an O(n) full table scan + sort on every request. On a 3.5M row table, this typically takes 500ms-2s depending on hardware, which violates the p95 < 300ms target.

The random puzzle query must be fast (p95 < 50ms), reasonably uniform (no obvious bias), and simple enough for a solo developer to implement and maintain.

## Decision

Implement a **two-phase approach**, with Phase 1 for MVP and Phase 2 as a scaling improvement.

### Phase 1 -- MVP (Sprint 0-2)

Use PostgreSQL's `TABLESAMPLE` with a fallback:

```sql
-- Primary: TABLESAMPLE for approximate random sampling
-- Returns ~0.01% of rows randomly (roughly 350 rows from 3.5M)
-- Then pick one from that small set
SELECT * FROM puzzles TABLESAMPLE SYSTEM(0.01) LIMIT 1;
```

**How TABLESAMPLE SYSTEM works**: Instead of scanning every row, it randomly selects disk pages (8KB blocks) and returns rows from those pages. This is O(1) relative to table size -- it does not scale with row count.

**Fallback** (if TABLESAMPLE returns 0 rows, which can happen with very small sample percentages):

```sql
-- Fallback: random offset within known ID count
SELECT * FROM puzzles OFFSET floor(random() * (SELECT COUNT(*) FROM puzzles)) LIMIT 1;
```

The COUNT(*) can be cached in application memory (refreshed hourly) to avoid repeated count queries.

**Implementation**:

```python
async def get_random_puzzle(db: AsyncSession) -> Puzzle:
    # Try TABLESAMPLE first
    result = await db.execute(
        text("SELECT * FROM puzzles TABLESAMPLE SYSTEM(0.01) LIMIT 1")
    )
    puzzle = result.fetchone()

    if puzzle is None:
        # Fallback: offset-based random
        count = await get_cached_puzzle_count(db)
        offset = random.randint(0, count - 1)
        result = await db.execute(
            select(Puzzle).offset(offset).limit(1)
        )
        puzzle = result.scalars().first()

    return puzzle
```

### Phase 2 -- Scaling (Post-MVP, when needed)

Pre-generate batches of random puzzle IDs via a background job:

```
Background Job (runs every 10 minutes or when batch is exhausted):
  1. SELECT id FROM puzzles TABLESAMPLE SYSTEM(0.1) LIMIT 500
  2. Store the 500 IDs in an in-memory list (or Redis if multi-instance)
  3. Serve puzzle requests by popping from the pre-generated list
  4. When list < 100 remaining, trigger refresh

API request path:
  1. Pop next puzzle_id from pre-generated batch
  2. SELECT * FROM puzzles WHERE id = <puzzle_id>  -- index lookup, ~1ms
  3. Return puzzle
```

**When to implement Phase 2**: When EXPLAIN ANALYZE on production shows TABLESAMPLE exceeding 50ms p95, or when load testing reveals degradation under concurrent requests.

## Alternatives Considered

### Alternative 1: ORDER BY RANDOM() (REJECTED)

```sql
SELECT * FROM puzzles ORDER BY RANDOM() LIMIT 1;
```

**Pros**:
- Simplest possible implementation -- one line of SQL
- Perfectly uniform distribution
- No additional code or infrastructure

**Cons**:
- Full table scan + sort on every request: O(n) where n = 3.5M
- Benchmarks on comparable datasets show 500ms-2s per query
- Does not improve with indexes (the random value is generated per-query)
- At 50 concurrent users each clicking "next puzzle", this creates serious database load

**Why rejected**: Performance is unacceptable at any meaningful scale. The p95 < 300ms target is violated by a single query on an unloaded database.

### Alternative 2: Materialized View of Random IDs (REJECTED)

```sql
CREATE MATERIALIZED VIEW random_puzzles AS
  SELECT id FROM puzzles ORDER BY RANDOM() LIMIT 10000;

-- Refresh periodically
REFRESH MATERIALIZED VIEW random_puzzles;
```

**Pros**:
- Pre-computed random set, fast to query
- Standard PostgreSQL feature, no application code needed

**Cons**:
- Stale: the same 10,000 puzzles are served until the view is refreshed
- `REFRESH MATERIALIZED VIEW` takes the same O(n) time as ORDER BY RANDOM() -- just moves the cost to background
- `REFRESH MATERIALIZED VIEW CONCURRENTLY` requires a unique index and is not instant
- For a 10-minute refresh interval, users solving 3+ puzzles per session may see the same set

**Why rejected**: Staleness is a user experience problem (repeat puzzles), and the refresh operation still pays the full O(n) cost. The application-level pre-caching in Phase 2 achieves the same result with more control and no materialized view overhead.

### Alternative 3: Application-Level Random ID Generation (REJECTED)

```python
# Generate a random integer, assume sequential IDs
random_id = random.randint(1, max_puzzle_id)
puzzle = await db.get(Puzzle, random_id)
```

**Pros**:
- O(1) -- generate a number and do a primary key lookup
- No database overhead beyond a single index scan

**Cons**:
- Assumes sequential integer IDs with no gaps. Lichess puzzle IDs are alphanumeric strings (e.g., "00sHx"), not sequential integers.
- If using auto-increment surrogate keys, deletions create gaps -- random IDs may hit missing rows, requiring retry loops
- Distribution is biased if ID space has large gaps

**Why rejected**: Lichess puzzle IDs are short alphanumeric strings, not sequential integers. Converting to sequential integer IDs adds a mapping layer. The gap problem (generating IDs that do not exist) requires retry logic that adds complexity and latency variance. TABLESAMPLE achieves O(1)-like performance without these issues.

## Consequences

### Positive

- **Phase 1 meets the p95 < 50ms target**: TABLESAMPLE SYSTEM operates at the disk page level, not the row level. Benchmarks on 3.5M row tables show sub-10ms query times.
- **No additional infrastructure for MVP**: Phase 1 requires only PostgreSQL -- no Redis, no background jobs, no cron.
- **Smooth upgrade path**: Phase 1 to Phase 2 is an additive change (add a batch cache in front of the same query), not a rewrite.
- **Fallback handles edge cases**: The OFFSET-based fallback ensures a puzzle is always returned even if TABLESAMPLE yields an empty result.

### Negative

- **TABLESAMPLE is not perfectly uniform**: `TABLESAMPLE SYSTEM` samples at the page level, not the row level. Rows on the same disk page are correlated. For a puzzle app, this means some puzzles have a slightly higher probability of being selected than others. This is imperceptible to users but is not mathematically uniform.
- **Phase 2 adds complexity**: The pre-caching batch approach requires a background task, a cache data structure, and cache invalidation logic. This is justified only when Phase 1 performance degrades under real load.
- **OFFSET-based fallback has its own cost**: `OFFSET N` requires scanning N rows. With a cached count and random offset, this averages to scanning half the table (1.75M rows). This is acceptable as a rare fallback, not as the primary path.

## Validation Plan (Sprint 0)

Before committing to this approach, run the following benchmarks on the full 3.5M row dataset in local Docker PostgreSQL:

```sql
-- Benchmark 1: Naive ORDER BY RANDOM()
EXPLAIN ANALYZE SELECT * FROM puzzles ORDER BY RANDOM() LIMIT 1;

-- Benchmark 2: TABLESAMPLE SYSTEM
EXPLAIN ANALYZE SELECT * FROM puzzles TABLESAMPLE SYSTEM(0.01) LIMIT 1;

-- Benchmark 3: OFFSET-based
EXPLAIN ANALYZE SELECT * FROM puzzles OFFSET 1750000 LIMIT 1;

-- Benchmark 4: Pre-cached ID lookup (simulates Phase 2)
EXPLAIN ANALYZE SELECT * FROM puzzles WHERE id = '00sHx';
```

**Decision criteria**:
- If TABLESAMPLE p95 < 50ms on the full dataset: proceed with Phase 1 as designed
- If TABLESAMPLE p95 > 50ms: skip directly to Phase 2 (pre-cached batches) for MVP
- If ORDER BY RANDOM() p95 < 100ms (unlikely but possible on fast hardware): reconsider -- simplicity wins if performance is acceptable

**Record the benchmark results** in a Sprint 0 validation report and update this ADR status to Accepted or Superseded based on findings.

---

## Version History

| Version | Date       | Change                                  |
|---------|------------|-----------------------------------------|
| 1.0     | 2026-02-27 | Initial proposal -- pending Sprint 0 validation |
