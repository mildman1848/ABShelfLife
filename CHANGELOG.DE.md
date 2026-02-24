# Änderungsprotokoll

> 🇩🇪 **Deutsche Version** | 📖 **[English Version](CHANGELOG.md)**

Alle maßgeblichen Änderungen dieses Projekts werden in dieser Datei dokumentiert.

## [Unveröffentlicht]

### Hinzugefügt
- _Noch keine Einträge._

### Geändert
- _Noch keine Einträge._

### Behoben
- _Noch keine Einträge._

## [0.1.1] - 2026-02-24

### Hinzugefügt
- Manuelle Aktion "Fortschritt aus ABS neu einlesen" in den Sync-Einstellungen.
- Manuelle Aktion "Gesammelte Bibliothek bereinigen" in den Sync-Einstellungen.
- Dedizierte Hadolint-Konfiguration (`.hadolint.yaml`) und Workflow (`.github/workflows/hadolint.yml`) für alle Dockerfiles.
- Repository-weite Single-Container-only-Betriebsart (`abshelflife`) in Compose, Env, Makefile und Workflows.
- GitHub-Community-Standards nach LSIO-`docker-freshrss`: Issue-Templates, PR-Template und Contributing-Guide.
- `greetings.yml`-Workflow für Erstinteraktions-Nachrichten bei Issues/PRs.
- Automatischer `SECURITY.md`-Sync-Workflow (`.github/workflows/security-policy-sync.yml`) auf Basis der `VERSION`.

### Geändert
- Darkmode-Kontrast für Navigation, Karten, Statistik-Widgets und Formulare überarbeitet.
- Kopfzeilen-Titel auf `ABShelfLife` reduziert (ohne Tracker-Zusatz).
- Navigation auf `Startseite`, `Hörbücher`, `Podcasts`, `Einstellungen` reduziert (Verlauf aus dem Top-Menü entfernt).
- Deployment-Defaults setzen nun auf UI-verwaltete ABS-Konten und `targets.json`.
- Docker-Release-Workflow veröffentlicht jetzt nur noch das Single-Image `abshelflife`.
- Docker-Release-Workflow unterstützt jetzt sowohl manuellen Dispatch als auch Tag-Push-Trigger (`v*`).
- CI/Security/Hadolint prüfen nur noch Single-Container-Dockerfiles.
- Make-Defaults nutzen `abshelflife` und nur noch Single-Container-Compose-Flows.
- Legacy-Multi-Container-Services (`abshelflife-db`, `abshelflife-ui`) sowie alte Dockerfiles wurden aus den aktiven Pflegepfaden entfernt.
- Weblate-/Crowdin-Integrationsdateien und alle Verweise darauf wurden aus dem Repository entfernt.
- `permissions.yml` führt nun einen Execute-Permission-Check für Init-/Service-Skripte über den LSIO-Reusable-Workflow aus.
- Die YAML des Sync-Security-Policy-Workflows wurde korrigiert, damit geplante/push-basierte Läufe korrekt starten.

### Behoben
- Verschachteltes Formular in den Sync-Einstellungen beseitigt (`Bearbeitung abbrechen` ohne nested `<form>`).
- Runtime-Sync-Warnung verweist nur noch auf UI-Kontoeinrichtung / `targets.json`.

## [0.1.0] - 2026-02-23

### Hinzugefügt
- LinuxServer-orientierte Repository-Struktur (`Dockerfile`, `Dockerfile.aarch64`, `root/` auf Top-Level).
- Aufgeteilte Doku-Dateien (`README.md`, `README.DE.md`, `CHANGELOG.md`, `CHANGELOG.DE.md`).
- Optionaler History-UI-Service (`ui/abshelflife-ui`) zur Ansicht von Latest/History-Syncdaten.
- Multi-Target-Sync-Basis für mehrere ABS-Server/-User in einem Container.
- Kombiniertes Identitätsmodell in der DB: `target_id + user_id + library_item_id + episode_id`.
- Kanonischer Matching-Key (`ASIN` -> `ISBN` -> `title+author+duration`).
- Zielübergreifende Übernahme von `isFinished` via kanonischem Key und gemeinsamer `principalId`.
- Library-Identity-Index pro Target für Migrationsszenarien.
- Automatisierungs-Basis: `Makefile` und `VERSION`.
- Dependabot-Konfiguration (`.github/dependabot.yml`).
- CI-Workflow (`.github/workflows/ci.yml`).
- Security-Workflow (`.github/workflows/security.yml`).
- Manueller Docker-Publish-Workflow für Docker Hub + GHCR (`.github/workflows/docker-release.yml`).
- Workflow-Permissions-Check (`.github/workflows/permissions.yml`).

### Geändert
- Docker-Compose- und Env-Templates auf Root-Ebene verschoben.
- Sync-Engine unterstützt Target-Profile aus `/config/app/targets.json`.
- Matching-Strategie ist über `ABS_MATCH_PRIORITY` konfigurierbar.

### Behoben
- Atomares Backup-Schreiben (`.tmp` + move).
- Sync-Schema vermeidet Konflikte mit reservierten SQL-Bezeichnern.
