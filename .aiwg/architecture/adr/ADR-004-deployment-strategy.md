# ADR-004: Self-Hosted Deployment with Docker Compose + nginx + GitHub Actions

**Status**: Accepted
**Date**: 2026-02-27
**Deciders**: Developer (solo)

---

## Context

Night Chess needs a deployment strategy for the FastAPI backend, Next.js frontend, and PostgreSQL database. The initial recommendation (Render + Vercel) was based on minimizing operational overhead, but the developer has access to a dedicated server and wants to eliminate per-service SaaS costs at the early stage.

Constraints:
- Solo developer, 4-6 week MVP timeline
- Dedicated server already available (cost already paid)
- CI/CD must be automated — no manual deploy steps on each push
- TLS required (HTTPS enforced for HttpOnly cookie security)
- Must support the Flutter v2 mobile client consuming the same FastAPI backend
- All three services (frontend, backend, database) must be co-deployable

## Decision

Deploy all services on a single dedicated server using **Docker Compose** for container orchestration, **nginx** for reverse proxy and TLS termination, **Let's Encrypt (certbot)** for free TLS certificates, and **GitHub Actions** for CI/CD via SSH.

**Deployment flow**:
```
git push main
  → GitHub Actions runs tests
  → Builds Docker images for backend and frontend
  → Pushes images to GitHub Container Registry (GHCR)
  → SSHs into dedicated server
  → docker compose pull && docker compose up -d
```

**Service layout on server**:

| Service | Container | Port | Notes |
|---------|-----------|------|-------|
| nginx | Host process | 80, 443 | TLS termination, reverse proxy |
| Next.js | Docker | 3000 | Internal only, nginx proxies to it |
| FastAPI | Docker | 8000 | Internal only, nginx proxies `/api/` |
| PostgreSQL | Docker | 5432 | Internal only, not exposed to host |

**nginx routing**:
- `/api/` → FastAPI container (:8000)
- `/` → Next.js container (:3000)
- Port 80 → 301 redirect to HTTPS

**Data persistence**:
- PostgreSQL data in a named Docker volume (`pgdata`) — survives container restarts and image updates
- `.env` file on server at `/opt/night-chess/.env` (mode 600) for all secrets

## Alternatives Considered

### Alternative 1: Render (backend) + Vercel (frontend)

**How it works**: FastAPI deployed as a Render Web Service (Docker); Next.js deployed to Vercel; PostgreSQL as Render's managed database service. Both platforms auto-deploy on push to `main`.

**Pros**:
- Zero server management — both platforms handle OS updates, scaling, health checks
- Render provides managed PostgreSQL with automatic backups, point-in-time recovery
- Vercel provides CDN edge caching for Next.js static assets globally
- No SSH key management, no nginx config, no certbot setup
- Render free tier + Vercel free tier = $0/month initially

**Cons**:
- Render free tier has cold starts (service sleeps after 15 minutes of inactivity) — degrades puzzle fetch latency for returning users
- Render PostgreSQL free tier expires after 90 days; forced migration to $7/month Starter
- Vercel hobby tier has bandwidth limits; SSR function timeouts at 10s (acceptable for MVP)
- Costs grow non-linearly as traffic increases — two separate billing relationships
- Developer already pays for a dedicated server, making this option an unnecessary cost addition

**Why rejected**: The developer has an existing dedicated server. Running on it costs nothing additional. The cold start problem on Render's free tier would degrade the puzzle experience for users who visit after inactivity periods.

---

### Alternative 2: Single Process (no Docker, direct systemd services)

**How it works**: Run FastAPI directly via uvicorn, Next.js directly via `node server.js`, and PostgreSQL as a system package. Managed via systemd services. nginx installed as a system package.

**Pros**:
- No Docker overhead (CPU, memory, image management)
- Simpler local debugging (no container networking)
- Less tooling to learn

**Cons**:
- Environment divergence between local dev and production — "works on my machine" problems
- Python virtual env and Node.js version management becomes manual
- System package updates can break services (e.g., PostgreSQL major version upgrade)
- No easy rollback — can't simply pull a previous image tag
- CI/CD is more complex: must ssh in, `git pull`, restart services, run migrations
- Reproducibility is lower — the deployment environment depends on server state accumulated over time

**Why rejected**: Docker provides consistent, reproducible environments and clean rollback (just pull the previous tag). The operational simplicity of `docker compose up -d` outweighs the minor overhead cost.

---

### Alternative 3: Kubernetes (k3s on dedicated server)

**How it works**: Install k3s (lightweight Kubernetes) on the dedicated server. Deploy all services as Kubernetes Deployments with a nginx Ingress controller.

**Pros**:
- Rolling updates with zero downtime
- Health checks and automatic pod restarts
- Namespace isolation
- Scales to multi-node cluster if server is upgraded

**Cons**:
- Significant operational overhead for a solo MVP developer
- k3s still requires learning kubectl, manifests, Ingress configuration
- Overkill: Docker Compose restarts failed containers, handles the same use case with 1/10th the complexity
- Longer setup time (days vs hours for Docker Compose)

**Why rejected**: Kubernetes solves problems Night Chess will not have during MVP phase. Docker Compose with `restart: unless-stopped` is sufficient reliability for the target 99% uptime SLA.

## Consequences

### Positive

- **Zero incremental cost**: The dedicated server is already paid for; running all services on it adds nothing to the monthly bill.
- **No cold starts**: Containers stay running — puzzle fetch p95 is consistent regardless of traffic gaps.
- **Full control**: No SaaS platform constraints on request timeout, memory limits, or allowed packages.
- **Simple rollback**: `docker compose pull` of a previous image tag restores a known-good deployment.
- **Unified deployment**: One SSH connection deploys everything — backend, frontend, and database all in one `docker compose up`.
- **Production parity**: The same Docker images run in local dev (docker compose up) and production. No environment divergence.

### Negative

- **Manual backup responsibility**: No managed backup service. Must configure PostgreSQL backups explicitly (pg_dump cron, or volume backup). **Action required: set up automated pg_dump before launch.**
- **OS maintenance**: Server OS updates, security patches, and disk management are the developer's responsibility. Mitigated by: unattended-upgrades for security patches, minimal additional software installed.
- **No CDN for static assets**: Vercel provided edge caching globally. Self-hosted nginx does not. For MVP scale this is acceptable; revisit if latency from distant users becomes a complaint.
- **Single point of failure**: All services on one server. If the server goes down, everything goes down. Mitigated by: `restart: unless-stopped` handles container crashes; server-level uptime depends on hosting provider. For 99% SLA target, this is acceptable.
- **nginx + certbot to manage**: Adds one-time setup complexity. Certbot auto-renewal must be confirmed working.

## Implementation Requirements

### Server Prerequisites (one-time setup)

```bash
# 1. Install Docker Engine
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER

# 2. Install nginx and certbot
apt install nginx certbot python3-certbot-nginx -y

# 3. Create deploy user (for GitHub Actions SSH)
useradd -m -s /bin/bash deploy
mkdir -p /home/deploy/.ssh
# Paste GitHub Actions public key into:
# /home/deploy/.ssh/authorized_keys
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

# 4. Grant deploy user permission to run docker
usermod -aG docker deploy

# 5. Create app directory
mkdir -p /opt/night-chess
chown deploy:deploy /opt/night-chess

# 6. Get TLS cert
certbot --nginx -d yourdomain.com

# 7. Verify certbot auto-renewal
certbot renew --dry-run
```

### Backup Configuration (required before launch)

Set up daily pg_dump before public launch:

```bash
# /etc/cron.d/nightchess-backup
0 3 * * * deploy docker exec night-chess-db-1 \
  pg_dump -U nightchess nightchess | \
  gzip > /opt/night-chess/backups/nightchess-$(date +\%Y\%m\%d).sql.gz

# Retain 14 days
0 4 * * * deploy find /opt/night-chess/backups -mtime +14 -delete
```

### GitHub Actions Secrets Required

| Secret | Description |
|--------|-------------|
| `SERVER_HOST` | Server IP or domain |
| `SERVER_USER` | `deploy` |
| `SSH_PRIVATE_KEY` | Private key matching the authorized_keys on server |

`GITHUB_TOKEN` is automatically available for pushing to GHCR — no additional secret needed.

### Migration Path (if outgrown)

Docker images built for this deployment run without modification on:
- **DigitalOcean App Platform** — drop Compose, use their managed service
- **AWS ECS Fargate** — replace Compose with task definitions; use RDS for PostgreSQL
- **Fly.io** — fly deploy reads Dockerfiles directly

The FastAPI image is stateless and horizontally scalable. PostgreSQL data migration is a standard pg_dump/restore.

---

## Version History

| Version | Date       | Change |
|---------|------------|--------|
| 1.0     | 2026-02-27 | Initial decision — accepted (replaces Render/Vercel from intake option matrix) |
