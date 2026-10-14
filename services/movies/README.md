# CineMind Movies Service (FastAPI, port 8002)

## Setup

```powershell
cd services/movies
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Seed the database from CSV

The dataset is the repo-root `tmdb_top1000_movies.csv` (1000 rows, 24 columns).
The seed script validates each row, maps only columns that exist, and
upserts on the stable `tmdb_id` key. Reruns update in place — no duplicates,
no deletes.

```powershell
cd services/movies
python seed.py              # CSV auto-resolved to ../../tmdb_top1000_movies.csv
python seed.py --dry-run    # validate only, no database writes
python seed.py --csv <path> --db cinemind --collection movies
```

Expected output ends with:

```
total_rows=1000
imported_new=N
updated_existing=M
skipped=K
write_errors=0
duplicates: handled by upsert on tmdb_id (reruns update, never duplicate); no records deleted.
```

## Verify imported records

```powershell
# count + sample via mongosh
mongosh --eval "db.getSiblingDB('cinemind').movies.countDocuments()"
mongosh --eval "db.getSiblingDB('cinemind').movies.findOne({tmdb_id: 1115544})"
mongosh --eval "db.getSiblingDB('cinemind').movies.getIndexes()"
```

Or without mongosh:

```powershell
python -c "import pymongo; c=pymongo.MongoClient('mongodb://localhost:27017')['cinemind']['movies']; print(c.count_documents({})); print(c.find_one({'tmdb_id': 1115544}, {'title': 1, 'year': 1}))"
```

## Run the service

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
curl http://localhost:8002/health
```

## Endpoints (proposed contract — docs/API_CONTRACTS.md does not exist yet)

| Method | Path | Response |
|---|---|---|
| GET | `/movies?page&limit` | `{items, page, limit, total}` (title A→Z) |
| GET | `/movies/search?q&page&limit` | same envelope, case-insensitive title match, popularity first |
| GET | `/movies/{movie_id}` | movie object; 404 unknown, 422 non-integer |
| GET | `/discover?genre&year&language&min_vote&page&limit` | same envelope, popularity first |
| GET | `/trending?limit` | `{items, limit, ranking}` — popularity DESC, vote_average tiebreak (no time field in dataset; documented proxy) |
| GET | `/movies/{movie_id}/similar?limit` | `{items, movie_id, rule}` — shared-genre count DESC, vote_average then popularity tiebreaks; 404 unknown source |

## Tests

```powershell
cd services/movies
python -m pytest tests/ -q
```

Tests use an in-memory fake collection (motor/pymongo not required);
`app/db.py` defers the motor import so the app imports without it.
