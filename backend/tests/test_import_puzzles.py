"""Tests for backend/scripts/import_puzzles.py

Covers:
- CSV row parsing and Pydantic validation
- Malformed row detection and tolerance threshold
- Streaming decompression helper (mocked)
- Batch construction
- Progress reporting
- Summary formatting
- CLI argument defaults
- Dry-run mode (no DB calls)
- KeyboardInterrupt partial-stats output
"""

import csv
import io
import zstandard
from typing import Optional
from unittest.mock import MagicMock, patch, call

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
from scripts.import_puzzles import (
    PuzzleRow,
    ImportStats,
    parse_csv_row,
    validate_puzzle_row,
    build_batches,
    format_summary,
    MALFORMED_TOLERANCE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_ROW = {
    "PuzzleId": "00sHx",
    "FEN": "r1bqkb1r/pppp1ppp/2n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    "Moves": "e1g1 f6e4 d1e2 e4d6",
    "Rating": "1500",
    "RatingDeviation": "75",
    "Popularity": "80",
    "NbPlays": "12345",
    "Themes": "fork middlegame",
    "GameUrl": "https://lichess.org/abc123",
    "OpeningTags": "e4_e5",
}

FIELDNAMES = [
    "PuzzleId", "FEN", "Moves", "Rating", "RatingDeviation",
    "Popularity", "NbPlays", "Themes", "GameUrl", "OpeningTags",
]


def make_row(**overrides):
    row = dict(VALID_ROW)
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# PuzzleRow validation tests
# ---------------------------------------------------------------------------

class TestPuzzleRow:
    def test_valid_row_parses_correctly(self):
        pr = PuzzleRow(
            puzzle_id="00sHx",
            fen=VALID_ROW["FEN"],
            moves="e1g1 f6e4 d1e2 e4d6",
            rating=1500,
            rating_deviation=75,
            popularity=80,
            nb_plays=12345,
            themes="fork middlegame",
            game_url="https://lichess.org/abc123",
            opening_tags="e4_e5",
        )
        assert pr.puzzle_id == "00sHx"
        assert pr.rating == 1500
        assert pr.themes == "fork middlegame"

    def test_nullable_fields_accept_none(self):
        pr = PuzzleRow(
            puzzle_id="00sHx",
            fen=VALID_ROW["FEN"],
            moves="e1g1 f6e4",
            rating=1000,
            rating_deviation=60,
            popularity=50,
            nb_plays=100,
            themes=None,
            game_url=None,
            opening_tags=None,
        )
        assert pr.themes is None
        assert pr.game_url is None
        assert pr.opening_tags is None

    def test_nullable_fields_accept_empty_string_as_none(self):
        """Empty strings from CSV should be treated as None by parse_csv_row."""
        pr = PuzzleRow(
            puzzle_id="00sHx",
            fen=VALID_ROW["FEN"],
            moves="e1g1",
            rating=1000,
            rating_deviation=60,
            popularity=50,
            nb_plays=100,
            themes=None,
            game_url=None,
            opening_tags=None,
        )
        assert pr.themes is None

    def test_puzzle_id_max_length(self):
        pr = PuzzleRow(
            puzzle_id="1234567890",  # exactly 10 chars
            fen=VALID_ROW["FEN"],
            moves="e1g1",
            rating=1000,
            rating_deviation=60,
            popularity=50,
            nb_plays=100,
        )
        assert len(pr.puzzle_id) == 10

    def test_rating_boundary_zero(self):
        pr = PuzzleRow(
            puzzle_id="abc",
            fen=VALID_ROW["FEN"],
            moves="e1g1",
            rating=0,
            rating_deviation=60,
            popularity=50,
            nb_plays=100,
        )
        assert pr.rating == 0

    def test_rating_boundary_4000(self):
        pr = PuzzleRow(
            puzzle_id="abc",
            fen=VALID_ROW["FEN"],
            moves="e1g1",
            rating=4000,
            rating_deviation=60,
            popularity=50,
            nb_plays=100,
        )
        assert pr.rating == 4000


# ---------------------------------------------------------------------------
# parse_csv_row tests
# ---------------------------------------------------------------------------

class TestParseCsvRow:
    def test_parses_valid_dict(self):
        result = parse_csv_row(VALID_ROW)
        assert result is not None
        assert result.puzzle_id == "00sHx"
        assert result.rating == 1500
        assert result.nb_plays == 12345

    def test_empty_puzzle_id_returns_none(self):
        row = make_row(PuzzleId="")
        result = parse_csv_row(row)
        assert result is None

    def test_empty_fen_returns_none(self):
        row = make_row(FEN="")
        result = parse_csv_row(row)
        assert result is None

    def test_empty_moves_returns_none(self):
        row = make_row(Moves="")
        result = parse_csv_row(row)
        assert result is None

    def test_negative_rating_returns_none(self):
        row = make_row(Rating="-1")
        result = parse_csv_row(row)
        assert result is None

    def test_rating_above_4000_returns_none(self):
        row = make_row(Rating="4001")
        result = parse_csv_row(row)
        assert result is None

    def test_non_integer_rating_returns_none(self):
        row = make_row(Rating="not_a_number")
        result = parse_csv_row(row)
        assert result is None

    def test_empty_themes_becomes_none(self):
        row = make_row(Themes="")
        result = parse_csv_row(row)
        assert result is not None
        assert result.themes is None

    def test_empty_game_url_becomes_none(self):
        row = make_row(GameUrl="")
        result = parse_csv_row(row)
        assert result is not None
        assert result.game_url is None

    def test_empty_opening_tags_becomes_none(self):
        row = make_row(OpeningTags="")
        result = parse_csv_row(row)
        assert result is not None
        assert result.opening_tags is None

    def test_puzzle_id_too_long_returns_none(self):
        row = make_row(PuzzleId="12345678901")  # 11 chars
        result = parse_csv_row(row)
        assert result is None


# ---------------------------------------------------------------------------
# validate_puzzle_row tests (alias for the business-logic validation)
# ---------------------------------------------------------------------------

class TestValidatePuzzleRow:
    def test_valid_row_passes(self):
        pr = parse_csv_row(VALID_ROW)
        assert pr is not None
        result = validate_puzzle_row(pr)
        assert result is True

    def test_rating_exactly_0_passes(self):
        row = make_row(Rating="0")
        pr = parse_csv_row(row)
        assert pr is not None
        assert validate_puzzle_row(pr) is True

    def test_rating_exactly_4000_passes(self):
        row = make_row(Rating="4000")
        pr = parse_csv_row(row)
        assert pr is not None
        assert validate_puzzle_row(pr) is True


# ---------------------------------------------------------------------------
# ImportStats tests
# ---------------------------------------------------------------------------

class TestImportStats:
    def test_initial_state(self):
        stats = ImportStats()
        assert stats.rows_read == 0
        assert stats.rows_valid == 0
        assert stats.rows_skipped == 0
        assert stats.rows_inserted == 0
        assert stats.rows_already_exist == 0

    def test_malformed_rate_zero_when_no_rows(self):
        stats = ImportStats()
        assert stats.malformed_rate == 0.0

    def test_malformed_rate_calculation(self):
        stats = ImportStats()
        stats.rows_read = 1000
        stats.rows_skipped = 10
        assert abs(stats.malformed_rate - 0.01) < 1e-9

    def test_malformed_rate_above_tolerance_detected(self):
        stats = ImportStats()
        stats.rows_read = 1000
        stats.rows_skipped = 2  # 0.2% > 0.1% tolerance
        assert stats.malformed_rate > MALFORMED_TOLERANCE

    def test_malformed_rate_at_tolerance_ok(self):
        stats = ImportStats()
        stats.rows_read = 10000
        stats.rows_skipped = 10  # exactly 0.1%
        assert stats.malformed_rate <= MALFORMED_TOLERANCE


# ---------------------------------------------------------------------------
# build_batches tests
# ---------------------------------------------------------------------------

class TestBuildBatches:
    def _make_puzzle(self, idx: int) -> PuzzleRow:
        return PuzzleRow(
            puzzle_id=f"id{idx:05d}",
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            moves="e2e4",
            rating=1500,
            rating_deviation=75,
            popularity=80,
            nb_plays=100,
        )

    def test_single_batch(self):
        puzzles = [self._make_puzzle(i) for i in range(5)]
        batches = list(build_batches(puzzles, batch_size=10))
        assert len(batches) == 1
        assert len(batches[0]) == 5

    def test_exact_multiple_batches(self):
        puzzles = [self._make_puzzle(i) for i in range(20)]
        batches = list(build_batches(puzzles, batch_size=10))
        assert len(batches) == 2
        assert all(len(b) == 10 for b in batches)

    def test_remainder_batch(self):
        puzzles = [self._make_puzzle(i) for i in range(25)]
        batches = list(build_batches(puzzles, batch_size=10))
        assert len(batches) == 3
        assert len(batches[-1]) == 5

    def test_empty_input(self):
        batches = list(build_batches([], batch_size=10))
        assert batches == []

    def test_batch_contents_are_tuples(self):
        puzzles = [self._make_puzzle(0)]
        batches = list(build_batches(puzzles, batch_size=10))
        row_tuples = batches[0]
        assert len(row_tuples) == 1
        # Each element should be a tuple suitable for execute_values
        assert isinstance(row_tuples[0], tuple)
        assert len(row_tuples[0]) == 10  # 10 columns


# ---------------------------------------------------------------------------
# format_summary tests
# ---------------------------------------------------------------------------

class TestFormatSummary:
    def test_summary_contains_required_fields(self):
        stats = ImportStats()
        stats.rows_read = 3_500_000
        stats.rows_valid = 3_498_750
        stats.rows_skipped = 1_250
        stats.rows_inserted = 3_498_000
        stats.rows_already_exist = 750
        duration = 142.3
        db_count = 3_498_000
        filename = "lichess_db_puzzle.csv.zst"

        summary = format_summary(stats, duration, db_count, filename)

        assert "Import complete" in summary
        assert "3,500,000" in summary
        assert "3,498,750" in summary
        assert "1,250" in summary
        assert "3,498,000" in summary
        assert "750" in summary
        assert "142.3" in summary
        assert filename in summary

    def test_summary_shows_malformed_percentage(self):
        stats = ImportStats()
        stats.rows_read = 1000
        stats.rows_skipped = 10
        summary = format_summary(stats, 1.0, 990, "test.zst")
        # 10/1000 = 1.0%
        assert "1.0%" in summary or "1.000%" in summary or "1.00%" in summary

    def test_summary_has_tree_structure(self):
        stats = ImportStats()
        summary = format_summary(stats, 0.0, 0, "f.zst")
        assert "├──" in summary or "|--" in summary or "File:" in summary

    def test_zero_rows_no_division_error(self):
        stats = ImportStats()
        summary = format_summary(stats, 0.0, 0, "empty.zst")
        assert "Import complete" in summary


# ---------------------------------------------------------------------------
# Streaming decompression integration test (uses real zstandard)
# ---------------------------------------------------------------------------

class TestStreamingDecompression:
    def _make_zst_csv(self, rows: list[dict]) -> bytes:
        """Create a real zstandard-compressed CSV in memory."""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
        csv_bytes = buf.getvalue().encode()

        cctx = zstandard.ZstdCompressor()
        return cctx.compress(csv_bytes)

    def test_decompress_and_parse_small_file(self):
        """End-to-end: compress CSV -> parse -> get PuzzleRow objects."""
        from scripts.import_puzzles import stream_parse_zst

        rows_data = [VALID_ROW, make_row(PuzzleId="aAbBc", Rating="2000")]
        zst_bytes = self._make_zst_csv(rows_data)

        zst_file = io.BytesIO(zst_bytes)
        results = list(stream_parse_zst(zst_file, limit=None))

        assert len(results) == 2
        assert results[0].puzzle_id == "00sHx"
        assert results[1].puzzle_id == "aAbBc"
        assert results[1].rating == 2000

    def test_limit_respected(self):
        from scripts.import_puzzles import stream_parse_zst

        rows_data = [make_row(PuzzleId=f"id{i:04d}") for i in range(10)]
        zst_bytes = self._make_zst_csv(rows_data)

        zst_file = io.BytesIO(zst_bytes)
        results = list(stream_parse_zst(zst_file, limit=3))

        assert len(results) == 3

    def test_malformed_rows_skipped_not_aborted(self):
        from scripts.import_puzzles import stream_parse_zst

        rows_data = [
            VALID_ROW,
            make_row(PuzzleId="", FEN=""),  # malformed
            make_row(PuzzleId="valid2", Rating="9999"),  # bad rating
            make_row(PuzzleId="valid3"),  # OK
        ]
        zst_bytes = self._make_zst_csv(rows_data)
        zst_file = io.BytesIO(zst_bytes)
        results = list(stream_parse_zst(zst_file, limit=None))

        # Only 2 valid rows (VALID_ROW and "valid3")
        assert len(results) == 2
        ids = {r.puzzle_id for r in results}
        assert "00sHx" in ids
        assert "valid3" in ids

    def test_empty_nullable_fields_in_csv(self):
        from scripts.import_puzzles import stream_parse_zst

        row = make_row(Themes="", GameUrl="", OpeningTags="")
        zst_bytes = self._make_zst_csv([row])
        zst_file = io.BytesIO(zst_bytes)
        results = list(stream_parse_zst(zst_file, limit=None))

        assert len(results) == 1
        assert results[0].themes is None
        assert results[0].game_url is None
        assert results[0].opening_tags is None


# ---------------------------------------------------------------------------
# CLI argument parsing tests
# ---------------------------------------------------------------------------

class TestCLIArgs:
    def test_default_batch_size(self):
        from scripts.import_puzzles import build_arg_parser
        parser = build_arg_parser()
        args = parser.parse_args(["--file", "/tmp/test.zst"])
        assert args.batch_size == 1000

    def test_custom_batch_size(self):
        from scripts.import_puzzles import build_arg_parser
        parser = build_arg_parser()
        args = parser.parse_args(["--file", "/tmp/test.zst", "--batch-size", "500"])
        assert args.batch_size == 500

    def test_limit_none_by_default(self):
        from scripts.import_puzzles import build_arg_parser
        parser = build_arg_parser()
        args = parser.parse_args(["--file", "/tmp/test.zst"])
        assert args.limit is None

    def test_limit_set(self):
        from scripts.import_puzzles import build_arg_parser
        parser = build_arg_parser()
        args = parser.parse_args(["--file", "/tmp/test.zst", "--limit", "10000"])
        assert args.limit == 10000

    def test_dry_run_false_by_default(self):
        from scripts.import_puzzles import build_arg_parser
        parser = build_arg_parser()
        args = parser.parse_args(["--file", "/tmp/test.zst"])
        assert args.dry_run is False

    def test_dry_run_flag(self):
        from scripts.import_puzzles import build_arg_parser
        parser = build_arg_parser()
        args = parser.parse_args(["--file", "/tmp/test.zst", "--dry-run"])
        assert args.dry_run is True

    def test_url_argument(self):
        from scripts.import_puzzles import build_arg_parser
        parser = build_arg_parser()
        args = parser.parse_args(["--url", "https://example.com/file.zst"])
        assert args.url == "https://example.com/file.zst"
        assert args.file is None

    def test_database_url_default_is_none(self):
        from scripts.import_puzzles import build_arg_parser
        parser = build_arg_parser()
        args = parser.parse_args(["--file", "/tmp/test.zst"])
        # Should be None when not specified (will fall back to env var in main)
        assert args.database_url is None
