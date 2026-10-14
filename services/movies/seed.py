"""Seed the movies database from the root tmdb_top1000_movies.csv.

Idempotent: each row upserts on the stable ``tmdb_id`` key, so reruns
update existing documents instead of creating duplicates. Never deletes.

Usage (from services/movies/):
    python seed.py                      # CSV auto-resolved to repo root
    python seed.py --csv <path>         # explicit CSV path
    python seed.py --dry-run            # validate CSV, no database writes

Connection comes from the environment (.env supported):
    MONGODB_URI, MONGODB_DB, MONGODB_COLLECTION
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore  # dotenv optional; env vars still work

# Column contract: verified against tmdb_top1000_movies.csv (1000 rows, 24 cols).
EXPECTED_COLUMNS = (
    "tmdb_id",
    "imdb_id",
    "title",
    "original_title",
    "original_language",
    "release_date",
    "year",
    "runtime_min",
    "genres",
    "popularity",
    "vote_average",
    "vote_count",
    "budget_usd",
    "revenue_usd",
    "overview",
    "tagline",
    "director",
    "top_cast",
    "production_companies",
    "production_countries",
    "us_rating",
    "keywords",
    "poster_path",
    "tmdb_url",
)
REQUIRED_COLUMNS = ("tmdb_id", "title")

DEFAULT_CSV = Path(__file__).resolve().parent.parent.parent / "tmdb_top1000_movies.csv"


def _parse_int(value: str | None) -> int | None:
    try:
        text = (value or "").strip()
        if not text:
            return None
        return int(float(text))
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    try:
        text = (value or "").strip()
        if not text:
            return None
        return float(text)
    except ValueError:
        return None


def _parse_str(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _parse_list(value: str | None) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def build_document(row: dict[str, str], line_no: int) -> tuple[dict | None, str | None]:
    """Validate one CSV row. Returns (document, skip_reason)."""
    tmdb_raw = (row.get("tmdb_id") or "").strip()
    if not tmdb_raw or not tmdb_raw.isdigit():
        return None, f"line {line_no}: missing or non-numeric tmdb_id"
    title = (row.get("title") or "").strip()
    if not title:
        return None, f"line {line_no}: tmdb_id={tmdb_raw} missing title"

    tmdb_id = int(tmdb_raw)
    year = _parse_int(row.get("year"))
    if year is None:
        release = (row.get("release_date") or "").strip()
        if len(release) >= 4 and release[:4].isdigit():
            year = int(release[:4])

    return {
        "_id": f"tmdb-{tmdb_id}",  # deterministic; reruns target the same doc
        "tmdb_id": tmdb_id,
        "imdb_id": _parse_str(row.get("imdb_id")),
        "title": title,
        "original_title": _parse_str(row.get("original_title")) or title,
        "original_language": _parse_str(row.get("original_language")),
        "release_date": _parse_str(row.get("release_date")),
        "year": year,
        "runtime_min": _parse_int(row.get("runtime_min")),
        "genres": _parse_list(row.get("genres")),
        "popularity": _parse_float(row.get("popularity")),
        "vote_average": _parse_float(row.get("vote_average")),
        "vote_count": _parse_int(row.get("vote_count")),
        "budget_usd": _parse_int(row.get("budget_usd")),
        "revenue_usd": _parse_int(row.get("revenue_usd")),
        "overview": _parse_str(row.get("overview")),
        "tagline": _parse_str(row.get("tagline")),
        "director": _parse_str(row.get("director")),
        "top_cast": _parse_list(row.get("top_cast")),
        "production_companies": _parse_list(row.get("production_companies")),
        "production_countries": _parse_list(row.get("production_countries")),
        "us_rating": _parse_str(row.get("us_rating")),
        "keywords": _parse_list(row.get("keywords")),
        "poster_path": _parse_str(row.get("poster_path")),
        "tmdb_url": _parse_str(row.get("tmdb_url")),
    }, None


INDEX_SPECS = [
    {"keys": "tmdb_id", "unique": True},
    {"keys": "title", "unique": False},
    {"keys": [("year", -1)], "unique": False},
    {"keys": "genres", "unique": False},
]


def ensure_indexes(collection) -> None:
    """Create lookup/search indexes. Idempotent; safe to call every run."""
    for spec in INDEX_SPECS:
        keys = spec["keys"]
        collection.create_index(keys, unique=spec["unique"])
    try:
        collection.create_index(
            [("title", "text"), ("original_title", "text"), ("overview", "text")],
            name="movie_text_search",
        )
    except Exception as exc:  # e.g. conflicting text index already exists
        print(f"warning: text index not created ({exc})")


def load_rows(csv_path: Path) -> tuple[list[dict], list[str], int]:
    """Parse and validate the CSV. Returns (documents, skip_reasons, total_rows)."""
    documents: list[dict] = []
    skipped: list[str] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSV header missing required columns: {missing}")
        for col in (reader.fieldnames or []):
            if col not in EXPECTED_COLUMNS:
                print(f"warning: unexpected column ignored: {col!r}")
        total = 0
        for line_no, row in enumerate(reader, start=2):  # header is line 1
            total += 1
            doc, reason = build_document(row, line_no)
            if reason:
                skipped.append(reason)
            else:
                documents.append(doc)
    return documents, skipped, total


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed movies from tmdb_top1000_movies.csv")
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--uri", default=None)
    parser.add_argument("--db", default=None)
    parser.add_argument("--collection", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if load_dotenv is not None:
        load_dotenv(Path(__file__).resolve().parent / ".env")

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"error: CSV not found: {csv_path}", file=sys.stderr)
        return 2

    try:
        documents, skipped, total = load_rows(csv_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"total_rows={total} valid={len(documents)} skipped={len(skipped)} (dry-run, no writes)")
        for reason in skipped[:20]:
            print(f"  skipped: {reason}")
        return 0

    try:
        import pymongo
    except ImportError:
        print("error: pymongo is not installed (pip install -r requirements.txt)", file=sys.stderr)
        return 1

    uri = args.uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = args.db or os.getenv("MONGODB_DB", "cinemind")
    coll_name = args.collection or os.getenv("MONGODB_COLLECTION", "movies")

    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except Exception as exc:
        print(f"error: cannot reach MongoDB at {uri} ({exc})", file=sys.stderr)
        return 1

    collection = client[db_name][coll_name]
    ensure_indexes(collection)

    inserted = updated = 0
    write_errors: list[str] = []
    for doc in documents:
        try:
            result = collection.update_one({"tmdb_id": doc["tmdb_id"]}, {"$set": doc}, upsert=True)
            if result.upserted_id is not None:
                inserted += 1
            else:
                updated += 1
        except Exception as exc:
            write_errors.append(f"tmdb_id={doc['tmdb_id']}: {exc}")

    print(f"seed complete: db={db_name} collection={coll_name}")
    print(f"total_rows={total}")
    print(f"imported_new={inserted}")
    print(f"updated_existing={updated}")
    print(f"skipped={len(skipped)}")
    for reason in skipped[:20]:
        print(f"  skipped: {reason}")
    if len(skipped) > 20:
        print(f"  ... and {len(skipped) - 20} more")
    print(f"write_errors={len(write_errors)}")
    for err in write_errors[:20]:
        print(f"  error: {err}")
    print("duplicates: handled by upsert on tmdb_id (reruns update, never duplicate); no records deleted.")
    return 1 if write_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
