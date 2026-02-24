# ABShelfLife

Deutsche Dokumentation. Englische Version: `README.md`

ABShelfLife ist ein LinuxServer-orientiertes Docker-Image für persistentes Historien-Tracking in Audiobookshelf.

## Funktionen
- Alpine-Basisimage mit s6-overlay
- MariaDB-Persistenz in `/config/databases`
- Verlaufstabellen (`progress_latest`, `progress_history`)
- Outbox-basierte Rücksynchronisierung nach ABS (`progress_outbox`)
- `FILE__`-Secret-Unterstützung
- lokale Mount-Backups (`/config/backups`)
- Multi-Target (mehrere Server/User) über UI-verwaltete ABS-Konten
- optionales read-only History-UI (Profil `ui`)

## Repository-Struktur (LSIO-Style)
- `Dockerfile`
- `Dockerfile.aarch64`
- `root/`
- `docker-compose.example.yml`
- `.env.example`
- `runtime/` (lokale Dev-Bind-Mounts)
- `secrets/` (lokale Secret-Dateien)
- `ui/abshelflife-ui/` (optionales History-Frontend)

## Schnellstart
```bash
cp .env.example .env
printf '%s' 'dein-db-passwort' > secrets/abs_db_password.txt
printf '%s' 'dein-root-passwort' > secrets/mysql_root_password.txt
printf '%s' 'dein-ui-token-key' > secrets/ui_token_encryption_key.txt
docker compose -f docker-compose.example.yml up -d --build
```

## Optionales History-UI
```bash
docker compose -f docker-compose.example.yml --profile ui up -d --build
```
Aufruf: `http://<host>:8080`

## Automatisierung
- `Makefile` und `VERSION` sind fuer lokale Build/Release-Routinen enthalten.
- Dependabot-Konfiguration: `.github/dependabot.yml`
- CI-Workflow: `.github/workflows/ci.yml`
- Security-Workflow: `.github/workflows/security.yml`
- Manueller Docker-Publish-Workflow (Docker Hub + GHCR): `.github/workflows/docker-release.yml`

## Multi-Target (mehrere ABS-Server/-User)
Füge in der UI unter `Einstellungen` ein oder mehrere ABS-Konten hinzu (URL, Nutzername, Token). ABShelfLife schreibt die Targets automatisch in `ABS_TARGETS_FILE` (`/config/app/targets.json`).

Manuelle `targets.json`-Pflege wird weiterhin unterstützt und nutzt ein JSON-Array mit Targets:

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

Eine Beispiel-Datei wird automatisch nach folgendem Pfad kopiert:
- `/config/app/targets.json.example`

Jedes Target repräsentiert einen ABS-User-Kontext (ein Token). So kann ein einzelner ABShelfLife-Container viele User über einen oder mehrere ABS-Server synchronisieren.

## Matching- und Migrationsstrategie (neuer ABS-Server)
- Primaerstrategie: `ASIN` (empfohlen)
- Fallbacks: `ISBN`, danach normalisiertes `title+author+duration`
- Konfigurierbar ueber `ABS_MATCH_PRIORITY`

So funktioniert die Uebernahme von "bereits gehoert":
1. Source-Target meldet `isFinished=true`
2. ABShelfLife bildet den kanonischen Key (ASIN-first)
3. Identity-Index mappt den Key auf das passende Item im Ziel-Target
4. Outbox queued ein `isFinished=true` Update auf `/api/me/progress/...` im Ziel-ABS

Fuer bessere Match-Qualitaet:
- ASIN/ISBN-Metadaten in ABS gepflegt halten
- `ABS_ENABLE_LIBRARY_INDEX=1` aktiv lassen
- fuer dieselbe Person serveruebergreifend dieselbe `principalId` verwenden

## Identitaetsstrategie
- Primaere Identitaet sind ABS-native IDs plus kanonischer Metadaten-Key.
- Konfliktfreies Schluesselmodell:
- `target_id + user_id + library_item_id + episode_id`
- Kanonischer Bruecken-Key fuer Cross-Target-Matching (ASIN/ISBN/TAD-Hash).

## Changelog
- Englisch: `CHANGELOG.md`
- Deutsch: `CHANGELOG.DE.md`
