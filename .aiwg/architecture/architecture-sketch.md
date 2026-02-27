# Night Chess -- Architecture Sketch

**Document Type**: Architecture Sketch
**Project**: Night Chess -- Chess Puzzle Platform
**Version**: 1.0
**Date**: 2026-02-27
**Author**: Architecture Designer
**Status**: Active

---

## 1. Architecture Overview

Night Chess uses a separated client-server architecture: a Next.js frontend and FastAPI backend run as Docker containers on a single dedicated server, fronted by nginx as a reverse proxy and TLS terminator. PostgreSQL runs as a Docker container on the same server. GitHub Actions handles CI/CD — on push to `main`, it builds and pushes Docker images to GitHub Container Registry, then SSHs into the server to pull and restart services. A one-time data import script populates the puzzle database from the Lichess open dataset.

### System Component Diagram

```
                          +---------------------+
                          |    Browser/Client    |
                          |  (Chess Enthusiast)  |
                          +----------+----------+
                                     |
                                     | HTTPS (:443)
                                     v
                          +---------------------+
                          |       nginx          |
                          |  (reverse proxy +    |
                          |   TLS termination)   |
                          |                     |
                          |  /        → :3000    |
                          |  /api/v1/ → :8000    |
                          +----------+----------+
                                     |
                         +-----------+----------+
                         |                      |
                         v                      v
              +--------------------+  +--------------------+
              |  Next.js Frontend  |  |  FastAPI Backend   |
              |  (Docker :3000)    |  |  (Docker :8000)    |
              |                    |  |                    |
              |  - Puzzle Page     |  |  - Auth Module     |
              |  - Auth Pages      |  |  - Puzzle API      |
              |  - Dashboard Page  |  |  - Progress API    |
              |  - react-chessboard|  |  - CORS Middleware |
              |  - chess.js        |  |  - Rate Limiting   |
              +--------------------+  +----------+---------+
                                                 |
                                                 | SQL (asyncpg)
                                                 | Docker network
                                                 v
                                      +--------------------+
                                      |    PostgreSQL      |
                                      |  (Docker :5432)    |
                                      |                    |
                                      |  - users           |
                                      |  - puzzles (3.5M)  |
                                      |  - user_progress   |
                                      |  - refresh_tokens  |
                                      |  volume: pgdata     |
                                      +--------------------+

   All three containers run on one dedicated server via Docker Compose.
   pgdata volume persists PostgreSQL data across container restarts.

   --- CI/CD (GitHub Actions) ---

   git push main
        |
        v
   [GitHub Actions]
        |-- Build backend image --> ghcr.io/user/night-chess-backend:latest
        |-- Build frontend image -> ghcr.io/night-chess-frontend:latest
        |
        v
   SSH into server
        |-- docker compose pull
        |-- docker compose up -d
        +-- docker image prune -f

   --- Offline / One-Time ---

   +---------------------+         +------------------------+
   | Data Import Script  | ------> | database.lichess.org   |
   |  (Python CLI)       | <------ | lichess_db_puzzle.csv.zst
   |                     |         +------------------------+
   |  - Download .zst    |
   |  - Decompress       |
   |  - Validate schema  |
   |  - COPY into PG     |
   +----------+----------+
              |
              | COPY (bulk insert, runs inside server)
              v
        [ PostgreSQL puzzles table ]
```

---

## 2. Component Descriptions

### 2.1 Next.js Frontend

**Runtime**: Node.js 20.x (Docker container, port 3000)
**Framework**: Next.js 14+ (App Router)
**Language**: TypeScript

**Pages**:

| Route              | Purpose                        | Auth Required |
|--------------------|--------------------------------|---------------|
| `/`                | Landing + immediate puzzle     | No            |
| `/puzzle`          | Puzzle solver (main experience)| No            |
| `/login`           | Login form                     | No            |
| `/register`        | Registration form              | No            |
| `/dashboard`       | Progress history               | Yes           |
| `/settings`        | Account settings + deletion    | Yes           |

**Key Components**:

- **PuzzleBoard**: Wraps `react-chessboard` with `chess.js` for move validation. Loads FEN from API, enforces legal moves, checks solution sequence, displays result feedback.
- **PuzzleControls**: Next puzzle button, puzzle rating display, solution hint toggle (post-MVP).
- **AuthProvider**: React context managing JWT access token in memory, refresh via HttpOnly cookie.
- **ApiClient**: Centralized fetch wrapper handling auth headers, token refresh on 401, error normalization.

**Chess Libraries**:

- `react-chessboard` -- React component rendering the interactive SVG chessboard
- `chess.js` -- All move validation, FEN parsing, game state management. Zero custom chess logic.

### 2.2 FastAPI Backend

**Runtime**: Python 3.11+
**Framework**: FastAPI
**ORM**: SQLAlchemy 2.x (async)
**DB Driver**: asyncpg

**Module Structure**:

```
backend/
  app/
    main.py              # FastAPI app, middleware, lifespan
    config.py            # Settings via pydantic-settings
    models/              # SQLAlchemy ORM models
      user.py
      puzzle.py
      user_progress.py
      refresh_token.py
    schemas/             # Pydantic request/response schemas
      auth.py
      puzzle.py
      progress.py
    api/
      v1/
        auth.py          # Register, login, refresh, logout
        puzzles.py       # Random puzzle, submit answer
        users.py         # Profile, progress, account deletion
    services/
      auth_service.py    # JWT creation/validation, bcrypt
      puzzle_service.py  # Random selection logic
      progress_service.py
    middleware/
      cors.py
      rate_limit.py
    db/
      session.py         # Async engine + session factory
      migrations/        # Alembic migrations
```

**Middleware Stack** (applied in order):

1. **CORS** -- Allow frontend origin, credentials: true
2. **Rate Limiting** -- slowapi or custom: 10 req/min on auth endpoints, 60 req/min general
3. **Request ID** -- UUID per request for log correlation
4. **Error Handler** -- Catch unhandled exceptions, return structured JSON errors

### 2.3 PostgreSQL Database

**Version**: 15+
**Hosting**: Self-hosted Docker container on dedicated server (volume-backed persistent storage)

**Schema Overview**:

```sql
-- Users table
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login    TIMESTAMPTZ
);

-- Puzzles table (3.5M rows, imported from Lichess)
CREATE TABLE puzzles (
    id               VARCHAR(10) PRIMARY KEY,  -- Lichess puzzle ID (e.g., "00sHx")
    fen              TEXT NOT NULL,
    moves            TEXT NOT NULL,             -- Space-separated UCI moves
    rating           INTEGER NOT NULL,
    rating_deviation INTEGER NOT NULL,
    popularity       INTEGER NOT NULL,
    nb_plays         INTEGER NOT NULL,
    themes           TEXT,                      -- Space-separated theme tags
    game_url         TEXT,
    opening_tags     TEXT
);

-- User progress (solve history)
CREATE TABLE user_progress (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    puzzle_id   VARCHAR(10) NOT NULL REFERENCES puzzles(id),
    result      VARCHAR(10) NOT NULL CHECK (result IN ('solved', 'failed')),
    time_spent_ms INTEGER,
    solved_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, puzzle_id)
);

-- Refresh tokens (for server-side invalidation)
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_puzzles_rating ON puzzles(rating);
CREATE INDEX idx_user_progress_user_id ON user_progress(user_id);
CREATE INDEX idx_user_progress_solved_at ON user_progress(user_id, solved_at DESC);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
```

**Key Design Decisions**:

- `puzzles.id` is VARCHAR (Lichess IDs are short alphanumeric strings), not auto-increment UUID
- `user_progress` has a UNIQUE constraint on `(user_id, puzzle_id)` -- one result per puzzle per user
- `ON DELETE CASCADE` from `users` to `user_progress` and `refresh_tokens` enables GDPR deletion with a single DELETE
- `refresh_tokens` table enables server-side token revocation on logout

### 2.4 Data Import Script

**Location**: `backend/scripts/import_puzzles.py`
**Runtime**: Python CLI script (runs outside FastAPI)
**Dependencies**: `python-zstandard`, `psycopg2` (sync, for COPY performance)

**Process**:

1. Download `lichess_db_puzzle.csv.zst` from `https://database.lichess.org/`
2. Decompress `.zst` stream using `python-zstandard`
3. Validate CSV header against expected schema (fail fast on mismatch)
4. Stream rows through Pydantic validation (log and skip malformed rows)
5. Bulk insert via PostgreSQL `COPY FROM STDIN` (single transaction)
6. Verify row count: `SELECT COUNT(*) FROM puzzles` vs source CSV row count
7. Log import summary to `data_imports` audit table

**Performance Target**: Full 3.5M row import completes in under 10 minutes on standard hardware.

---

## 3. API Endpoint Design

All endpoints are prefixed with `/api/v1`.

### 3.1 Puzzle Endpoints

```
GET /api/v1/puzzles/random
    Auth: None required
    Query params:
        min_rating (optional, int) -- minimum puzzle rating
        max_rating (optional, int) -- maximum puzzle rating
    Response 200:
        {
            "id": "00sHx",
            "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
            "moves": "f6h5 e1g1",  -- first move is opponent's last move (setup)
            "rating": 1500,
            "themes": "mateIn2 short"
        }

POST /api/v1/puzzles/{puzzle_id}/submit
    Auth: Optional (Bearer token)
    Request body:
        {
            "result": "solved" | "failed",
            "time_spent_ms": 12340
        }
    Response 200 (authenticated):
        {
            "saved": true,
            "puzzle_id": "00sHx",
            "result": "solved"
        }
    Response 200 (guest):
        {
            "saved": false,
            "message": "Sign in to save your progress"
        }
```

### 3.2 Auth Endpoints

```
POST /api/v1/auth/register
    Rate limit: 5 req/min per IP
    Request body:
        {
            "email": "player@example.com",
            "password": "securepassword123"
        }
    Response 201:
        {
            "user_id": "uuid",
            "email": "player@example.com"
        }
    Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800

POST /api/v1/auth/login
    Rate limit: 10 req/min per IP
    Request body:
        {
            "email": "player@example.com",
            "password": "securepassword123"
        }
    Response 200:
        {
            "access_token": "eyJhbG...",
            "token_type": "bearer",
            "expires_in": 900
        }
    Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800

POST /api/v1/auth/refresh
    Cookie: refresh_token=<token>
    Response 200:
        {
            "access_token": "eyJhbG...",
            "token_type": "bearer",
            "expires_in": 900
        }
    Set-Cookie: refresh_token=<new_token>; ...  (token rotation)

POST /api/v1/auth/logout
    Auth: Bearer token
    Cookie: refresh_token=<token>
    Response 204: (no content)
    Set-Cookie: refresh_token=; Max-Age=0  (clear cookie)
    Side effect: Revoke refresh token in database
```

### 3.3 User Endpoints

```
GET /api/v1/users/me/progress
    Auth: Required (Bearer token)
    Query params:
        page (optional, int, default 1)
        per_page (optional, int, default 20, max 100)
    Response 200:
        {
            "total": 142,
            "page": 1,
            "per_page": 20,
            "results": [
                {
                    "puzzle_id": "00sHx",
                    "result": "solved",
                    "time_spent_ms": 12340,
                    "solved_at": "2026-03-15T10:30:00Z",
                    "puzzle_rating": 1500
                }
            ]
        }

GET /api/v1/users/me
    Auth: Required (Bearer token)
    Response 200:
        {
            "user_id": "uuid",
            "email": "player@example.com",
            "created_at": "2026-03-01T00:00:00Z",
            "puzzles_solved": 142,
            "puzzles_failed": 38
        }

DELETE /api/v1/users/me
    Auth: Required (Bearer token)
    Response 204: (no content)
    Side effect: CASCADE delete user + progress + refresh tokens
    Note: GDPR account deletion -- irreversible
```

---

## 4. Data Flow Diagrams

### 4.1 Guest Puzzle Flow

```
  Guest User                    Next.js                    FastAPI                  PostgreSQL
     |                            |                          |                         |
     |-- Opens /puzzle ---------->|                          |                         |
     |                            |-- GET /puzzles/random -->|                         |
     |                            |                          |-- TABLESAMPLE query --->|
     |                            |                          |<-- puzzle row ----------|
     |                            |<-- { fen, moves, ... } --|                         |
     |                            |                          |                         |
     |<-- Render chessboard ------|                          |                         |
     |    (FEN loaded into        |                          |                         |
     |     chess.js instance)     |                          |                         |
     |                            |                          |                         |
     |-- Makes move on board ---->|                          |                         |
     |                            |-- chess.js validates --->|  (client-side only)     |
     |                            |   legal move? yes/no     |                         |
     |                            |   matches solution?      |                         |
     |                            |                          |                         |
     |<-- Move accepted/rejected -|                          |                         |
     |                            |                          |                         |
     |-- Solves puzzle ---------->|                          |                         |
     |                            |-- POST /puzzles/{id}/    |                         |
     |                            |   submit (no auth) ----->|                         |
     |                            |<-- { saved: false } -----|                         |
     |<-- "Sign in to save" -----|                          |                         |
     |                            |                          |                         |
     |-- Clicks "Next Puzzle" --->|                          |                         |
     |                            |-- GET /puzzles/random -->| ... (cycle repeats)     |
```

### 4.2 Authenticated Puzzle Flow

```
  Auth User                     Next.js                    FastAPI                  PostgreSQL
     |                            |                          |                         |
     |-- POST /auth/login ------->|                          |                         |
     |                            |-- POST /auth/login ----->|                         |
     |                            |                          |-- Verify bcrypt ------->|
     |                            |                          |<-- User row ------------|
     |                            |<-- access_token (JSON) --|                         |
     |                            |   + refresh_token (cookie)|                        |
     |                            |                          |                         |
     |-- Opens /puzzle ---------->|                          |                         |
     |                            |-- GET /puzzles/random    |                         |
     |                            |   Authorization: Bearer  |                         |
     |                            |   (same flow as guest)   |                         |
     |                            |                          |                         |
     |-- Solves puzzle ---------->|                          |                         |
     |                            |-- POST /puzzles/{id}/    |                         |
     |                            |   submit                 |                         |
     |                            |   Authorization: Bearer  |                         |
     |                            |   { result: "solved" } ->|                         |
     |                            |                          |-- INSERT user_progress->|
     |                            |<-- { saved: true } ------|<-- OK ----------------|
     |<-- "Saved!" --------------|                          |                         |
     |                            |                          |                         |
     |-- Token expires (15 min)   |                          |                         |
     |                            |-- POST /auth/refresh     |                         |
     |                            |   Cookie: refresh_token  |                         |
     |                            |                          |-- Validate + rotate --->|
     |                            |<-- new access_token -----|<-- New refresh row -----|
```

### 4.3 Data Import Flow

```
  Developer                 Import Script              Lichess CDN              PostgreSQL
     |                            |                          |                         |
     |-- python import_puzzles.py |                          |                         |
     |                            |-- GET .csv.zst --------->|                         |
     |                            |<-- Stream .zst file -----|                         |
     |                            |                          |                         |
     |                            |-- Decompress .zst                                  |
     |                            |-- Validate CSV header                              |
     |                            |   (fail if schema mismatch)                        |
     |                            |                          |                         |
     |                            |-- BEGIN TRANSACTION ------------------------------>|
     |                            |-- COPY FROM STDIN (bulk) ------------------------->|
     |                            |   (stream rows, validate each with Pydantic)       |
     |                            |-- COMMIT ----------------------------------------->|
     |                            |                          |                         |
     |                            |-- SELECT COUNT(*) ------------------------------>  |
     |                            |<-- 3,500,000+ -----------------------------------|
     |                            |                          |                         |
     |                            |-- Verify count matches source                      |
     |                            |-- Log import summary to data_imports table         |
     |                            |                          |                         |
     |<-- Import complete         |                          |                         |
     |   (3.5M rows, ~5-10 min)  |                          |                         |
```

---

## 5. Technology Choices with Rationale

| Component         | Choice              | Rationale                                                              |
|-------------------|---------------------|------------------------------------------------------------------------|
| Frontend Framework| Next.js 14+         | SSR for SEO on landing page; CSR for puzzle interaction; React ecosystem for chess libraries |
| Backend Framework | FastAPI             | Async by default (good for DB-bound workload); auto-generated OpenAPI docs; Pydantic validation built-in; Python ecosystem for data import |
| Database          | PostgreSQL 15+      | ACID for auth data; handles 3.5M puzzle rows comfortably; TABLESAMPLE for random selection |
| ORM               | SQLAlchemy 2.x      | Async support; mature migration tooling (Alembic); type-safe query building |
| Chess Logic       | chess.js            | Battle-tested (1M+ weekly npm downloads); handles all special moves; FEN/PGN parsing |
| Chess Board UI    | react-chessboard    | Standard React chessboard; pairs with chess.js; drag-and-drop + click-to-move |
| Auth              | PyJWT + bcrypt      | Lightweight JWT implementation; bcrypt for password hashing; no heavy auth framework needed for v1 |
| Data Import       | python-zstandard    | Streaming decompression of .zst format; memory-efficient for 800 MB file |
| Migrations        | Alembic             | Standard SQLAlchemy migration tool; version-controlled schema changes |
| Reverse Proxy     | nginx               | TLS termination; routes `/api/v1/` to FastAPI (:8000) and `/` to Next.js (:3000); serves on :443 |
| Containerization  | Docker + Compose    | All three services (frontend, backend, PostgreSQL) run as containers; single `docker compose up` for full stack |
| CI/CD             | GitHub Actions + SSH| Builds images → pushes to GHCR → SSHs into server → `docker compose pull && up` |
| TLS               | Let's Encrypt (certbot) | Free TLS cert; auto-renewal via certbot cron; nginx-certbot integration |
| Error Tracking    | Sentry              | Free tier sufficient for MVP; both Python and Next.js SDKs available |

---

## 6. Deployment Architecture

### Active: Self-Hosted Dedicated Server (Docker Compose + nginx)

All services run on a single dedicated server. nginx terminates TLS and proxies requests to the appropriate container. This approach eliminates per-service SaaS costs and gives full control over the stack.

```
  Dedicated Server (1 machine)
  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │   nginx (:80/:443)                                  │
  │   ├── /          → Next.js container (:3000)        │
  │   └── /api/v1/   → FastAPI container (:8000)        │
  │                                                     │
  │   Docker Compose services:                          │
  │   ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
  │   │   frontend   │  │   backend    │  │    db    │ │
  │   │  Next.js     │  │  FastAPI     │  │ Postgres │ │
  │   │  :3000       │  │  :8000       │  │  :5432   │ │
  │   └──────────────┘  └──────────────┘  └──┬───────┘ │
  │                                           │         │
  │                                      pgdata volume  │
  │                                      (persistent)   │
  └─────────────────────────────────────────────────────┘
```

**Server directory layout**:
```
/opt/night-chess/
  docker-compose.yml      # Production compose file
  .env                    # Secrets (DATABASE_URL, JWT_SECRET_KEY, etc.)
  nginx/
    nightchess.conf       # nginx site config
  data/                   # Lichess import staging (temp, large)
```

**`docker-compose.yml`** (production):
```yaml
services:
  frontend:
    image: ghcr.io/YOUR_USER/night-chess-frontend:latest
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: https://yourdomain.com

  backend:
    image: ghcr.io/YOUR_USER/night-chess-backend:latest
    restart: unless-stopped
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16
    restart: unless-stopped
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "nightchess"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

**nginx config** (`/etc/nginx/sites-available/nightchess`):
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # API — FastAPI backend
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend — Next.js
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}
```

**One-time server setup**:
```bash
# Install Docker + Compose
curl -fsSL https://get.docker.com | sh

# Install nginx + certbot
apt install nginx certbot python3-certbot-nginx

# Get TLS cert
certbot --nginx -d yourdomain.com

# Create deploy user with SSH access
useradd -m deploy
# Add GitHub Actions public key to /home/deploy/.ssh/authorized_keys

# Create app directory
mkdir -p /opt/night-chess
chown deploy:deploy /opt/night-chess
# Copy docker-compose.yml and .env

# Log in to GHCR (if images are private)
docker login ghcr.io

# First deploy
cd /opt/night-chess && docker compose up -d
```

### CI/CD Pipeline (GitHub Actions → SSH)

```
  git push main
       |
       v
  ┌─── GitHub Actions ──────────────────────────────────┐
  │                                                     │
  │  [Lint + Type Check]                                │
  │         |                                           │
  │  [Unit + Integration Tests]                         │
  │         |                                           │
  │         ├──────────────────────────┐                │
  │         v                          v                │
  │  [Build backend image]    [Build frontend image]    │
  │  [Push → GHCR]            [Push → GHCR]             │
  │         |                          |                │
  │         └──────────┬───────────────┘                │
  │                    v                                │
  │            [SSH into server]                        │
  │            cd /opt/night-chess                      │
  │            docker compose pull                      │
  │            docker compose up -d --remove-orphans    │
  │            docker image prune -f                    │
  │                                                     │
  └─────────────────────────────────────────────────────┘
```

**GitHub Secrets required** (`Settings → Secrets → Actions`):
| Secret | Value |
|--------|-------|
| `SERVER_HOST` | Server IP or domain |
| `SERVER_USER` | `deploy` (SSH user) |
| `SSH_PRIVATE_KEY` | Contents of deploy user's private key |
| `GHCR_TOKEN` | GitHub PAT with `packages:write` (or use `GITHUB_TOKEN`) |

**`.github/workflows/deploy.yml`**:
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run backend tests
        run: cd backend && pip install -e ".[dev]" && pytest
      - name: Run frontend checks
        run: cd frontend && npm ci && npm run lint && npm run type-check

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/night-chess-backend:latest

      - uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/night-chess-frontend:latest

      - uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/night-chess
            docker compose pull
            docker compose up -d --remove-orphans
            docker image prune -f
```

### Future Option: Cloud Migration (if needed)

Self-hosted works well up to moderate traffic. Consider migrating to a cloud provider if:
- Server CPU/RAM becomes a bottleneck under sustained load
- Need multi-region availability or auto-scaling
- Managed PostgreSQL backups/failover become critical

Migration path: Replace Docker Compose with AWS ECS (Fargate) + RDS, or DigitalOcean App Platform. The Docker images built for self-hosted deploy without modification.

---

## 7. Cross-Cutting Concerns

### 7.1 Logging

- **Format**: JSON structured logs (machine-parseable)
- **Fields per log line**: `timestamp`, `level`, `request_id`, `user_id` (if authenticated), `method`, `path`, `status_code`, `duration_ms`
- **PII rule**: Never log email addresses or passwords. Use `user_id` (UUID) for user identification in logs.
- **Backend**: Python `structlog` or `logging` with JSON formatter
- **Frontend**: Console logs in development; Sentry for production errors

### 7.2 Error Handling

- **Backend**: Global exception handler returns consistent JSON error responses:
  ```json
  {
      "error": "not_found",
      "message": "Puzzle not found",
      "status_code": 404
  }
  ```
- **Frontend**: ApiClient catches HTTP errors, normalizes to typed error objects, displays user-friendly messages
- **Validation errors**: FastAPI returns 422 with Pydantic field-level error details
- **Unhandled errors**: Caught by middleware, logged with full traceback, return generic 500 to client

### 7.3 CORS Configuration

```python
origins = [
    "https://nightchess.app",       # Production
    "http://localhost:3000",         # Local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,          # Required for HttpOnly cookies
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 7.4 Rate Limiting

| Endpoint Group     | Limit              | Window  | Scope  |
|--------------------|--------------------|---------|--------|
| `/auth/login`      | 10 requests        | 1 min   | Per IP |
| `/auth/register`   | 5 requests         | 1 min   | Per IP |
| `/puzzles/*`       | 60 requests        | 1 min   | Per IP |
| `/users/*`         | 30 requests        | 1 min   | Per IP |
| `DELETE /users/me` | 1 request          | 1 hour  | Per user |

### 7.5 Environment Configuration

```
# Required environment variables
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/nightchess
JWT_SECRET_KEY=<random-256-bit-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=https://nightchess.app
ENVIRONMENT=production  # or development
SENTRY_DSN=<sentry-dsn>
```

All secrets loaded via environment variables. Never committed to git. Production secrets stored in `/opt/night-chess/.env` on the server (mode 600, owned by deploy user). Never stored in GHCR images or GitHub Actions logs.

---

## Version History

| Version | Date       | Change                          |
|---------|------------|---------------------------------|
| 1.0     | 2026-02-27 | Initial architecture sketch     |
| 1.1     | 2026-02-27 | Deployment updated: self-hosted Docker Compose + nginx + GitHub Actions SSH (replaces Render/Vercel) |
