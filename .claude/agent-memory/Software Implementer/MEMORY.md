# Software Implementer Memory — Night Chess

## Project Structure
- Backend: FastAPI (Python 3.11) at `/home/baongoc/workspaces/night-chess/backend/`
- Frontend: Next.js 14 (TypeScript, App Router) at `/home/baongoc/workspaces/night-chess/frontend/`
- Backend listens on port 8000 with `/health` endpoint
- Backend uses asyncpg + SQLAlchemy 2.0 async + Alembic

## Key Conventions
- Docker Compose dev file: `docker-compose.yml` at project root
- Production images pushed to GHCR (`ghcr.io/<repo>/backend` and `.../frontend`)
- Frontend uses Next.js standalone output (`output: 'standalone'` in next.config.js)
- Non-root users in both Dockerfiles: `appuser` (backend), `nextjs` (frontend)

## CI/CD
- CI runs on push + PR to main (`.github/workflows/ci.yml`)
- Deploy runs on push to main only (`.github/workflows/deploy.yml`)
- Branch protection enforces CI passing before merge — deploy.yml does NOT re-run tests
- Required secrets: `SERVER_HOST`, `SERVER_USER`, `SSH_PRIVATE_KEY`
- Server deploys from `/opt/night-chess/` with production `docker-compose.yml`

## Write Tool Pattern
- Must Read a file before Writing if it already exists on disk
- Even empty files (like `.gitignore`) count as "existing" and require a Read first

## Scripts Package
- `backend/scripts/__init__.py` must exist (empty) for `python -m scripts.X` to work
- Scripts must NOT import from `app/` — they are standalone CLI tools
- Use `psycopg2-binary` (sync) for CLI scripts, NOT asyncpg
- Use `zstandard` for zst streaming: `ZstdDecompressor().stream_reader(fileobj)`

## Bash Restrictions
- `pip install` and `python -m pytest` require explicit user approval per session
- Always explain what commands you need before seeking approval

## Frontend Lint
- `next lint` requires `.eslintrc.json` — always create it with `{"extends": "next/core-web-vitals"}`
- `npm ci` requires `package-lock.json` — must be committed or generated via `npm install`
