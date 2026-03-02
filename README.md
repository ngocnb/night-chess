# Night Chess

Chess puzzle practice powered by the [Lichess open puzzle database](https://database.lichess.org/) (3.5M puzzles).

**Stack**: Python FastAPI · Next.js 14 · PostgreSQL 16 · Docker Compose

---

## Prerequisites

| Tool           | Minimum version       |
| -------------- | --------------------- |
| Docker         | 24.x                  |
| Docker Compose | v2 (`docker compose`) |
| Git            | any                   |

That's it for local development — no Python or Node.js installation required.

---

## Quick start

```bash
# 1. Clone
git clone <your-repo-url> night-chess
cd night-chess

# 2. Configure environment
cp backend/.env.example backend/.env
#    Edit backend/.env if you want custom passwords — defaults work out of the box

# 3. Start all services (first run builds images, takes ~2 min)
docker compose up
```

Services started:

| Service            | URL                            |
| ------------------ | ------------------------------ |
| Frontend (Next.js) | http://localhost:3000          |
| Backend API        | http://localhost:8000          |
| API docs (Swagger) | http://localhost:8000/api/docs |
| PostgreSQL         | localhost:5432                 |

---

## First-time database setup

After `docker compose up` is running, open a second terminal:

```bash
# Apply database migrations
docker compose exec backend alembic upgrade head
```

Expected output:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
```

---

## Import puzzle database

The Lichess puzzle CSV is ~1 GB compressed (3.5M rows). For development, import a 10k subset first:

```bash
# Streaming download + import — 10k puzzle subset (fast, ~30s)
docker compose exec backend python -m scripts.import_puzzles \
  --url https://database.lichess.org/lichess_db_puzzle.csv.zst \
  --database-url "postgresql://nightchess:nightchess_dev@db:5432/nightchess" \
  --limit 10000
```

For a full import (takes ~5–10 min depending on connection):

```bash
docker compose exec backend python -m scripts.import_puzzles \
  --url https://database.lichess.org/lichess_db_puzzle.csv.zst \
  --database-url "postgresql://nightchess:nightchess_dev@db:5432/nightchess"
```

Or use a local file if you've already downloaded it:

```bash
# Copy the file into the backend container first
docker compose cp /path/to/lichess_db_puzzle.csv.zst backend:/tmp/

docker compose exec backend python -m scripts.import_puzzles \
  --file /tmp/lichess_db_puzzle.csv.zst \
  --database-url "postgresql://nightchess:nightchess_dev@db:5432/nightchess"
```

Import flags:

| Flag             | Default   | Description                     |
| ---------------- | --------- | ------------------------------- |
| `--url URL`      | —         | Download and import from URL    |
| `--file PATH`    | —         | Import from local `.zst` file   |
| `--limit N`      | unlimited | Stop after N rows (for testing) |
| `--batch-size N` | 1000      | Rows per DB insert batch        |
| `--dry-run`      | false     | Parse only, no DB writes        |

---

## Development workflow

### Hot reload

Both services support hot reload out of the box:

- **Backend**: editing any file under `backend/app/` reloads the FastAPI server instantly
- **Frontend**: editing any file under `frontend/src/` triggers Next.js fast refresh

### Running tests

```bash
# Backend (inside container)
docker compose exec backend pytest tests/ -v --cov=app

# Backend (local Python — requires virtualenv)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v --cov=app
```

### Linting

```bash
# Backend
docker compose exec backend ruff check app/

# Frontend
docker compose exec frontend npm run lint
docker compose exec frontend npm run type-check
```

### Database shell

```bash
docker compose exec db psql -U nightchess nightchess
```

### Alembic — creating new migrations

```bash
docker compose exec backend alembic revision --autogenerate -m "describe your change"
docker compose exec backend alembic upgrade head
```

---

## Environment variables

Copy `backend/.env.example` to `backend/.env` and adjust as needed.

| Variable              | Default                     | Description                                               |
| --------------------- | --------------------------- | --------------------------------------------------------- |
| `POSTGRES_USER`       | `nightchess`                | DB username                                               |
| `POSTGRES_PASSWORD`   | `nightchess_dev`            | DB password                                               |
| `POSTGRES_DB`         | `nightchess`                | DB name                                                   |
| `DATABASE_URL`        | `postgresql+asyncpg://...`  | Full async DB URL for FastAPI                             |
| `ENVIRONMENT`         | `development`               | `development` or `production`                             |
| `SECRET_KEY`          | `dev-secret-key-...`        | JWT signing key — **change in production** (min 32 chars) |
| `CORS_ORIGINS`        | `["http://localhost:3000"]` | JSON array of allowed CORS origins                        |
| `SENTRY_DSN`          | _(empty)_                   | Sentry DSN for error tracking (optional)                  |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000`     | Backend URL visible to the browser                        |

---

## Project structure

```
night-chess/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (Sprint 1+)
│   │   ├── db/
│   │   │   ├── migrations/  # Alembic migrations
│   │   │   └── session.py   # Async SQLAlchemy engine
│   │   ├── middleware/
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   └── main.py          # FastAPI app factory
│   ├── scripts/
│   │   └── import_puzzles.py  # Lichess CSV importer
│   ├── tests/
│   ├── alembic.ini
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/app/             # Next.js App Router pages
│   ├── Dockerfile
│   ├── next.config.js
│   └── package.json
├── .github/
│   └── workflows/
│       ├── ci.yml           # Lint + test on push/PR
│       └── deploy.yml       # Build + push to GHCR + SSH deploy
├── docker-compose.yml       # Local dev orchestration
├── .env.example             # Environment template
└── .gitignore
```

---

## CI/CD — GitHub Actions

### CI (automatic)

Runs on every push and pull request to `main`:

- Backend: ruff lint → pytest with coverage
- Frontend: TypeScript type-check → ESLint

### Deployment to your server

The deploy workflow SSHs into your server and runs `docker compose pull && up -d`.

**Required GitHub Secrets** (Settings → Secrets and variables → Actions):

| Secret            | Description                |
| ----------------- | -------------------------- |
| `SERVER_HOST`     | Your server IP or hostname |
| `SERVER_USER`     | SSH username               |
| `SSH_PRIVATE_KEY` | Private key for SSH access |

**Server setup** (one-time):

```bash
# On your server
mkdir -p /opt/night-chess
cd /opt/night-chess

# Copy your production .env (do NOT commit this file)
nano .env   # fill in production values

# Pull and start (images come from GHCR after first deploy)
docker compose pull
docker compose up -d
```

---

## Running without Docker

Requires: Python 3.11+, Node.js 20+, PostgreSQL running locally.

**Backend**

```bash
cp backend/.env.example backend/.env
# DATABASE_URL defaults to @localhost — ready to use as-is

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --port 8000 --reload
```

**Frontend**

```bash
# Create frontend/.env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local

cd frontend
yarn install
yarn dev
```

**Import puzzles (local)**

```bash
# inside backend/ with .venv active
python -m scripts.import_puzzles \
  --url https://database.lichess.org/lichess_db_puzzle.csv.zst \
  --database-url "postgresql://nightchess:nightchess_dev@localhost:5432/nightchess" \
  --limit 10000
```

---

## Stopping and resetting

```bash
# Stop services
docker compose down

# Stop and remove all data (wipes the database volume)
docker compose down -v
```
