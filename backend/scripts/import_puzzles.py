"""Lichess puzzle database importer for Night Chess.

Streams and imports the Lichess open puzzle database
(https://database.lichess.org/lichess_db_puzzle.csv.zst)
into the PostgreSQL ``puzzles`` table.

Usage::

    python -m scripts.import_puzzles --file /path/to/lichess_db_puzzle.csv.zst
    python -m scripts.import_puzzles --file /path/to/file.zst --limit 10000
    python -m scripts.import_puzzles --url https://database.lichess.org/lichess_db_puzzle.csv.zst
    python -m scripts.import_puzzles --file /path/to/file.zst --dry-run

The script is intentionally synchronous — it is a one-shot CLI tool, not a
FastAPI handler.  Do NOT import from ``app/`` here.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
from dataclasses import dataclass
from typing import Generator, IO, Iterable, Optional

import structlog
import zstandard
from pydantic import BaseModel, Field, ValidationError
import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MALFORMED_TOLERANCE = 0.001  # 0.1 % — abort threshold for bad rows
PROGRESS_INTERVAL = 100_000  # print progress every N rows read
ESTIMATED_TOTAL = 3_500_000  # rough total for progress %

INSERT_SQL = """
INSERT INTO puzzles
    (id, fen, moves, rating, rating_deviation, popularity, nb_plays,
     themes, game_url, opening_tags)
VALUES %s
ON CONFLICT (id) DO NOTHING
"""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class PuzzleRow(BaseModel):
    """Validated representation of a single Lichess puzzle CSV row."""

    puzzle_id: str = Field(min_length=1, max_length=10)
    fen: str = Field(min_length=1)
    moves: str = Field(min_length=1)
    rating: int = Field(ge=0, le=4000)
    rating_deviation: int
    popularity: int
    nb_plays: int
    themes: Optional[str] = None
    game_url: Optional[str] = None
    opening_tags: Optional[str] = None


@dataclass
class ImportStats:
    """Mutable counters updated throughout the import run."""

    rows_read: int = 0
    rows_valid: int = 0
    rows_skipped: int = 0
    rows_inserted: int = 0
    rows_already_exist: int = 0

    @property
    def malformed_rate(self) -> float:
        if self.rows_read == 0:
            return 0.0
        return self.rows_skipped / self.rows_read


# ---------------------------------------------------------------------------
# Row parsing and validation helpers
# ---------------------------------------------------------------------------

_NULLABLE_FIELDS = ("Themes", "GameUrl", "OpeningTags")


def parse_csv_row(row: dict) -> Optional[PuzzleRow]:
    """Parse and validate a raw CSV dict row.

    Returns a :class:`PuzzleRow` on success, or ``None`` if the row is
    malformed / out-of-range.  Empty strings for nullable fields are
    normalised to ``None``.
    """
    puzzle_id = row.get("PuzzleId", "").strip()
    fen = row.get("FEN", "").strip()
    moves = row.get("Moves", "").strip()

    # Fast-path rejections before Pydantic overhead
    if not puzzle_id or not fen or not moves:
        return None

    def _opt(key: str) -> Optional[str]:
        val = row.get(key, "").strip()
        return val if val else None

    try:
        rating = int(row.get("Rating", ""))
        rating_deviation = int(row.get("RatingDeviation", ""))
        popularity = int(row.get("Popularity", ""))
        nb_plays = int(row.get("NbPlays", ""))
    except (ValueError, TypeError):
        return None

    try:
        return PuzzleRow(
            puzzle_id=puzzle_id,
            fen=fen,
            moves=moves,
            rating=rating,
            rating_deviation=rating_deviation,
            popularity=popularity,
            nb_plays=nb_plays,
            themes=_opt("Themes"),
            game_url=_opt("GameUrl"),
            opening_tags=_opt("OpeningTags"),
        )
    except ValidationError:
        return None


def validate_puzzle_row(row: PuzzleRow) -> bool:
    """Secondary validation gate after initial parse.

    Currently a no-op pass-through (Pydantic covers all constraints), but
    kept as an explicit hook for future business-rule extensions.
    """
    return True


# ---------------------------------------------------------------------------
# Batch builder
# ---------------------------------------------------------------------------

def build_batches(
    puzzles: Iterable[PuzzleRow],
    batch_size: int,
) -> Generator[list[tuple], None, None]:
    """Yield lists of row-tuples suitable for ``psycopg2.extras.execute_values``.

    Each tuple matches the column order in ``INSERT_SQL``:
    ``(id, fen, moves, rating, rating_deviation, popularity, nb_plays,
    themes, game_url, opening_tags)``
    """
    batch: list[tuple] = []
    for puzzle in puzzles:
        batch.append((
            puzzle.puzzle_id,
            puzzle.fen,
            puzzle.moves,
            puzzle.rating,
            puzzle.rating_deviation,
            puzzle.popularity,
            puzzle.nb_plays,
            puzzle.themes,
            puzzle.game_url,
            puzzle.opening_tags,
        ))
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


# ---------------------------------------------------------------------------
# Streaming decompression
# ---------------------------------------------------------------------------

def stream_parse_zst(
    fileobj: IO[bytes],
    limit: Optional[int] = None,
) -> Generator[PuzzleRow, None, None]:
    """Decompress a ``.zst`` stream and yield validated :class:`PuzzleRow` objects.

    Args:
        fileobj: A binary file-like object containing zstandard-compressed data.
        limit: If set, stop after yielding this many valid rows.

    Malformed rows are silently skipped; callers should track counts separately.
    """
    dctx = zstandard.ZstdDecompressor()
    yielded = 0

    with dctx.stream_reader(fileobj) as reader:
        text_stream = io.TextIOWrapper(reader, encoding="utf-8", newline="")
        reader_csv = csv.DictReader(text_stream)

        for raw_row in reader_csv:
            puzzle = parse_csv_row(raw_row)
            if puzzle is None:
                continue
            yield puzzle
            yielded += 1
            if limit is not None and yielded >= limit:
                break


# ---------------------------------------------------------------------------
# Summary formatting
# ---------------------------------------------------------------------------

def format_summary(
    stats: ImportStats,
    duration: float,
    db_count: int,
    filename: str,
) -> str:
    """Render the final import summary in tree format."""
    skipped_pct = stats.malformed_rate * 100
    lines = [
        "Import complete",
        f"├── File: {filename}",
        f"├── Rows read: {stats.rows_read:,}",
        f"├── Rows valid: {stats.rows_valid:,}",
        f"├── Rows skipped (malformed): {stats.rows_skipped:,} ({skipped_pct:.3f}%)",
        f"├── Rows inserted: {stats.rows_inserted:,}",
        f"├── Rows already existed: {stats.rows_already_exist:,}",
        f"├── Duration: {duration:.1f}s",
        f"└── Puzzles in DB: {db_count:,}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import Lichess puzzle database into Night Chess PostgreSQL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--file",
        metavar="PATH",
        default=None,
        help="Path to the .zst file to import.",
    )
    source.add_argument(
        "--url",
        metavar="URL",
        default=None,
        help="Download the .zst file from this URL before importing.",
    )
    parser.add_argument(
        "--database-url",
        metavar="URL",
        default=None,
        help="PostgreSQL connection string (default: DATABASE_URL env var).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Import only the first N valid rows (useful for testing).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        metavar="N",
        help="Number of rows per INSERT batch (default: 1000).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Parse and validate rows without inserting into the database.",
    )
    return parser


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def download_file(url: str, dest_path: str) -> None:
    """Stream-download *url* to *dest_path* using requests."""
    import requests

    log.info("Downloading puzzle database", url=url, dest=dest_path)
    with requests.get(url, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):  # 1 MB chunks
                fh.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(
                        f"\rDownloaded {downloaded / 1_048_576:.1f} MB"
                        f" / {total / 1_048_576:.1f} MB ({pct:.1f}%)",
                        end="",
                        flush=True,
                    )
    print()  # newline after progress


# ---------------------------------------------------------------------------
# Core import routine
# ---------------------------------------------------------------------------

def run_import(
    fileobj: IO[bytes],
    filename: str,
    database_url: str,
    limit: Optional[int],
    batch_size: int,
    dry_run: bool,
) -> ImportStats:
    """Perform the full streaming import.

    Args:
        fileobj:      Binary file-like object for the ``.zst`` compressed CSV.
        filename:     Human-readable filename for progress/summary output.
        database_url: psycopg2 DSN / connection string.
        limit:        Maximum valid rows to import (``None`` means no limit).
        batch_size:   Rows per INSERT batch.
        dry_run:      When ``True``, parse only — do not touch the database.

    Returns:
        :class:`ImportStats` with final counters.

    Raises:
        SystemExit: When the malformed-row rate exceeds :data:`MALFORMED_TOLERANCE`.
    """
    stats = ImportStats()
    start_time = time.monotonic()

    conn = None
    cursor = None

    if not dry_run:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()

    dctx = zstandard.ZstdDecompressor()

    try:
        with dctx.stream_reader(fileobj) as reader:
            text_stream = io.TextIOWrapper(reader, encoding="utf-8", newline="")
            reader_csv = csv.DictReader(text_stream)

            batch: list[tuple] = []

            def flush_batch() -> None:
                if dry_run or not batch:
                    return
                psycopg2.extras.execute_values(cursor, INSERT_SQL, batch, page_size=batch_size)
                # Count how many rows were actually inserted vs already existed
                inserted = cursor.rowcount if cursor.rowcount >= 0 else len(batch)
                stats.rows_inserted += inserted
                stats.rows_already_exist += len(batch) - inserted
                conn.commit()
                batch.clear()

            for raw_row in reader_csv:
                stats.rows_read += 1

                # Progress reporting
                if stats.rows_read % PROGRESS_INTERVAL == 0:
                    pct = stats.rows_read / ESTIMATED_TOTAL * 100
                    elapsed = time.monotonic() - start_time
                    print(
                        f"Processed {stats.rows_read:,} / ~{ESTIMATED_TOTAL:,} rows"
                        f" ({pct:.1f}%) — {elapsed:.0f}s elapsed"
                    )

                puzzle = parse_csv_row(raw_row)
                if puzzle is None:
                    stats.rows_skipped += 1
                    log.debug("Skipped malformed row", row=dict(raw_row))

                    # Abort if malformed rate exceeds tolerance (check every 1000 rows)
                    if stats.rows_read % 1000 == 0 and stats.rows_read >= 1000:
                        rate = stats.malformed_rate
                        if rate > MALFORMED_TOLERANCE:
                            log.error(
                                "Malformed row rate exceeds tolerance — aborting",
                                rate=f"{rate:.4%}",
                                tolerance=f"{MALFORMED_TOLERANCE:.4%}",
                                rows_read=stats.rows_read,
                                rows_skipped=stats.rows_skipped,
                            )
                            if conn:
                                conn.rollback()
                            print(
                                f"ERROR: Malformed row rate {rate:.4%} exceeds"
                                f" {MALFORMED_TOLERANCE:.4%} tolerance."
                                " Aborting import.",
                                file=sys.stderr,
                            )
                            sys.exit(1)
                    continue

                stats.rows_valid += 1

                batch.append((
                    puzzle.puzzle_id,
                    puzzle.fen,
                    puzzle.moves,
                    puzzle.rating,
                    puzzle.rating_deviation,
                    puzzle.popularity,
                    puzzle.nb_plays,
                    puzzle.themes,
                    puzzle.game_url,
                    puzzle.opening_tags,
                ))

                if len(batch) >= batch_size:
                    flush_batch()

                # Respect --limit on valid rows
                if limit is not None and stats.rows_valid >= limit:
                    log.info("Reached row limit", limit=limit)
                    break

            # Flush remaining partial batch
            flush_batch()

    except KeyboardInterrupt:
        if conn:
            conn.rollback()
        elapsed = time.monotonic() - start_time
        print("\nInterrupted by user. Partial stats:")
        print(
            f"  Rows read: {stats.rows_read:,}\n"
            f"  Rows valid: {stats.rows_valid:,}\n"
            f"  Rows skipped: {stats.rows_skipped:,}\n"
            f"  Rows inserted: {stats.rows_inserted:,}\n"
            f"  Elapsed: {elapsed:.1f}s"
        )
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return stats


# ---------------------------------------------------------------------------
# DB row count
# ---------------------------------------------------------------------------

def get_puzzle_count(database_url: str) -> int:
    """Return the current number of rows in the ``puzzles`` table."""
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM puzzles")
            return cur.fetchone()[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    # Resolve database URL
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not args.dry_run and not database_url:
        print(
            "ERROR: No database URL provided. Set DATABASE_URL env var or"
            " use --database-url.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve source file
    zst_path: Optional[str] = args.file
    if args.url:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".zst", delete=False)
        tmp.close()
        zst_path = tmp.name
        try:
            download_file(args.url, zst_path)
        except Exception as exc:
            log.error("Download failed", url=args.url, error=str(exc))
            sys.exit(1)

    if not zst_path:
        print("ERROR: Provide --file or --url.", file=sys.stderr)
        sys.exit(1)

    filename = os.path.basename(zst_path)
    log.info(
        "Starting import",
        file=filename,
        limit=args.limit,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    start_time = time.monotonic()

    try:
        with open(zst_path, "rb") as fh:
            stats = run_import(
                fileobj=fh,
                filename=filename,
                database_url=database_url or "",
                limit=args.limit,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as exc:
        log.error("Import failed", error=str(exc))
        sys.exit(1)

    duration = time.monotonic() - start_time

    # Post-import row count
    db_count = 0
    if not args.dry_run and database_url:
        try:
            db_count = get_puzzle_count(database_url)
        except Exception as exc:
            log.warning("Could not fetch puzzle count", error=str(exc))

    summary = format_summary(stats, duration, db_count, filename)
    print(summary)

    # Verify count when --limit was used
    if args.limit is not None and not args.dry_run:
        expected_min = args.limit - stats.rows_skipped
        if db_count < expected_min:
            log.warning(
                "Puzzle count lower than expected after limited import",
                db_count=db_count,
                expected_min=expected_min,
            )


if __name__ == "__main__":
    main()
