# UC-003: Import Lichess Puzzle Database

## Summary

A one-time (repeatable) automated pipeline downloads the Lichess puzzle database in `.zst` compressed CSV format, decompresses it, validates the schema, and bulk-inserts approximately 3.5 million puzzles into PostgreSQL. The pipeline must complete within 24 hours of first deploy and produce a fully queryable puzzle table with correct FEN and solution move data.

## Actor

System (automated data pipeline — Python script run by operator or CI job)

## Preconditions

- PostgreSQL database is running with the `puzzles` table schema applied (migration complete)
- Network access to `https://database.lichess.org/lichess_db_puzzle.csv.zst` is available
- Sufficient disk space for the compressed file (~100 MB) and uncompressed staging (~800 MB)
- The `zstandard` Python library is available in the runtime environment
- The operator has confirmed the target database is empty or has accepted a re-import (idempotent upsert supported)

## Main Flow

1. Operator (or CI job) executes the import script: `python scripts/import_puzzles.py`
2. Script checks whether the local `.zst` file is already cached; if not, downloads from Lichess via HTTPS with progress reporting
3. Script opens the `.zst` stream and decompresses it incrementally (streaming — no full uncompressed file written to disk)
4. Script reads the CSV header row and validates the expected column names:
   `PuzzleId, FEN, Moves, Rating, RatingDeviation, Popularity, NbPlays, Themes, GameUrl, OpeningTags`
5. If header validation fails, the script aborts with a clear schema mismatch error message and exits non-zero
6. Script processes rows in batches of 10,000; for each batch:
   a. Parses each field: `puzzle_id` (string), `fen` (string), `moves` (space-separated UCI move list), `rating` (integer), `rating_deviation` (integer), `popularity` (integer), `themes` (space-separated string), `game_url` (string)
   b. Validates that `fen` is a non-empty string and `moves` contains at least one move token
   c. Inserts the batch into PostgreSQL using `COPY` or bulk `INSERT` via SQLAlchemy; skips (logs) rows that fail individual validation
7. Script logs progress every 100,000 rows: rows processed, rows skipped, elapsed time
8. After all rows are processed, script runs a row count verification query and prints the final total
9. Script creates a PostgreSQL index on `rating` (for difficulty filtering) and ensures `puzzle_id` has a unique index
10. Script exits with code 0; logs total import time and final puzzle count

## Alternative Flows

**AF-1: Cached download reuse**
- If the `.zst` file already exists locally and matches the expected file size, skip re-download
- Log: "Using cached puzzle file at `data/lichess_db_puzzle.csv.zst`"

**AF-2: Partial re-import (idempotent)**
- If puzzles already exist in the database, the script uses `INSERT ... ON CONFLICT (puzzle_id) DO NOTHING`
- This allows re-runs without duplicate data; script logs the count of skipped (already-existing) rows

**AF-3: Network failure during download**
- Script retries the download up to 3 times with exponential backoff (5s, 15s, 45s)
- After 3 failures, script exits non-zero with a descriptive error message

**AF-4: Individual row parse failure**
- Rows with unparseable FEN or empty moves field are skipped (not inserted)
- Each skipped row is logged with its `PuzzleId` and the reason for rejection
- Import continues; final summary includes skipped row count

## Success Criteria

- [ ] All puzzles from the Lichess CSV are present in the database after a clean import (within a 0.1% tolerance for legitimately malformed source rows)
- [ ] `fen` values are stored exactly as they appear in the source CSV without modification
- [ ] `moves` field stores the full UCI move sequence as a space-separated string
- [ ] `rating` values are stored as integers matching the source data
- [ ] `GET /puzzles/random` returns valid puzzles immediately after import completes
- [ ] Import completes within 24 hours on standard hardware (target: under 4 hours on a single CPU core)
- [ ] Re-running the script does not create duplicate puzzle records
- [ ] Script exits non-zero on schema mismatch or catastrophic errors; exits zero on success

## Dependencies

- PostgreSQL `puzzles` table with schema:
  `(puzzle_id VARCHAR PRIMARY KEY, fen TEXT NOT NULL, moves TEXT NOT NULL, rating INTEGER, rating_deviation INTEGER, popularity INTEGER, themes TEXT, game_url TEXT)`
- Python libraries: `zstandard`, `psycopg2` or `sqlalchemy`, `csv` (stdlib)
- Source URL: `https://database.lichess.org/lichess_db_puzzle.csv.zst`
- Disk: ~150 MB free (compressed file only; streaming decompression avoids full uncompressed write)
- Network: HTTPS access to `database.lichess.org`

## Priority

Must Have
