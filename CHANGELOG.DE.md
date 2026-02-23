# Aenderungsprotokoll

Alle relevanten Aenderungen dieses Projekts werden in dieser Datei dokumentiert.

## [Unveroeffentlicht]

### Hinzugefuegt
- Manuelle Aktion "Fortschritt aus ABS neu einlesen" in den Sync-Einstellungen.
- Manuelle Aktion "Gesammelte Bibliothek bereinigen" in den Sync-Einstellungen.

### Geaendert
- Darkmode-Kontrast fuer Navigation, Karten, Statistik-Widgets und Formulare ueberarbeitet.
- Kopfzeilen-Titel auf `ABShelfLife` reduziert (ohne Tracker-Zusatz).
- Navigation auf `Startseite`, `Hoerbuecher`, `Podcasts`, `Einstellungen` reduziert (Verlauf aus dem Top-Menue entfernt).
- Deployment-Defaults setzen nun auf UI-verwaltete ABS-Konten und `targets.json`.

### Behoben
- Verschachteltes Formular in den Sync-Einstellungen beseitigt (`Bearbeitung abbrechen` ohne nested `<form>`).
- Runtime-Sync-Warnung verweist nur noch auf UI-Kontoeinrichtung / `targets.json`.

## [0.1.0] - 2026-02-23

### Hinzugefuegt
- LinuxServer-orientierte Repository-Struktur (`Dockerfile`, `Dockerfile.aarch64`, `root/` auf Top-Level).
- Aufgeteilte Doku-Dateien (`README.md`, `README.DE.md`, `CHANGELOG.md`, `CHANGELOG.DE.md`).
- Optionaler History-UI-Service (`ui/history-ui`) zur Ansicht von Latest/History-Syncdaten.
- Multi-Target-Sync-Basis fuer mehrere ABS-Server/-User in einem Container.
- Kombiniertes Identitaetsmodell in der DB: `target_id + user_id + library_item_id + episode_id`.
- Kanonischer Matching-Key (`ASIN` -> `ISBN` -> `title+author+duration`).
- Zieluebergreifende Uebernahme von `isFinished` via kanonischem Key und gemeinsamer `principalId`.
- Library-Identity-Index pro Target fuer Migrationsszenarien.
- Automatisierungs-Basis: `Makefile` und `VERSION`.
- Dependabot-Konfiguration (`.github/dependabot.yml`).
- CI-Workflow (`.github/workflows/ci.yml`).
- Security-Workflow (`.github/workflows/security.yml`).
- Manueller Docker-Publish-Workflow fuer Docker Hub + GHCR (`.github/workflows/docker-release.yml`).
- Workflow-Permissions-Check (`.github/workflows/permissions.yml`).

### Geaendert
- Docker-Compose- und Env-Templates auf Root-Ebene verschoben.
- Sync-Engine unterstuetzt Target-Profile aus `/config/app/targets.json`.
- Matching-Strategie ist ueber `ABS_MATCH_PRIORITY` konfigurierbar.

### Behoben
- Atomares Backup-Schreiben (`.tmp` + move).
- Sync-Schema vermeidet Konflikte mit reservierten SQL-Bezeichnern.
