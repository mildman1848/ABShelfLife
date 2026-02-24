# ABShelfLife

English documentation. German version: `README.DE.md`

ABShelfLife is a LinuxServer-style Docker image for persistent Audiobookshelf history tracking.

## Features
- Alpine base image with s6-overlay supervision
- MariaDB persistence in `/config/databases`
- historical tracking tables (`progress_latest`, `progress_history`)
- outbox-based reverse sync (`progress_outbox`) back to ABS
- `FILE__` secrets support
- local mount backups (`/config/backups`)
- multi-target (multi server/user) sync support via UI-managed ABS accounts
- optional read-only ABShelfLife UI (`ui` profile, service `abshelflife-ui`)

## Repository Layout (LSIO-style)
- `Dockerfile`
- `Dockerfile.aarch64`
- `root/`
- `docker-compose.example.yml`
- `.env.example`
- `runtime/` (local dev bind mounts)
- `secrets/` (local dev secret files)
- `ui/abshelflife-ui/` (optional history frontend)

## Quick Start
```bash
cp .env.example .env
printf '%s' 'your-db-password' > secrets/abs_db_password.txt
printf '%s' 'your-root-password' > secrets/mysql_root_password.txt
printf '%s' 'your-ui-token-encryption-key' > secrets/ui_token_encryption_key.txt
docker compose -f docker-compose.example.yml up -d --build
```

## Optional ABShelfLife UI
```bash
docker compose -f docker-compose.example.yml --profile ui up -d --build
```
Open: `http://<host>:8080`

## Automation
- `Makefile` and `VERSION` are included for local build/release routines.
- Dependabot config: `.github/dependabot.yml`
- CI workflow: `.github/workflows/ci.yml`
- Security workflow: `.github/workflows/security.yml`
- Manual Docker publish workflow (Docker Hub + GHCR): `.github/workflows/docker-release.yml`

## Multi-Target (Multiple ABS servers/users)
Use the UI at `Settings` to add one or more ABS accounts (URL, username, token). ABShelfLife writes targets to `ABS_TARGETS_FILE` (`/config/app/targets.json`) automatically.

Manual `targets.json` is still supported and can contain:

```json
[
  {
    "id": "server1-userA",
    "serverId": "server1",
    "principalId": "philipp",
    "url": "http://audiobookshelf-server1:13378",
    "tokenFile": "/run/secrets/server1_userA_token"
  },
  {
    "id": "server2-userA",
    "serverId": "server2",
    "principalId": "philipp",
    "url": "http://audiobookshelf-server2:13378",
    "tokenFile": "/run/secrets/server2_userA_token"
  }
]
```

A sample file is copied automatically to:
- `/config/app/targets.json.example`

Each target equals one ABS user context (one token). This allows one ABShelfLife container to sync many users across one or more ABS servers.

## Matching & Migration Strategy (new ABS server)
- Primary strategy: `ASIN` (recommended)
- Fallbacks: `ISBN`, then normalized `title+author+duration`
- Configurable via `ABS_MATCH_PRIORITY`

How "already listened" migration works:
1. source target reports finished progress
2. ABShelfLife resolves canonical key (ASIN-first)
3. identity index maps canonical key to matching item on destination target
4. outbox queues `isFinished=true` update to destination `/api/me/progress/...`

To improve matching quality:
- Ensure ASIN/ISBN metadata exists in ABS items
- Keep `ABS_ENABLE_LIBRARY_INDEX=1`
- Use same `principalId` for the same real person across servers

## Identity Strategy
- Primary identity is ABS-native IDs + canonical metadata key.
- Conflict-safe key model:
- `target_id + user_id + library_item_id + episode_id`
- Canonical bridge key for cross-target matching (ASIN/ISBN/TAD hash).

## Changelog
- English: `CHANGELOG.md`
- Deutsch: `CHANGELOG.DE.md`
