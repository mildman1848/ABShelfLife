import base64
import hashlib
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import wraps
from typing import Any
from urllib.parse import quote, urlparse

import pymysql
import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, Response, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("UI_SECRET_KEY", "change-me-in-production")

SCHEMA_READY = False

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "nav.dashboard": "Home",
        "nav.sync": "Settings",
        "nav.history": "History",
        "nav.audiobooks": "Audiobooks",
        "nav.podcasts": "Podcasts",
        "nav.logout": "Logout",
        "dashboard.title": "Home",
        "dashboard.subtitle": "Track audiobooks and podcasts across ABS.",
        "stats.not_started": "Not Started",
        "stats.in_progress": "In Progress",
        "stats.completed": "Completed",
        "stats.paused": "Paused",
        "stats.dropped": "Dropped",
        "stats.accounts": "ABS Accounts",
        "stats.synced_rows": "Synced Rows",
        "stats.audiobooks": "Audiobooks",
        "stats.podcast_episodes": "Podcast Episodes",
        "section.tracked": "Tracked Audiobooks",
        "section.search": "Find Audiobooks",
        "section.sync_latest": "Latest Synced Progress",
        "section.collected": "Collected Audiobooks",
        "section.audiobooks": "Audiobooks",
        "section.podcasts": "Podcasts",
        "section.home_continue": "Continue Listening",
        "section.home_series_next": "Next in Series",
        "section.home_podcasts_next": "Next Podcast Episode",
        "section.home_completed": "Recently Completed",
        "section.home_collected": "New in Collection",
        "section.home_podcasts": "Podcast Suggestions",
        "section.podcast_episodes": "Tracked Podcast Episodes",
        "section.sync_settings": "Sync Settings",
        "section.sync_accounts": "ABS Accounts",
        "section.matching": "Manual Matching",
        "field.title": "Title",
        "field.author": "Author",
        "field.series": "Series",
        "field.year": "Year",
        "field.asin": "ASIN",
        "field.cover": "Cover",
        "field.episode": "Episode",
        "field.published": "Published",
        "field.collected": "Collected",
        "field.collection_status": "Collection",
        "field.listening_status": "Listening",
        "field.progress": "Progress",
        "field.status": "Status",
        "field.abs_presence": "ABS",
        "collection.collected": "Collected",
        "collection.missing": "Missing",
        "presence.present": "Present",
        "presence.missing": "Missing",
        "status.not_started": "Not Started",
        "status.in_progress": "In Progress",
        "status.completed": "Completed",
        "status.unknown": "Unknown",
        "action.mark_heard": "Mark as Heard",
        "action.mark_unheard": "Mark as Unheard",
        "action.open_itunes": "Open iTunes",
        "action.save": "Save",
        "action.save_interval": "Save Interval",
        "action.run_sync_now": "Run Sync Now",
        "action.import_collected": "Import Collected Audiobooks",
        "action.import_podcasts": "Import Podcasts (ABS + iTunes)",
        "action.rebuild_progress": "Rebuild Progress from ABS",
        "action.cleanup_collected": "Clean Collected Library",
        "action.edit": "Edit",
        "action.delete": "Delete",
        "action.cancel_edit": "Cancel Edit",
        "action.show_unheard": "Only Unheard",
        "action.show_all_episodes": "Show All",
        "action.open_abs": "Open in ABS",
        "action.open_matching": "Open Matching",
        "action.match_now": "Match Now",
        "sync.subtitle": "Manage ABS servers and users. Settings are written to targets.json.",
        "sync.interval": "Sync interval (seconds)",
        "sync.account_form_add": "Add ABS Account",
        "sync.account_form_edit": "Edit ABS Account",
        "sync.account_name": "Account Name",
        "sync.abs_url": "ABS URL",
        "sync.abs_username": "ABS Username",
        "sync.api_token": "API Token",
        "sync.api_token_help": "Required for new account, optional for updates",
        "sync.enabled": "Enabled",
        "sync.target_id": "Target ID (optional)",
        "sync.server_id": "Server ID (optional)",
        "sync.principal_id": "Principal ID (optional)",
        "sync.configured_accounts": "Configured Accounts",
        "sync.table_name": "Name",
        "sync.table_url": "URL",
        "sync.table_user": "User",
        "sync.table_target": "Target",
        "sync.table_enabled": "Enabled",
        "sync.table_updated": "Updated",
        "sync.table_actions": "Actions",
        "history.title": "History",
        "podcast.next_episode": "Next Episode",
        "podcast.all_done": "All episodes completed",
        "podcast.open": "Open Podcast",
        "podcast.episodes": "Episodes",
        "podcast.overview": "Podcast Overview",
        "podcast.back": "Back to Podcasts",
        "matching.subtitle": "Match unmatched audiobooks across ABS targets using a shared canonical identity.",
        "matching.source_item": "Unmatched Source",
        "matching.reference_item": "Reference Item",
        "matching.unmatched": "Unmatched Audiobooks",
        "matching.abs_links": "Unmatched ABS Links",
        "message.no_unmatched": "No unmatched audiobooks found.",
        "message.no_collected": "No collected audiobooks yet. Use Sync Setup -> Import Collected Audiobooks.",
        "message.no_podcasts": "No podcasts imported yet. Use Sync Setup -> Import Podcasts (ABS + iTunes).",
        "message.no_podcast_episodes": "No podcast episodes imported yet.",
        "common.none": "-",
        "common.yes": "Yes",
        "common.no": "No",
        "common.language": "Language",
    },
    "de": {
        "nav.dashboard": "Startseite",
        "nav.sync": "Einstellungen",
        "nav.history": "Verlauf",
        "nav.audiobooks": "Hörbücher",
        "nav.podcasts": "Podcasts",
        "nav.logout": "Abmelden",
        "dashboard.title": "Startseite",
        "dashboard.subtitle": "Hörbücher und Podcasts über ABS hinweg tracken.",
        "stats.not_started": "Nicht begonnen",
        "stats.in_progress": "In Bearbeitung",
        "stats.completed": "Abgeschlossen",
        "stats.paused": "Pausiert",
        "stats.dropped": "Abgebrochen",
        "stats.accounts": "ABS-Konten",
        "stats.synced_rows": "Synchronisierte Einträge",
        "stats.audiobooks": "Hörbücher",
        "stats.podcast_episodes": "Podcast-Folgen",
        "section.tracked": "Getrackte Hörbücher",
        "section.search": "Hörbücher suchen",
        "section.sync_latest": "Zuletzt synchronisierter Fortschritt",
        "section.collected": "Gesammelte Hörbücher",
        "section.audiobooks": "Hörbücher",
        "section.podcasts": "Podcasts",
        "section.home_continue": "Weiterhören",
        "section.home_series_next": "Nächstes in der Serie",
        "section.home_podcasts_next": "Nächste Podcast-Folge",
        "section.home_completed": "Kürzlich abgeschlossen",
        "section.home_collected": "Neu in der Sammlung",
        "section.home_podcasts": "Podcast-Empfehlungen",
        "section.podcast_episodes": "Getrackte Podcast-Folgen",
        "section.sync_settings": "Synchronisation",
        "section.sync_accounts": "ABS-Konten",
        "section.matching": "Manuelles Matching",
        "field.title": "Titel",
        "field.author": "Autor",
        "field.series": "Serie",
        "field.year": "Jahr",
        "field.asin": "ASIN",
        "field.cover": "Cover",
        "field.episode": "Folge",
        "field.published": "Veröffentlicht",
        "field.collected": "Gesammelt",
        "field.collection_status": "Sammlung",
        "field.listening_status": "Hörstatus",
        "field.progress": "Fortschritt",
        "field.status": "Status",
        "field.abs_presence": "ABS",
        "collection.collected": "Gesammelt",
        "collection.missing": "Fehlend",
        "presence.present": "Vorhanden",
        "presence.missing": "Fehlend",
        "status.not_started": "Nicht begonnen",
        "status.in_progress": "In Bearbeitung",
        "status.completed": "Abgeschlossen",
        "status.unknown": "Unbekannt",
        "action.mark_heard": "Als gehört markieren",
        "action.mark_unheard": "Als ungehört markieren",
        "action.open_itunes": "iTunes öffnen",
        "action.save": "Speichern",
        "action.save_interval": "Intervall speichern",
        "action.run_sync_now": "Sync jetzt ausführen",
        "action.import_collected": "Gesammelte Hörbücher importieren",
        "action.import_podcasts": "Podcasts importieren (ABS + iTunes)",
        "action.rebuild_progress": "Fortschritt aus ABS neu einlesen",
        "action.cleanup_collected": "Gesammelte Bibliothek bereinigen",
        "action.edit": "Bearbeiten",
        "action.delete": "Löschen",
        "action.cancel_edit": "Bearbeitung abbrechen",
        "action.show_unheard": "Nur ungehörte",
        "action.show_all_episodes": "Alle anzeigen",
        "action.open_abs": "In ABS öffnen",
        "action.open_matching": "Matching öffnen",
        "action.match_now": "Jetzt matchen",
        "sync.subtitle": "ABS-Server und Nutzer verwalten. Die Einstellungen werden in targets.json geschrieben.",
        "sync.interval": "Sync-Intervall (Sekunden)",
        "sync.account_form_add": "ABS-Konto hinzufügen",
        "sync.account_form_edit": "ABS-Konto bearbeiten",
        "sync.account_name": "Kontoname",
        "sync.abs_url": "ABS-URL",
        "sync.abs_username": "ABS-Benutzername",
        "sync.api_token": "API-Token",
        "sync.api_token_help": "Für neue Konten erforderlich, bei Updates optional",
        "sync.enabled": "Aktiv",
        "sync.target_id": "Target-ID (optional)",
        "sync.server_id": "Server-ID (optional)",
        "sync.principal_id": "Principal-ID (optional)",
        "sync.configured_accounts": "Eingerichtete Konten",
        "sync.table_name": "Name",
        "sync.table_url": "URL",
        "sync.table_user": "Nutzer",
        "sync.table_target": "Target",
        "sync.table_enabled": "Aktiv",
        "sync.table_updated": "Aktualisiert",
        "sync.table_actions": "Aktionen",
        "history.title": "Verlauf",
        "podcast.next_episode": "Nächste Folge",
        "podcast.all_done": "Alle Folgen abgeschlossen",
        "podcast.open": "Podcast öffnen",
        "podcast.episodes": "Folgen",
        "podcast.overview": "Podcast-Übersicht",
        "podcast.back": "Zurück zu Podcasts",
        "matching.subtitle": "Ordne ungematchte Hörbücher über ABS-Targets mithilfe einer gemeinsamen kanonischen Identität zu.",
        "matching.source_item": "Ungematchte Quelle",
        "matching.reference_item": "Referenz-Element",
        "matching.unmatched": "Ungematchte Hörbücher",
        "matching.abs_links": "Ungematchte ABS-Links",
        "message.no_unmatched": "Keine ungematchten Hörbücher gefunden.",
        "message.no_collected": "Noch keine gesammelten Hörbücher. Nutze Sync-Einrichtung -> Gesammelte Hörbücher importieren.",
        "message.no_podcasts": "Noch keine Podcasts importiert. Nutze Sync-Einrichtung -> Podcasts importieren (ABS + iTunes).",
        "message.no_podcast_episodes": "Noch keine Podcast-Folgen importiert.",
        "common.none": "-",
        "common.yes": "Ja",
        "common.no": "Nein",
        "common.language": "Sprache",
    },
}


def get_db_password() -> str:
    pwd = os.getenv("DB_PASSWORD", "")
    if pwd:
        return pwd
    pwd_file = os.getenv("DB_PASSWORD_FILE", "")
    if pwd_file and os.path.isfile(pwd_file):
        with open(pwd_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "abshelflife-db"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "abshelflife"),
        password=get_db_password(),
        database=os.getenv("DB_NAME", "abshelflife"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def get_lang() -> str:
    requested = (request.args.get("lang") or "").strip().lower()
    if requested in ("en", "de"):
        session["lang"] = requested
        return requested
    stored = (session.get("lang") or "").strip().lower()
    if stored in ("en", "de"):
        return stored
    return "en"


def t(key: str) -> str:
    lang = getattr(g, "lang", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)


@app.context_processor
def inject_i18n() -> dict[str, Any]:
    return {"t": t, "lang": getattr(g, "lang", "en")}


def _get_crypto_material() -> str:
    inline = os.getenv("UI_TOKEN_ENCRYPTION_KEY", "").strip()
    if inline:
        return inline

    key_file = os.getenv("UI_TOKEN_ENCRYPTION_KEY_FILE", "")
    if key_file and os.path.isfile(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            data = f.read().strip()
            if data:
                return data

    return app.secret_key


def _build_fernet() -> Fernet:
    raw = _get_crypto_material().encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_token(token: str) -> str:
    return _build_fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(token_enc: str) -> str:
    if not token_enc:
        return ""
    try:
        return _build_fernet().decrypt(token_enc.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def ensure_ui_schema() -> None:
    global SCHEMA_READY
    if SCHEMA_READY:
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_users (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  username VARCHAR(128) NOT NULL,
                  password_hash VARCHAR(255) NOT NULL,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  last_login_at TIMESTAMP NULL,
                  PRIMARY KEY(id),
                  UNIQUE KEY uq_ui_users_username (username)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_user_settings (
                  user_id BIGINT NOT NULL,
                  sync_interval_seconds INT NOT NULL DEFAULT 300,
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY(user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_sync_accounts (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  owner_user_id BIGINT NOT NULL,
                  account_name VARCHAR(128) NOT NULL,
                  abs_url VARCHAR(512) NOT NULL,
                  abs_username VARCHAR(128) NOT NULL,
                  api_token TEXT NULL,
                  api_token_enc TEXT NULL,
                  target_id VARCHAR(128) NULL,
                  server_id VARCHAR(128) NULL,
                  principal_id VARCHAR(128) NULL,
                  enabled TINYINT(1) NOT NULL DEFAULT 1,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY(id),
                  UNIQUE KEY uq_ui_sync_accounts_user_name (owner_user_id, account_name),
                  KEY idx_ui_sync_accounts_enabled (enabled)
                )
                """
            )
            try:
                cur.execute("ALTER TABLE ui_sync_accounts ADD COLUMN api_token_enc TEXT NULL")
            except Exception:
                pass
            # Backward compatibility: ensure all rows have a usable account_name
            # even when the UI no longer exposes this field.
            cur.execute(
                """
                SELECT id, owner_user_id, abs_url, abs_username, account_name
                FROM ui_sync_accounts
                """
            )
            for row in cur.fetchall():
                current_name = str(row.get("account_name") or "").strip()
                if current_name:
                    continue
                owner_user_id = int(row.get("owner_user_id") or 0)
                account_id = int(row.get("id") or 0)
                base_name = derive_account_name(str(row.get("abs_url") or ""), str(row.get("abs_username") or ""))
                fixed_name = ensure_unique_account_name(cur, owner_user_id, base_name, account_id)
                cur.execute(
                    "UPDATE ui_sync_accounts SET account_name=%s WHERE id=%s",
                    (fixed_name, account_id),
                )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_tracked_books (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  owner_user_id BIGINT NOT NULL,
                  title VARCHAR(512) NOT NULL,
                  author VARCHAR(512) NULL,
                  asin VARCHAR(32) NULL,
                  isbn VARCHAR(32) NULL,
                  series_name VARCHAR(256) NULL,
                  series_index DECIMAL(6,2) NULL,
                  status ENUM('planned','in_progress','heard') NOT NULL DEFAULT 'planned',
                  progress DECIMAL(6,3) NOT NULL DEFAULT 0,
                  metadata_source VARCHAR(32) NOT NULL DEFAULT 'manual',
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY(id),
                  UNIQUE KEY uq_ui_tracked_books_identity (owner_user_id, asin, isbn, title(191)),
                  KEY idx_ui_tracked_books_series (owner_user_id, series_name, series_index),
                  KEY idx_ui_tracked_books_status (owner_user_id, status)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_runtime_settings (
                  setting_key VARCHAR(64) NOT NULL,
                  setting_value VARCHAR(255) NOT NULL,
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY(setting_key)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_collected_items (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  owner_user_id BIGINT NOT NULL,
                  target_id VARCHAR(128) NOT NULL,
                  library_item_id VARCHAR(64) NOT NULL,
                  media_type VARCHAR(32) NOT NULL DEFAULT 'book',
                  title VARCHAR(512) NOT NULL,
                  author VARCHAR(512) NULL,
                  series_name VARCHAR(512) NULL,
                  published_year INT NULL,
                  asin VARCHAR(64) NULL,
                  cover_url TEXT NULL,
                  collection_status ENUM('collected','missing') NOT NULL DEFAULT 'collected',
                  source VARCHAR(32) NOT NULL DEFAULT 'abs',
                  collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY(id),
                  UNIQUE KEY uq_ui_collected_items (owner_user_id, target_id, library_item_id),
                  KEY idx_ui_collected_owner (owner_user_id, media_type)
                )
                """
            )
            try:
                cur.execute(
                    "ALTER TABLE ui_collected_items ADD COLUMN collection_status ENUM('collected','missing') NOT NULL DEFAULT 'collected'"
                )
            except Exception:
                pass
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_podcast_shows (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  owner_user_id BIGINT NOT NULL,
                  target_id VARCHAR(128) NOT NULL,
                  library_item_id VARCHAR(64) NOT NULL,
                  title VARCHAR(512) NOT NULL,
                  author VARCHAR(512) NULL,
                  feed_url TEXT NULL,
                  image_url TEXT NULL,
                  itunes_id VARCHAR(64) NULL,
                  itunes_page_url TEXT NULL,
                  release_date VARCHAR(64) NULL,
                  language VARCHAR(32) NULL,
                  source VARCHAR(32) NOT NULL DEFAULT 'abs',
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY(id),
                  UNIQUE KEY uq_ui_podcast_shows (owner_user_id, target_id, library_item_id),
                  KEY idx_ui_podcast_owner (owner_user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_podcast_episodes (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  owner_user_id BIGINT NOT NULL,
                  target_id VARCHAR(128) NOT NULL,
                  library_item_id VARCHAR(64) NOT NULL,
                  episode_id VARCHAR(64) NOT NULL,
                  abs_episode_id VARCHAR(64) NULL,
                  abs_presence ENUM('present','missing') NOT NULL DEFAULT 'missing',
                  podcast_title VARCHAR(512) NOT NULL,
                  episode_title VARCHAR(512) NOT NULL,
                  author VARCHAR(512) NULL,
                  published_at VARCHAR(64) NULL,
                  duration_sec DOUBLE NULL,
                  image_url TEXT NULL,
                  source VARCHAR(32) NOT NULL DEFAULT 'abs',
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY(id),
                  UNIQUE KEY uq_ui_podcast_episodes (owner_user_id, target_id, library_item_id, episode_id),
                  KEY idx_ui_podcast_episodes_owner (owner_user_id, target_id)
                )
                """
            )
            try:
                cur.execute("ALTER TABLE ui_podcast_episodes ADD COLUMN abs_episode_id VARCHAR(64) NULL")
            except Exception:
                pass
            try:
                cur.execute(
                    "ALTER TABLE ui_podcast_episodes ADD COLUMN abs_presence ENUM('present','missing') NOT NULL DEFAULT 'missing'"
                )
            except Exception:
                pass

            # Migrate plain-text tokens once to encrypted storage.
            cur.execute(
                """
                SELECT id, api_token
                FROM ui_sync_accounts
                WHERE (api_token_enc IS NULL OR api_token_enc = '')
                  AND api_token IS NOT NULL
                  AND api_token <> ''
                """
            )
            for row in cur.fetchall():
                token_enc = encrypt_token(str(row["api_token"]))
                cur.execute(
                    "UPDATE ui_sync_accounts SET api_token_enc = %s, api_token = '' WHERE id = %s",
                    (token_enc, int(row["id"])),
                )

    SCHEMA_READY = True


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def current_user() -> dict[str, Any] | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username FROM ui_users WHERE id = %s", (user_id,))
            return cur.fetchone()


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def derive_account_name(abs_url: str, abs_username: str) -> str:
    parsed = urlparse(abs_url if "://" in abs_url else f"http://{abs_url}")
    host = (parsed.netloc or parsed.path or "abs").strip().lower()
    user = (abs_username or "user").strip().lower()
    base = f"{user}@{host}"
    base = re.sub(r"[^a-z0-9@._:-]+", "-", base).strip("-")
    return base or "abs-account"


def ensure_unique_account_name(cur: Any, owner_user_id: int, base_name: str, exclude_id: int | None = None) -> str:
    candidate = (base_name or "abs-account").strip() or "abs-account"
    suffix = 1
    while True:
        if exclude_id and exclude_id > 0:
            cur.execute(
                """
                SELECT 1
                FROM ui_sync_accounts
                WHERE owner_user_id = %s
                  AND account_name = %s
                  AND id <> %s
                LIMIT 1
                """,
                (owner_user_id, candidate, exclude_id),
            )
        else:
            cur.execute(
                """
                SELECT 1
                FROM ui_sync_accounts
                WHERE owner_user_id = %s
                  AND account_name = %s
                LIMIT 1
                """,
                (owner_user_id, candidate),
            )
        if not cur.fetchone():
            return candidate
        suffix += 1
        candidate = f"{base_name}-{suffix}"


def resolve_target_id(row: dict[str, Any]) -> str:
    explicit = (row.get("target_id") or "").strip()
    if explicit:
        return explicit
    return f"u{row['owner_user_id']}-a{row['id']}"


def write_targets_file() -> None:
    targets_file = os.getenv("TARGETS_FILE", "/config/app/targets.json")
    targets_dir = os.path.dirname(targets_file)
    if targets_dir:
        os.makedirs(targets_dir, exist_ok=True)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, owner_user_id, abs_url, api_token, api_token_enc, target_id, server_id, principal_id
                FROM ui_sync_accounts
                WHERE enabled = 1
                ORDER BY owner_user_id, id
                """
            )
            rows = cur.fetchall()
            cur.execute(
                """
                SELECT owner_user_id, target_id
                FROM ui_collected_items
                WHERE target_id IS NOT NULL AND target_id <> ''
                GROUP BY owner_user_id, target_id
                """
            )
            collected_target_rows = cur.fetchall()

    owner_account_count: dict[int, int] = {}
    owner_alias_targets: dict[int, list[str]] = {}
    for row in rows:
        owner = int(row.get("owner_user_id") or 0)
        owner_account_count[owner] = owner_account_count.get(owner, 0) + 1

    for row in collected_target_rows:
        owner = int(row.get("owner_user_id") or 0)
        tid = str(row.get("target_id") or "").strip()
        if owner <= 0 or not tid:
            continue
        owner_alias_targets.setdefault(owner, []).append(tid)

    payload_map: dict[str, dict[str, str]] = {}
    for row in rows:
        token_enc = str(row.get("api_token_enc") or "")
        token = decrypt_token(token_enc)
        if not token:
            token = str(row.get("api_token") or "").strip()
        if not token:
            continue

        target_id = resolve_target_id(row)
        server_id = (row.get("server_id") or "").strip() or target_id
        principal_id = (row.get("principal_id") or "").strip() or target_id
        base_url = normalize_url(str(row.get("abs_url") or ""))

        payload_map[target_id] = {
            "id": target_id,
            "serverId": server_id,
            "principalId": principal_id,
            "url": base_url,
            "token": token,
        }

        explicit_target = (row.get("target_id") or "").strip()
        owner_user_id = int(row.get("owner_user_id") or 0)
        # Backward compatibility: older rows may still reference previous implicit target IDs.
        if not explicit_target and owner_account_count.get(owner_user_id, 0) == 1:
            for alias_tid in owner_alias_targets.get(owner_user_id, []):
                alias_tid = alias_tid.strip()
                if not alias_tid or alias_tid == target_id:
                    continue
                if alias_tid in payload_map:
                    continue
                payload_map[alias_tid] = {
                    "id": alias_tid,
                    "serverId": server_id,
                    "principalId": principal_id,
                    "url": base_url,
                    "token": token,
                }

    payload = list(payload_map.values())

    with open(targets_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def recalc_global_sync_interval() -> int:
    fallback = int(os.getenv("ABS_SYNC_INTERVAL_SECONDS_DEFAULT", "300"))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MIN(sync_interval_seconds) AS min_interval FROM ui_user_settings WHERE sync_interval_seconds > 0"
            )
            row = cur.fetchone() or {}
            min_interval = int(row.get("min_interval") or 0)
            final_interval = min_interval if min_interval > 0 else fallback
            cur.execute(
                """
                INSERT INTO ui_runtime_settings (setting_key, setting_value)
                VALUES ('sync_interval_seconds', %s)
                ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
                """,
                (str(final_interval),),
            )
            return final_interval


def request_manual_sync() -> None:
    trigger_file = os.getenv("MANUAL_SYNC_TRIGGER_FILE", "/config/app/run-now.trigger")
    trigger_dir = os.path.dirname(trigger_file)
    if trigger_dir:
        os.makedirs(trigger_dir, exist_ok=True)
    with open(trigger_file, "w", encoding="utf-8") as f:
        f.write(str(int(time.time())))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ui_runtime_settings (setting_key, setting_value)
                VALUES ('manual_sync_requested_at', %s)
                ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
                """,
                (str(int(time.time())),),
            )


def get_user_target_credentials(owner_user_id: int) -> dict[str, dict[str, str]]:
    creds: dict[str, dict[str, str]] = {}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, target_id, abs_url, api_token, api_token_enc
                FROM ui_sync_accounts
                WHERE owner_user_id = %s
                  AND enabled = 1
                """,
                (owner_user_id,),
            )
            rows = cur.fetchall()
            for row in rows:
                tid = (row.get("target_id") or f"u{owner_user_id}-a{row['id']}").strip()
                token = decrypt_token(str(row.get("api_token_enc") or "")) or str(row.get("api_token") or "").strip()
                if tid and token:
                    creds[tid] = {"url": normalize_url(str(row.get("abs_url") or "")), "token": token}
    return creds


def get_user_target_urls(owner_user_id: int) -> dict[str, str]:
    urls: dict[str, str] = {}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, target_id, abs_url
                FROM ui_sync_accounts
                WHERE owner_user_id = %s
                """,
                (owner_user_id,),
            )
            for row in cur.fetchall():
                tid = (row.get("target_id") or f"u{owner_user_id}-a{row['id']}").strip()
                if tid:
                    urls[tid] = normalize_url(str(row.get("abs_url") or ""))
    return urls


def abs_get_json(base_url: str, token: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = requests.get(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def abs_get_optional_json(base_url: str, token: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    try:
        return abs_get_json(base_url, token, path, params)
    except requests.HTTPError as exc:
        status = int(getattr(getattr(exc, "response", None), "status_code", 0) or 0)
        if status in (400, 401, 403, 404):
            return None
        raise
    except Exception:
        return None


def abs_post_optional_json(
    base_url: str,
    token: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    try:
        resp = requests.post(
            f"{base_url}{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload or {},
            timeout=20,
        )
        if resp.status_code >= 400:
            return None
        if not resp.text:
            return {}
        return resp.json()
    except Exception:
        return None


def build_abs_web_item_url(base_url: str, library_item_id: str) -> str:
    root = normalize_url(base_url)
    item_id = (library_item_id or "").strip()
    if not root or not item_id:
        return ""
    query = "autoplay=1&play=1&start=1"
    prefix = root if root.endswith("/audiobookshelf") else f"{root}/audiobookshelf"
    return f"{prefix}/item/{item_id}?{query}"


def append_query_param(url: str, key: str, value: str) -> str:
    if not url:
        return ""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{key}={quote(str(value), safe='')}"


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value))
    except Exception:
        return default


def parse_episode_number(text: str) -> int | None:
    raw = (text or "").strip()
    if not raw:
        return None
    patterns = [
        r"\bS\d{1,2}E(\d{1,4})\b",
        r"\b(?:episode|ep|folge)\s*#?\s*(\d{1,4})\b",
        r"^\s*(\d{1,4})\s*[-.:]",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            number = int(match.group(1))
            if number > 0:
                return number
        except Exception:
            continue
    return None


def normalize_series_group_name(series_name: str) -> str:
    raw = (series_name or "").strip()
    if not raw:
        return ""
    # Common ABS/Audible patterns: "Auris #1", "Saga, Book 2", "Serie 3"
    normalized = re.sub(r"\s*[#]\s*\d+\s*$", "", raw, flags=re.IGNORECASE)
    normalized = re.sub(r"\s*[,:\-]?\s*(book|band|teil|volume|vol|folge)\s*\d+\s*$", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or raw


def parse_published_timestamp(value: str) -> float:
    raw = (value or "").strip()
    if not raw:
        return float("inf")
    try:
        iso = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        pass
    try:
        dt2 = parsedate_to_datetime(raw)
        if dt2.tzinfo is None:
            dt2 = dt2.replace(tzinfo=timezone.utc)
        return dt2.timestamp()
    except Exception:
        return float("inf")


def podcast_episode_sort_key(episode_title: str, published_at: str) -> tuple[int, int, float, str]:
    episode_no = parse_episode_number(episode_title)
    published_ts = parse_published_timestamp(published_at)
    title_norm = (episode_title or "").strip().lower()
    if episode_no is not None:
        return (0, episode_no, published_ts, title_norm)
    return (1, 10**9, published_ts, title_norm)


def build_canonical_key(asin: str, isbn: str, title: str, author: str, duration: float) -> str:
    asin_norm = "".join(ch for ch in (asin or "").strip().upper() if ch.isalnum())
    isbn_norm = "".join(ch for ch in (isbn or "").strip().upper() if ch.isalnum())
    if asin_norm:
        return f"asin:{asin_norm}"
    if isbn_norm:
        return f"isbn:{isbn_norm}"
    base = f"{(title or '').strip().lower()}|{(author or '').strip().lower()}|{int(duration or 0)}"
    return f"tad:{hashlib.sha1(base.encode('utf-8')).hexdigest()}"


def itunes_lookup_podcast(title: str, author: str) -> dict[str, str]:
    query = " ".join([title or "", author or ""]).strip()
    if not query:
        return {}
    try:
        resp = requests.get(
            "https://itunes.apple.com/search",
            params={"term": query, "media": "podcast", "entity": "podcast", "limit": 1},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return {}
        hit = results[0]
        return {
            "itunes_id": str(hit.get("collectionId") or ""),
            "itunes_page_url": str(hit.get("collectionViewUrl") or ""),
            "image_url": str(hit.get("artworkUrl600") or hit.get("artworkUrl100") or ""),
            "feed_url": str(hit.get("feedUrl") or ""),
        }
    except Exception:
        return {}


def normalize_text_key(value: str) -> str:
    cleaned = (value or "").strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def parse_feed_podcast_episodes(feed_url: str, fallback_title: str, fallback_author: str) -> list[dict[str, Any]]:
    if not feed_url:
        return []
    try:
        resp = requests.get(feed_url, timeout=25)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception:
        return []

    entries = root.findall(".//item")
    if not entries:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    episodes: list[dict[str, Any]] = []
    for idx, item in enumerate(entries, start=1):
        def _txt(path: str) -> str:
            elem = item.find(path)
            return (elem.text or "").strip() if elem is not None and elem.text else ""

        title = _txt("title") or _txt("{http://www.w3.org/2005/Atom}title") or f"Episode {idx}"
        guid = _txt("guid") or _txt("{http://www.w3.org/2005/Atom}id")
        pub = _txt("pubDate") or _txt("{http://purl.org/dc/elements/1.1/}date") or _txt("{http://www.w3.org/2005/Atom}published")
        author = _txt("{http://www.itunes.com/dtds/podcast-1.0.dtd}author") or _txt("author") or fallback_author
        duration_raw = _txt("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration")
        duration_sec = 0.0
        if duration_raw:
            if ":" in duration_raw:
                parts = [p for p in duration_raw.split(":") if p.isdigit()]
                try:
                    if len(parts) == 3:
                        duration_sec = float(int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))
                    elif len(parts) == 2:
                        duration_sec = float(int(parts[0]) * 60 + int(parts[1]))
                except Exception:
                    duration_sec = 0.0
            elif duration_raw.isdigit():
                duration_sec = float(duration_raw)

        image_url = ""
        img = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
        if img is not None:
            image_url = (img.attrib.get("href") or "").strip()
        if not image_url:
            enc = item.find("enclosure")
            if enc is not None:
                image_url = (enc.attrib.get("url") or "").strip()

        external_id = guid or f"itunes:{hashlib.sha1((title + '|' + pub).encode('utf-8')).hexdigest()}"
        episodes.append(
            {
                "external_id": external_id[:64],
                "title": title,
                "published_at": pub,
                "author": author or fallback_author,
                "duration_sec": duration_sec if duration_sec > 0 else None,
                "image_url": image_url,
                "podcast_title": fallback_title,
            }
        )
    return episodes


def match_abs_episode(itunes_ep: dict[str, Any], abs_episodes: list[dict[str, Any]]) -> str | None:
    it_title = normalize_text_key(str(itunes_ep.get("title") or ""))
    it_pub = str(itunes_ep.get("published_at") or "")[:16]
    if not abs_episodes:
        return None
    for ep in abs_episodes:
        if normalize_text_key(str(ep.get("title") or "")) == it_title and it_title:
            return str(ep.get("id") or "") or None
    if it_pub:
        for ep in abs_episodes:
            if str(ep.get("pub") or "")[:16] == it_pub:
                return str(ep.get("id") or "") or None
    return None


def audible_podcast_fallback_episodes(title: str, author: str, limit: int = 50) -> list[dict[str, Any]]:
    query = " ".join([title or "", author or ""]).strip()
    if not query:
        return []

    base_url = os.getenv("AUDIBLE_API_BASE_URL", "https://api.audible.com").rstrip("/")
    bearer = os.getenv("AUDIBLE_API_BEARER_TOKEN", "").strip()
    marketplace = os.getenv("AUDIBLE_MARKETPLACE", "us").strip()
    if not bearer:
        return []

    try:
        response = requests.get(
            f"{base_url}/1.0/catalog/products",
            params={
                "num_results": limit,
                "keywords": query,
                "response_groups": "product_desc,contributors,product_attrs,media,series",
                "marketplace": marketplace,
            },
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=18,
        )
        response.raise_for_status()
        products = response.json().get("products", [])
    except Exception:
        return []

    episodes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    query_norm = normalize_text_key(title)
    for p in products:
        p_title = str(p.get("title") or "").strip()
        if not p_title:
            continue
        content_type = normalize_text_key(str(p.get("content_type") or p.get("contentType") or ""))
        product_type = normalize_text_key(str(p.get("product_type") or p.get("productType") or ""))
        merged_type = " ".join([content_type, product_type]).strip()
        if merged_type and ("podcast" not in merged_type and "episode" not in merged_type):
            # Audible fallback is only for podcast-like entities.
            continue
        if query_norm and query_norm not in normalize_text_key(p_title):
            # keep quality high for podcast fallback
            continue

        asin = str(p.get("asin") or "").strip()
        if not asin or asin in seen_ids:
            continue
        seen_ids.add(asin)
        authors = ", ".join([a.get("name", "") for a in p.get("authors", []) if a.get("name")]).strip()
        published = str(
            p.get("release_date")
            or p.get("releaseDate")
            or p.get("publication_datetime")
            or p.get("publicationDate")
            or ""
        ).strip()
        runtime = float(p.get("runtime_length_min") or p.get("runtimeLengthMin") or 0.0)
        duration_sec = runtime * 60.0 if runtime > 0 else None
        image_url = str(p.get("product_image") or p.get("productImage") or p.get("image_url") or "").strip()
        episodes.append(
            {
                "external_id": f"audible:{asin}"[:64],
                "title": p_title,
                "published_at": published,
                "author": authors or author,
                "duration_sec": duration_sec,
                "image_url": image_url,
                "podcast_title": title,
                "source": "audible",
            }
        )

    episodes.sort(key=lambda ep: parse_published_timestamp(str(ep.get("published_at") or "")))
    return episodes


def import_abs_catalog(owner_user_id: int, import_books: bool, import_podcasts: bool, enrich_podcasts: bool = False) -> dict[str, int]:
    creds_map = get_user_target_credentials(owner_user_id)
    stats = {"books": 0, "podcasts": 0, "podcast_episodes": 0}
    if not creds_map:
        return stats

    with get_conn() as conn:
        with conn.cursor() as cur:
            for target_id, cred in creds_map.items():
                if not cred.get("url") or not cred.get("token"):
                    continue
                me_payload = abs_get_optional_json(cred["url"], cred["token"], "/api/me") or {}
                me_user_id = str(me_payload.get("id") or "")
                try:
                    libs_payload = abs_get_json(cred["url"], cred["token"], "/api/libraries")
                except Exception:
                    continue
                libraries = libs_payload.get("libraries", []) if isinstance(libs_payload, dict) else []
                for lib in libraries:
                    media_type = str(lib.get("mediaType") or "").lower()
                    if media_type == "book" and not import_books:
                        continue
                    if media_type == "podcast" and not import_podcasts:
                        continue
                    library_id = str(lib.get("id") or "")
                    if not library_id:
                        continue

                    page = 0
                    while True:
                        try:
                            items_payload = abs_get_json(
                                cred["url"],
                                cred["token"],
                                f"/api/libraries/{library_id}/items",
                                {"limit": 200, "page": page, "minified": 0},
                            )
                        except Exception:
                            break

                        results = items_payload.get("results", []) if isinstance(items_payload, dict) else []
                        if not results:
                            break

                        for item in results:
                            item_id = str(item.get("id") or "")
                            item_media_type = str(item.get("mediaType") or media_type or "").lower()
                            metadata = ((item.get("media") or {}).get("metadata") or {})
                            title = str(metadata.get("title") or "")
                            if not item_id or not title:
                                continue

                            if item_media_type == "book" and import_books:
                                author = str(metadata.get("authorName") or metadata.get("author") or "")
                                series_name = str(metadata.get("seriesName") or "")
                                published_year = parse_int(metadata.get("publishedYear") or metadata.get("publishYear"), 0)
                                asin = str(metadata.get("asin") or "")
                                isbn = str(metadata.get("isbn") or "")
                                duration_sec = float(((item.get("media") or {}).get("duration") or 0.0))
                                canonical_key = build_canonical_key(asin, isbn, title, author, duration_sec)
                                cover_url = f"{cred['url']}/api/items/{item_id}/cover"
                                cur.execute(
                                    """
                                    INSERT INTO ui_collected_items
                                    (owner_user_id, target_id, library_item_id, media_type, title, author, series_name, published_year, asin, cover_url, collection_status, source)
                                    VALUES (%s,%s,%s,'book',%s,%s,%s,%s,%s,%s,'collected','abs')
                                    ON DUPLICATE KEY UPDATE
                                      title=VALUES(title),
                                      author=VALUES(author),
                                      series_name=VALUES(series_name),
                                      published_year=VALUES(published_year),
                                      asin=VALUES(asin),
                                      cover_url=VALUES(cover_url),
                                      collection_status='collected',
                                      updated_at=CURRENT_TIMESTAMP
                                    """,
                                    (
                                        owner_user_id,
                                        target_id,
                                        item_id,
                                        title,
                                        author,
                                        series_name,
                                        published_year if published_year > 0 else None,
                                        asin,
                                        cover_url,
                                    ),
                                )
                                cur.execute(
                                    """
                                    INSERT INTO item_identity
                                    (target_id, library_item_id, canonical_key, asin, isbn, title, author, series_name, published_year, duration_sec)
                                    VALUES (%s,%s,NULLIF(%s,''),NULLIF(%s,''),NULLIF(%s,''),%s,%s,%s,%s,%s)
                                    ON DUPLICATE KEY UPDATE
                                      canonical_key=VALUES(canonical_key),
                                      asin=VALUES(asin),
                                      isbn=VALUES(isbn),
                                      title=VALUES(title),
                                      author=VALUES(author),
                                      series_name=VALUES(series_name),
                                      published_year=VALUES(published_year),
                                      duration_sec=VALUES(duration_sec),
                                      updated_at=CURRENT_TIMESTAMP
                                    """,
                                    (
                                        target_id,
                                        item_id,
                                        canonical_key,
                                        asin,
                                        isbn,
                                        title,
                                        author,
                                        series_name,
                                        published_year if published_year > 0 else None,
                                        duration_sec if duration_sec > 0 else None,
                                    ),
                                )
                                stats["books"] += 1

                                # Full progress backfill: /api/me is often incomplete, so resolve per-item progress.
                                progress_payload = abs_get_optional_json(cred["url"], cred["token"], f"/api/me/progress/{item_id}") or {}
                                if progress_payload:
                                    progress_ratio = float(progress_payload.get("progress") or 0.0)
                                    is_finished = 1 if bool(progress_payload.get("isFinished")) or progress_ratio >= 0.98 else 0
                                    if progress_ratio > 0 or is_finished == 1:
                                        current_time_sec = float(progress_payload.get("currentTime") or 0.0)
                                        duration_sec_progress = float(progress_payload.get("duration") or duration_sec or 0.0)
                                        last_update_ms = int(progress_payload.get("lastUpdate") or int(time.time() * 1000))
                                        started_at_ms = int(progress_payload.get("startedAt") or 0) or None
                                        finished_at_ms = int(progress_payload.get("finishedAt") or 0) or None
                                        media_progress_id = str(progress_payload.get("id") or f"import-{target_id}-{item_id}")
                                        user_id = me_user_id or target_id
                                        server_id = target_id
                                        principal_id = target_id
                                        cur.execute(
                                            """
                                            INSERT INTO progress_latest
                                            (target_id, server_id, principal_id, user_id, library_item_id, episode_id, media_progress_id, canonical_key, progress, current_time_sec, duration, is_finished, started_at_ms, finished_at_ms, last_update_ms, source)
                                            VALUES (%s,%s,%s,%s,%s,'',%s,NULLIF(%s,''),%s,%s,%s,%s,%s,%s,%s,'remote_pull')
                                            ON DUPLICATE KEY UPDATE
                                              server_id=VALUES(server_id),
                                              principal_id=VALUES(principal_id),
                                              media_progress_id=VALUES(media_progress_id),
                                              canonical_key=VALUES(canonical_key),
                                              progress=VALUES(progress),
                                              current_time_sec=VALUES(current_time_sec),
                                              duration=VALUES(duration),
                                              is_finished=VALUES(is_finished),
                                              started_at_ms=VALUES(started_at_ms),
                                              finished_at_ms=VALUES(finished_at_ms),
                                              last_update_ms=VALUES(last_update_ms),
                                              source=VALUES(source)
                                            """,
                                            (
                                                target_id,
                                                server_id,
                                                principal_id,
                                                user_id,
                                                item_id,
                                                media_progress_id,
                                                canonical_key,
                                                progress_ratio,
                                                current_time_sec,
                                                duration_sec_progress,
                                                is_finished,
                                                started_at_ms,
                                                finished_at_ms,
                                                last_update_ms,
                                            ),
                                        )
                                        cur.execute(
                                            """
                                            INSERT INTO progress_history
                                            (target_id, server_id, principal_id, user_id, library_item_id, episode_id, media_progress_id, canonical_key, progress, current_time_sec, duration, is_finished, started_at_ms, finished_at_ms, last_update_ms, source)
                                            VALUES (%s,%s,%s,%s,%s,'',%s,NULLIF(%s,''),%s,%s,%s,%s,%s,%s,%s,'remote_pull')
                                            """,
                                            (
                                                target_id,
                                                server_id,
                                                principal_id,
                                                user_id,
                                                item_id,
                                                media_progress_id,
                                                canonical_key,
                                                progress_ratio,
                                                current_time_sec,
                                                duration_sec_progress,
                                                is_finished,
                                                started_at_ms,
                                                finished_at_ms,
                                                last_update_ms,
                                            ),
                                        )

                            if item_media_type == "podcast" and import_podcasts:
                                author = str(metadata.get("author") or metadata.get("authorName") or "")
                                feed_url = str(metadata.get("feedUrl") or "")
                                image_url = str(metadata.get("imageUrl") or "")
                                itunes_id = str(metadata.get("itunesId") or "")
                                itunes_page_url = str(metadata.get("itunesPageUrl") or "")
                                release_date = str(metadata.get("releaseDate") or "")
                                language = str(metadata.get("language") or "")

                                if enrich_podcasts and (not image_url or not itunes_id):
                                    enrich = itunes_lookup_podcast(title, author)
                                    image_url = image_url or enrich.get("image_url", "")
                                    feed_url = feed_url or enrich.get("feed_url", "")
                                    itunes_id = itunes_id or enrich.get("itunes_id", "")
                                    itunes_page_url = itunes_page_url or enrich.get("itunes_page_url", "")

                                cur.execute(
                                    """
                                    INSERT INTO ui_podcast_shows
                                    (owner_user_id, target_id, library_item_id, title, author, feed_url, image_url, itunes_id, itunes_page_url, release_date, language, source)
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                    ON DUPLICATE KEY UPDATE
                                      title=VALUES(title),
                                      author=VALUES(author),
                                      feed_url=VALUES(feed_url),
                                      image_url=VALUES(image_url),
                                      itunes_id=VALUES(itunes_id),
                                      itunes_page_url=VALUES(itunes_page_url),
                                      release_date=VALUES(release_date),
                                      language=VALUES(language),
                                      source=VALUES(source),
                                      updated_at=CURRENT_TIMESTAMP
                                    """,
                                    (
                                        owner_user_id,
                                        target_id,
                                        item_id,
                                        title,
                                        author,
                                        feed_url,
                                        image_url,
                                        itunes_id,
                                        itunes_page_url,
                                        release_date,
                                        language,
                                        "itunes" if enrich_podcasts else "abs",
                                    ),
                                )
                                stats["podcasts"] += 1

                                abs_episodes: list[dict[str, Any]] = []
                                try:
                                    item_detail = abs_get_json(cred["url"], cred["token"], f"/api/items/{item_id}")
                                    item_media = (item_detail.get("media") or {}) if isinstance(item_detail, dict) else {}
                                    eps = item_media.get("episodes", []) if isinstance(item_media, dict) else []
                                    for ep in eps:
                                        abs_episodes.append(
                                            {
                                                "id": str(ep.get("id") or ""),
                                                "title": str(ep.get("title") or ""),
                                                "pub": str(ep.get("pubDate") or ep.get("publishedAt") or ""),
                                            }
                                        )
                                except Exception:
                                    abs_episodes = []

                                feed_eps = parse_feed_podcast_episodes(feed_url, title, author)
                                episode_source = "itunes"
                                if not feed_eps:
                                    feed_eps = audible_podcast_fallback_episodes(title, author, limit=80)
                                    if feed_eps:
                                        episode_source = "audible"
                                if not feed_eps:
                                    feed_eps = [
                                        {
                                            "external_id": str(ep.get("id") or "")[:64],
                                            "title": str(ep.get("title") or ""),
                                            "published_at": str(ep.get("pub") or ""),
                                            "author": author,
                                            "duration_sec": None,
                                            "image_url": image_url,
                                            "podcast_title": title,
                                            "source": "abs",
                                        }
                                        for ep in abs_episodes
                                        if str(ep.get("id") or "")
                                    ]
                                    if feed_eps:
                                        episode_source = "abs"

                                imported_ids: list[str] = []
                                for ep in feed_eps:
                                    episode_id = str(ep.get("external_id") or "")[:64]
                                    if not episode_id:
                                        continue
                                    abs_episode_id = match_abs_episode(ep, abs_episodes)
                                    abs_presence = "present" if abs_episode_id else "missing"
                                    imported_ids.append(episode_id)
                                    cur.execute(
                                        """
                                        INSERT INTO ui_podcast_episodes
                                        (owner_user_id, target_id, library_item_id, episode_id, abs_episode_id, abs_presence, podcast_title, episode_title, author, published_at, duration_sec, image_url, source)
                                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                        ON DUPLICATE KEY UPDATE
                                          abs_episode_id=VALUES(abs_episode_id),
                                          abs_presence=VALUES(abs_presence),
                                          podcast_title=VALUES(podcast_title),
                                          episode_title=VALUES(episode_title),
                                          author=VALUES(author),
                                          published_at=VALUES(published_at),
                                          duration_sec=VALUES(duration_sec),
                                          image_url=VALUES(image_url),
                                          source=VALUES(source),
                                          updated_at=CURRENT_TIMESTAMP
                                        """,
                                        (
                                            owner_user_id,
                                            target_id,
                                            item_id,
                                            episode_id,
                                            abs_episode_id,
                                            abs_presence,
                                            title,
                                            str(ep.get("title") or ""),
                                            str(ep.get("author") or author),
                                            str(ep.get("published_at") or ""),
                                            float(ep.get("duration_sec") or 0.0) if float(ep.get("duration_sec") or 0.0) > 0 else None,
                                            str(ep.get("image_url") or image_url or ""),
                                            str(ep.get("source") or episode_source),
                                        ),
                                    )
                                    stats["podcast_episodes"] += 1

                                if imported_ids:
                                    placeholders = ",".join(["%s"] * len(imported_ids))
                                    cur.execute(
                                        f"""
                                        DELETE FROM ui_podcast_episodes
                                        WHERE owner_user_id=%s
                                          AND target_id=%s
                                          AND library_item_id=%s
                                          AND episode_id NOT IN ({placeholders})
                                        """,
                                        [owner_user_id, target_id, item_id, *imported_ids],
                                    )
                        page += 1
    return stats


def _fetch_abs_book_item_ids(base_url: str, token: str) -> set[str]:
    item_ids: set[str] = set()
    libs_payload = abs_get_optional_json(base_url, token, "/api/libraries") or {}
    libraries = libs_payload.get("libraries", []) if isinstance(libs_payload, dict) else []
    for lib in libraries:
        if str(lib.get("mediaType") or "").lower() != "book":
            continue
        library_id = str(lib.get("id") or "")
        if not library_id:
            continue
        page = 0
        while True:
            items_payload = abs_get_optional_json(
                base_url,
                token,
                f"/api/libraries/{library_id}/items",
                {"limit": 200, "page": page, "minified": 1},
            )
            if not isinstance(items_payload, dict):
                break
            results = items_payload.get("results", [])
            if not isinstance(results, list) or not results:
                break
            for item in results:
                item_id = str(item.get("id") or "")
                if item_id:
                    item_ids.add(item_id)
            if len(results) < 200:
                break
            page += 1
    return item_ids


def rebuild_progress_from_abs(owner_user_id: int) -> dict[str, int]:
    creds_map = get_user_target_credentials(owner_user_id)
    stats = {"targets": 0, "scanned": 0, "updated": 0, "completed": 0, "in_progress": 0, "missing": 0}
    if not creds_map:
        return stats

    with get_conn() as conn:
        with conn.cursor() as cur:
            for target_id, cred in creds_map.items():
                base_url = cred.get("url") or ""
                token = cred.get("token") or ""
                if not base_url or not token:
                    continue

                stats["targets"] += 1
                me_payload = abs_get_optional_json(base_url, token, "/api/me") or {}
                me_user_id = str(me_payload.get("id") or target_id)
                server_id = target_id
                principal_id = target_id

                cur.execute(
                    """
                    SELECT
                      c.target_id,
                      c.library_item_id,
                      c.title,
                      c.author,
                      c.asin,
                      COALESCE(ii.isbn, '') AS isbn,
                      COALESCE(ii.duration_sec, 0) AS duration_sec
                    FROM ui_collected_items c
                    LEFT JOIN item_identity ii
                      ON ii.target_id = c.target_id
                     AND ii.library_item_id = c.library_item_id
                    WHERE c.owner_user_id = %s
                      AND c.media_type = 'book'
                      AND c.target_id = %s
                    """,
                    (owner_user_id, target_id),
                )
                rows = cur.fetchall()

                for row in rows:
                    item_id = str(row.get("library_item_id") or "")
                    if not item_id:
                        continue
                    stats["scanned"] += 1

                    progress_payload = abs_get_optional_json(base_url, token, f"/api/me/progress/{item_id}") or {}
                    if not progress_payload:
                        stats["missing"] += 1
                        continue

                    progress_ratio = float(progress_payload.get("progress") or 0.0)
                    is_finished = 1 if bool(progress_payload.get("isFinished")) or progress_ratio >= 0.98 else 0
                    if is_finished == 1:
                        stats["completed"] += 1
                    elif progress_ratio > 0:
                        stats["in_progress"] += 1

                    current_time_sec = float(progress_payload.get("currentTime") or 0.0)
                    duration = float(progress_payload.get("duration") or row.get("duration_sec") or 0.0)
                    last_update_ms = int(progress_payload.get("lastUpdate") or int(time.time() * 1000))
                    started_at_ms = int(progress_payload.get("startedAt") or 0) or None
                    finished_at_ms = int(progress_payload.get("finishedAt") or 0) or None
                    media_progress_id = str(progress_payload.get("id") or f"rebuild-{target_id}-{item_id}")
                    canonical_key = build_canonical_key(
                        str(row.get("asin") or ""),
                        str(row.get("isbn") or ""),
                        str(row.get("title") or ""),
                        str(row.get("author") or ""),
                        duration,
                    )

                    cur.execute(
                        """
                        INSERT INTO progress_latest
                        (target_id, server_id, principal_id, user_id, library_item_id, episode_id, media_progress_id, canonical_key, progress, current_time_sec, duration, is_finished, started_at_ms, finished_at_ms, last_update_ms, source)
                        VALUES (%s,%s,%s,%s,%s,'',%s,NULLIF(%s,''),%s,%s,%s,%s,%s,%s,%s,'remote_pull')
                        ON DUPLICATE KEY UPDATE
                          server_id=VALUES(server_id),
                          principal_id=VALUES(principal_id),
                          media_progress_id=VALUES(media_progress_id),
                          canonical_key=VALUES(canonical_key),
                          progress=VALUES(progress),
                          current_time_sec=VALUES(current_time_sec),
                          duration=VALUES(duration),
                          is_finished=VALUES(is_finished),
                          started_at_ms=VALUES(started_at_ms),
                          finished_at_ms=VALUES(finished_at_ms),
                          last_update_ms=VALUES(last_update_ms),
                          source=VALUES(source)
                        """,
                        (
                            target_id,
                            server_id,
                            principal_id,
                            me_user_id,
                            item_id,
                            media_progress_id,
                            canonical_key,
                            progress_ratio,
                            current_time_sec,
                            duration,
                            is_finished,
                            started_at_ms,
                            finished_at_ms,
                            last_update_ms,
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO progress_history
                        (target_id, server_id, principal_id, user_id, library_item_id, episode_id, media_progress_id, canonical_key, progress, current_time_sec, duration, is_finished, started_at_ms, finished_at_ms, last_update_ms, source)
                        VALUES (%s,%s,%s,%s,%s,'',%s,NULLIF(%s,''),%s,%s,%s,%s,%s,%s,%s,'remote_pull')
                        """,
                        (
                            target_id,
                            server_id,
                            principal_id,
                            me_user_id,
                            item_id,
                            media_progress_id,
                            canonical_key,
                            progress_ratio,
                            current_time_sec,
                            duration,
                            is_finished,
                            started_at_ms,
                            finished_at_ms,
                            last_update_ms,
                        ),
                    )
                    stats["updated"] += 1

    return stats


def _dedupe_collected_key(asin: str, isbn: str, title: str, author: str, year: int) -> str:
    asin_norm = (asin or "").strip().upper()
    if asin_norm:
        return f"asin:{asin_norm}"
    isbn_norm = (isbn or "").strip().replace("-", "").replace(" ", "").upper()
    if isbn_norm:
        return f"isbn:{isbn_norm}"
    title_norm = " ".join((title or "").strip().lower().split())
    author_norm = " ".join((author or "").strip().lower().split())
    return f"text:{title_norm}|{author_norm}|{int(year or 0)}"


def cleanup_collected_library(owner_user_id: int) -> dict[str, int]:
    creds_map = get_user_target_credentials(owner_user_id)
    stats = {"before": 0, "after": 0, "marked_missing": 0, "merged_duplicates": 0, "merged_groups": 0, "targets": 0}

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM ui_collected_items WHERE owner_user_id = %s AND media_type = 'book'",
                (owner_user_id,),
            )
            stats["before"] = int((cur.fetchone() or {}).get("c") or 0)

            live_ids_by_target: dict[str, set[str]] = {}
            for target_id, cred in creds_map.items():
                if not cred.get("url") or not cred.get("token"):
                    continue
                live_ids = _fetch_abs_book_item_ids(cred["url"], cred["token"])
                live_ids_by_target[target_id] = live_ids
                stats["targets"] += 1

            if live_ids_by_target:
                for target_id, live_ids in live_ids_by_target.items():
                    cur.execute(
                        """
                        UPDATE ui_collected_items
                        SET collection_status = 'missing'
                        WHERE owner_user_id = %s
                          AND media_type = 'book'
                          AND target_id = %s
                        """,
                        (owner_user_id, target_id),
                    )
                    cur.execute(
                        """
                        SELECT id, library_item_id
                        FROM ui_collected_items
                        WHERE owner_user_id = %s
                          AND media_type = 'book'
                          AND target_id = %s
                        """,
                        (owner_user_id, target_id),
                    )
                    live_row_ids: list[int] = []
                    missing_count = 0
                    for row in cur.fetchall():
                        if str(row.get("library_item_id") or "") in live_ids:
                            live_row_ids.append(int(row["id"]))
                        else:
                            missing_count += 1
                    if live_row_ids:
                        placeholders = ",".join(["%s"] * len(live_row_ids))
                        cur.execute(
                            f"UPDATE ui_collected_items SET collection_status='collected' WHERE owner_user_id = %s AND id IN ({placeholders})",
                            [owner_user_id, *live_row_ids],
                        )
                    stats["marked_missing"] += missing_count

            cur.execute(
                """
                SELECT
                  c.id,
                  c.title,
                  c.author,
                  c.published_year,
                  c.asin,
                  c.cover_url,
                  c.series_name,
                  c.collection_status,
                  c.updated_at,
                  COALESCE(ii.isbn, '') AS isbn
                FROM ui_collected_items c
                LEFT JOIN item_identity ii
                  ON ii.target_id = c.target_id
                 AND ii.library_item_id = c.library_item_id
                WHERE c.owner_user_id = %s
                  AND c.media_type = 'book'
                ORDER BY c.updated_at DESC, c.id DESC
                """,
                (owner_user_id,),
            )
            rows = cur.fetchall()
            groups: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                key = _dedupe_collected_key(
                    str(row.get("asin") or ""),
                    str(row.get("isbn") or ""),
                    str(row.get("title") or ""),
                    str(row.get("author") or ""),
                    int(row.get("published_year") or 0),
                )
                groups.setdefault(key, []).append(row)

            delete_ids: list[int] = []
            for grouped_rows in groups.values():
                if len(grouped_rows) <= 1:
                    continue
                stats["merged_groups"] += 1
                scored: list[tuple[int, dict[str, Any]]] = []
                for row in grouped_rows:
                    score = 0
                    if str(row.get("collection_status") or "collected") == "collected":
                        score += 8
                    if str(row.get("asin") or "").strip():
                        score += 16
                    if str(row.get("isbn") or "").strip():
                        score += 12
                    if str(row.get("cover_url") or "").strip():
                        score += 4
                    if str(row.get("series_name") or "").strip():
                        score += 2
                    if int(row.get("published_year") or 0) > 0:
                        score += 1
                    scored.append((score, row))
                scored.sort(key=lambda pair: (pair[0], pair[1].get("updated_at"), int(pair[1].get("id") or 0)), reverse=True)
                keep_id = int(scored[0][1]["id"])
                for _, row in scored[1:]:
                    rid = int(row["id"])
                    if rid != keep_id:
                        delete_ids.append(rid)

            if delete_ids:
                placeholders = ",".join(["%s"] * len(delete_ids))
                cur.execute(
                    f"DELETE FROM ui_collected_items WHERE owner_user_id = %s AND id IN ({placeholders})",
                    [owner_user_id, *delete_ids],
                )
                stats["merged_duplicates"] = len(delete_ids)

            cur.execute(
                "SELECT COUNT(*) AS c FROM ui_collected_items WHERE owner_user_id = %s AND media_type = 'book'",
                (owner_user_id,),
            )
            stats["after"] = int((cur.fetchone() or {}).get("c") or 0)

    return stats


def _normalize_identifier(value: str) -> str:
    return "".join(ch for ch in (value or "").strip().upper() if ch.isalnum())


def manual_match_items(
    owner_user_id: int,
    source_target_id: str,
    source_library_item_id: str,
    ref_target_id: str,
    ref_library_item_id: str,
) -> tuple[bool, str]:
    source_target_id = (source_target_id or "").strip()
    source_library_item_id = (source_library_item_id or "").strip()
    ref_target_id = (ref_target_id or "").strip()
    ref_library_item_id = (ref_library_item_id or "").strip()
    if not source_target_id or not source_library_item_id or not ref_target_id or not ref_library_item_id:
        return (False, "Missing source/reference values.")
    if source_target_id == ref_target_id and source_library_item_id == ref_library_item_id:
        return (False, "Source and reference must be different items.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT target_id, library_item_id, title, author, series_name, published_year, asin
                FROM ui_collected_items
                WHERE owner_user_id = %s
                  AND media_type = 'book'
                  AND target_id = %s
                  AND library_item_id = %s
                LIMIT 1
                """,
                (owner_user_id, source_target_id, source_library_item_id),
            )
            source_collected = cur.fetchone()
            if not source_collected:
                return (False, "Source item not found.")

            cur.execute(
                """
                SELECT target_id, library_item_id, title, author, series_name, published_year, asin
                FROM ui_collected_items
                WHERE owner_user_id = %s
                  AND media_type = 'book'
                  AND target_id = %s
                  AND library_item_id = %s
                LIMIT 1
                """,
                (owner_user_id, ref_target_id, ref_library_item_id),
            )
            ref_collected = cur.fetchone()
            if not ref_collected:
                return (False, "Reference item not found.")

            cur.execute(
                """
                SELECT canonical_key, asin, isbn, title, author, series_name, published_year, duration_sec
                FROM item_identity
                WHERE target_id = %s
                  AND library_item_id = %s
                LIMIT 1
                """,
                (ref_target_id, ref_library_item_id),
            )
            ref_identity = cur.fetchone() or {}

            ref_asin = _normalize_identifier(str(ref_identity.get("asin") or ref_collected.get("asin") or ""))
            ref_isbn = _normalize_identifier(str(ref_identity.get("isbn") or ""))
            ref_title = str(ref_identity.get("title") or ref_collected.get("title") or "")
            ref_author = str(ref_identity.get("author") or ref_collected.get("author") or "")
            ref_duration = float(ref_identity.get("duration_sec") or 0.0)
            canonical_key = str(ref_identity.get("canonical_key") or "").strip()
            if not canonical_key:
                canonical_key = build_canonical_key(ref_asin, ref_isbn, ref_title, ref_author, ref_duration)
            if not canonical_key:
                return (False, "Could not derive canonical key for reference item.")

            source_asin = _normalize_identifier(str(source_collected.get("asin") or ""))
            source_title = str(source_collected.get("title") or "")
            source_author = str(source_collected.get("author") or "")
            source_series = str(source_collected.get("series_name") or "")
            source_year = int(source_collected.get("published_year") or 0) or None

            cur.execute(
                """
                INSERT INTO item_identity
                (target_id, library_item_id, canonical_key, asin, isbn, title, author, series_name, published_year, duration_sec)
                VALUES (%s,%s,NULLIF(%s,''),NULLIF(%s,''),NULLIF(%s,''),%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  canonical_key=VALUES(canonical_key),
                  asin=COALESCE(NULLIF(VALUES(asin),''), asin),
                  isbn=COALESCE(NULLIF(VALUES(isbn),''), isbn),
                  title=COALESCE(NULLIF(VALUES(title),''), title),
                  author=COALESCE(NULLIF(VALUES(author),''), author),
                  series_name=COALESCE(NULLIF(VALUES(series_name),''), series_name),
                  published_year=COALESCE(VALUES(published_year), published_year),
                  duration_sec=COALESCE(VALUES(duration_sec), duration_sec),
                  updated_at=CURRENT_TIMESTAMP
                """,
                (
                    source_target_id,
                    source_library_item_id,
                    canonical_key,
                    source_asin or ref_asin,
                    ref_isbn,
                    source_title or ref_title,
                    source_author or ref_author,
                    source_series or str(ref_identity.get("series_name") or ""),
                    source_year or ref_identity.get("published_year"),
                    ref_duration if ref_duration > 0 else None,
                ),
            )

    request_manual_sync()
    return (True, f"Manual match saved using key {canonical_key}.")


def collect_matching_rows(owner_user_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, target_id, abs_url
                FROM ui_sync_accounts
                WHERE owner_user_id = %s
                ORDER BY id
                """,
                (owner_user_id,),
            )
            accounts = cur.fetchall()
            target_url_map: dict[str, str] = {}
            for acc in accounts:
                tid = (acc.get("target_id") or f"u{owner_user_id}-a{acc['id']}").strip()
                target_url_map[tid] = normalize_url(str(acc.get("abs_url") or ""))

            target_ids = list(target_url_map.keys())
            if not target_ids:
                return ([], [], target_url_map)

            placeholders = ",".join(["%s"] * len(target_ids))
            cur.execute(
                f"""
                SELECT
                  c.target_id,
                  c.library_item_id,
                  c.title,
                  c.author,
                  c.series_name,
                  c.published_year,
                  c.asin,
                  c.collection_status,
                  COALESCE(ii.isbn, '') AS isbn,
                  COALESCE(ii.canonical_key, '') AS canonical_key
                FROM ui_collected_items c
                LEFT JOIN item_identity ii
                  ON ii.target_id = c.target_id
                 AND ii.library_item_id = c.library_item_id
                WHERE c.owner_user_id = %s
                  AND c.media_type = 'book'
                  AND c.target_id IN ({placeholders})
                ORDER BY c.title ASC
                """,
                [owner_user_id, *target_ids],
            )
            rows = cur.fetchall()

    keyed_targets: dict[str, set[str]] = {}
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        asin_norm = _normalize_identifier(str(row.get("asin") or ""))
        isbn_norm = _normalize_identifier(str(row.get("isbn") or ""))
        ck = str(row.get("canonical_key") or "").strip()
        keys: list[str] = []
        if ck:
            keys.append(f"ck:{ck}")
        if asin_norm:
            keys.append(f"asin:{asin_norm}")
        if isbn_norm:
            keys.append(f"isbn:{isbn_norm}")
        target_id = str(row.get("target_id") or "")
        for key in keys:
            keyed_targets.setdefault(key, set()).add(target_id)
        normalized_rows.append(
            {
                **row,
                "asin_norm": asin_norm,
                "isbn_norm": isbn_norm,
                "keys": keys,
                "abs_url": f"{target_url_map.get(target_id, '')}/item/{row.get('library_item_id')}" if target_url_map.get(target_id) else "",
                "value_key": f"{target_id}|{row.get('library_item_id')}",
            }
        )

    # "Unmatched" should only include items without stable identifiers.
    # Previous logic flagged almost everything unmatched on single-server setups.
    unmatched_rows: list[dict[str, Any]] = []
    for row in normalized_rows:
        canonical_key = str(row.get("canonical_key") or "").strip()
        asin_norm = str(row.get("asin_norm") or "").strip()
        isbn_norm = str(row.get("isbn_norm") or "").strip()
        if not canonical_key and not asin_norm and not isbn_norm:
            unmatched_rows.append(row)

    return (normalized_rows, unmatched_rows, target_url_map)


def openlibrary_search(query: str) -> list[dict[str, Any]]:
    response = requests.get(
        "https://openlibrary.org/search.json",
        params={"q": query, "limit": 12},
        timeout=10,
    )
    response.raise_for_status()
    docs = response.json().get("docs", [])

    results = []
    for doc in docs:
        title = (doc.get("title") or "").strip()
        if not title:
            continue
        authors = ", ".join(doc.get("author_name", [])[:3])
        isbn_list = doc.get("isbn", [])
        isbn = isbn_list[0] if isbn_list else ""
        results.append(
            {
                "title": title,
                "author": authors,
                "isbn": isbn,
                "asin": "",
                "series_name": "",
                "series_index": "",
                "source": "openlibrary",
            }
        )
    return results


def audible_search(query: str, limit: int = 12) -> list[dict[str, Any]]:
    base_url = os.getenv("AUDIBLE_API_BASE_URL", "https://api.audible.com").rstrip("/")
    bearer = os.getenv("AUDIBLE_API_BEARER_TOKEN", "").strip()
    marketplace = os.getenv("AUDIBLE_MARKETPLACE", "us").strip()
    if not bearer:
        return []

    response = requests.get(
        f"{base_url}/1.0/catalog/products",
        params={
            "num_results": limit,
            "keywords": query,
            "response_groups": "product_desc,contributors,series,product_attrs",
            "marketplace": marketplace,
        },
        headers={"Authorization": f"Bearer {bearer}"},
        timeout=12,
    )
    response.raise_for_status()
    products = response.json().get("products", [])

    results = []
    for p in products:
        authors = ", ".join([a.get("name", "") for a in p.get("authors", []) if a.get("name")])
        series = p.get("series", [])
        series_name = series[0].get("title", "") if series else ""
        series_index = series[0].get("sequence", "") if series else ""
        results.append(
            {
                "title": p.get("title", ""),
                "author": authors,
                "isbn": p.get("isbn", ""),
                "asin": p.get("asin", ""),
                "series_name": series_name,
                "series_index": str(series_index or ""),
                "source": "audible",
            }
        )
    return results


def enrich_with_audible(title: str, author: str, asin: str, isbn: str, series_name: str, series_index: str) -> dict[str, str]:
    if asin:
        return {
            "asin": asin,
            "isbn": isbn,
            "series_name": series_name,
            "series_index": series_index,
            "source": "manual",
        }

    query = f"{title} {author}".strip()
    if not query:
        return {
            "asin": asin,
            "isbn": isbn,
            "series_name": series_name,
            "series_index": series_index,
            "source": "manual",
        }

    try:
        matches = audible_search(query, limit=3)
        if matches:
            best = matches[0]
            return {
                "asin": asin or str(best.get("asin") or ""),
                "isbn": isbn or str(best.get("isbn") or ""),
                "series_name": series_name or str(best.get("series_name") or ""),
                "series_index": series_index or str(best.get("series_index") or ""),
                "source": "audible" if best.get("asin") else "manual",
            }
    except Exception:
        pass

    return {
        "asin": asin,
        "isbn": isbn,
        "series_name": series_name,
        "series_index": series_index,
        "source": "manual",
    }


@app.before_request
def before_request() -> Any:
    global SCHEMA_READY
    g.lang = get_lang()
    attempts = 20
    for _ in range(attempts):
        try:
            ensure_ui_schema()
            return None
        except pymysql.MySQLError:
            SCHEMA_READY = False
            time.sleep(1)
    return render_template("db_wait.html"), 503


@app.route("/register", methods=["GET", "POST"])
def register():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM ui_users")
            user_count = int((cur.fetchone() or {}).get("c") or 0)

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        if len(username) < 3 or len(password) < 8:
            flash("Username min. 3 chars, password min. 8 chars.", "error")
            return render_template("register.html", first_user=user_count == 0)
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO ui_users (username, password_hash) VALUES (%s, %s)",
                        (username, generate_password_hash(password)),
                    )
                    user_id = cur.lastrowid
                    cur.execute(
                        "INSERT INTO ui_user_settings (user_id, sync_interval_seconds) VALUES (%s, 300)",
                        (user_id,),
                    )
            session["user_id"] = user_id
            flash("Account created.", "ok")
            return redirect(url_for("sync_settings"))
        except pymysql.err.IntegrityError:
            flash("Username already exists.", "error")

    if user_count > 0:
        return render_template("register.html", first_user=False)
    return render_template("register.html", first_user=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, password_hash FROM ui_users WHERE username = %s", (username,))
                user = cur.fetchone()
                if user and check_password_hash(user["password_hash"], password):
                    session["user_id"] = user["id"]
                    cur.execute("UPDATE ui_users SET last_login_at = NOW() WHERE id = %s", (user["id"],))
                    return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/set-language/<lang_code>")
def set_language(lang_code: str):
    code = (lang_code or "").strip().lower()
    if code in ("en", "de"):
        session["lang"] = code
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/")
@login_required
def dashboard():
    user = current_user()
    user_id = int(user["id"])
    q = (request.args.get("q") or "").strip()
    provider = (request.args.get("provider") or "openlibrary").strip().lower()
    media_view = (request.args.get("media") or "home").strip().lower()
    if media_view not in ("home", "audiobooks", "podcasts"):
        media_view = "home"

    search_results = []
    search_error = ""
    if q:
        try:
            if provider == "audible":
                search_results = audible_search(q)
                if not search_results:
                    search_error = "No Audible results or missing Audible API bearer token."
            else:
                search_results = openlibrary_search(q)
        except Exception as exc:
            search_error = f"Search failed: {exc}"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, author, asin, isbn, series_name, series_index, status, progress, metadata_source, updated_at
                FROM ui_tracked_books
                WHERE owner_user_id = %s
                ORDER BY updated_at DESC, id DESC
                LIMIT 200
                """,
                (user_id,),
            )
            tracked = cur.fetchall()

            cur.execute(
                "SELECT status, COUNT(*) AS c FROM ui_tracked_books WHERE owner_user_id = %s GROUP BY status",
                (user_id,),
            )
            counts = {r["status"]: int(r["c"]) for r in cur.fetchall()}

            cur.execute(
                """
                SELECT series_name, MAX(series_index) AS max_idx
                FROM ui_tracked_books
                WHERE owner_user_id = %s
                  AND status = 'heard'
                  AND series_name IS NOT NULL
                  AND series_name <> ''
                  AND series_index IS NOT NULL
                GROUP BY series_name
                ORDER BY series_name
                """,
                (user_id,),
            )
            finished_series = cur.fetchall()

            recommendations = []
            for row in finished_series:
                cur.execute(
                    """
                    SELECT title, author, series_name, series_index, asin, isbn
                    FROM ui_tracked_books
                    WHERE owner_user_id = %s
                      AND series_name = %s
                      AND series_index > %s
                    ORDER BY series_index ASC
                    LIMIT 1
                    """,
                    (user_id, row["series_name"], row["max_idx"]),
                )
                nxt = cur.fetchone()
                if nxt:
                    recommendations.append(nxt)

            cur.execute(
                "SELECT sync_interval_seconds FROM ui_user_settings WHERE user_id = %s",
                (user_id,),
            )
            settings_row = cur.fetchone() or {}

            cur.execute(
                """
                SELECT id, account_name, abs_url, abs_username, target_id, enabled, updated_at
                FROM ui_sync_accounts
                WHERE owner_user_id = %s
                ORDER BY account_name
                """,
                (user_id,),
            )
            accounts = cur.fetchall()

            effective_target_ids = []
            target_url_map = {}
            for acc in accounts:
                tid = (acc.get("target_id") or f"u{user_id}-a{acc['id']}").strip()
                effective_target_ids.append(tid)
                target_url_map[tid] = normalize_url(str(acc.get("abs_url") or ""))

            sync_rows = []
            sync_count = 0
            sync_category_counts = {
                "not_started": 0,
                "in_progress": 0,
                "completed": 0,
                "paused": 0,
                "dropped": 0,
            }
            if effective_target_ids:
                placeholders = ",".join(["%s"] * len(effective_target_ids))
                cur.execute(
                    f"""
                    SELECT COUNT(*) AS c
                    FROM progress_latest
                    WHERE target_id IN ({placeholders})
                      AND episode_id = ''
                    """,
                    tuple(effective_target_ids),
                )
                sync_count = int((cur.fetchone() or {}).get("c") or 0)

                cur.execute(
                    f"""
                    SELECT target_id, user_id, library_item_id, episode_id, progress, is_finished, last_update_ms, source
                    FROM progress_latest
                    WHERE target_id IN ({placeholders})
                      AND episode_id = ''
                    ORDER BY last_update_ms DESC
                    LIMIT 20
                    """,
                    tuple(effective_target_ids),
                )
                sync_rows = cur.fetchall()
                tracked_books_sync = []
                cur.execute(
                    f"""
                    SELECT
                      pl.target_id,
                      pl.library_item_id,
                      pl.episode_id,
                      COALESCE(pl.progress,0) AS progress,
                      COALESCE(pl.is_finished,0) AS is_finished,
                      COALESCE(ii.title, pl.library_item_id) AS title,
                      COALESCE(ii.author, '') AS author,
                      COALESCE(ii.series_name, '') AS series_name,
                      COALESCE(ii.published_year, 0) AS published_year,
                      COALESCE(ii.asin, '') AS asin
                    FROM progress_latest pl
                    LEFT JOIN item_identity ii
                      ON ii.target_id = pl.target_id
                     AND ii.library_item_id = pl.library_item_id
                    WHERE pl.target_id IN ({placeholders})
                      AND pl.episode_id = ''
                    ORDER BY pl.last_update_ms DESC
                    LIMIT 500
                    """,
                    tuple(effective_target_ids),
                )
                for row in cur.fetchall():
                    progress_ratio = float(row.get("progress") or 0.0)
                    progress_pct = max(0.0, min(100.0, progress_ratio * 100.0))
                    is_finished = int(row.get("is_finished") or 0) == 1 or progress_ratio >= 0.98
                    status = "completed" if is_finished else ("in_progress" if progress_ratio > 0 else "not_started")
                    target_id = str(row.get("target_id") or "")
                    library_item_id = str(row.get("library_item_id") or "")
                    cover_url = url_for("cover_proxy", target_id=target_id, library_item_id=library_item_id) if target_id and library_item_id else ""
                    tracked_books_sync.append(
                        {
                            "target_id": target_id,
                            "library_item_id": library_item_id,
                            "title": row.get("title") or library_item_id,
                            "author": row.get("author") or "",
                            "series_name": row.get("series_name") or "",
                            "published_year": int(row.get("published_year") or 0),
                            "asin": row.get("asin") or "",
                            "progress_pct": round(progress_pct, 1),
                            "status": status,
                            "cover_url": cover_url,
                        }
                    )

                cur.execute(
                    f"""
                    SELECT
                      SUM(CASE WHEN (COALESCE(progress,0) = 0 AND COALESCE(is_finished,0) = 0) THEN 1 ELSE 0 END) AS backlog_count,
                      SUM(CASE WHEN (COALESCE(progress,0) > 0 AND COALESCE(progress,0) < 0.98 AND COALESCE(is_finished,0) = 0) THEN 1 ELSE 0 END) AS in_progress_count,
                      SUM(CASE WHEN (COALESCE(is_finished,0) = 1 OR COALESCE(progress,0) >= 0.98) THEN 1 ELSE 0 END) AS completed_count
                    FROM progress_latest
                    WHERE target_id IN ({placeholders})
                      AND episode_id = ''
                    """,
                    tuple(effective_target_ids),
                )
                stats = cur.fetchone() or {}
                sync_category_counts = {
                    "not_started": int(stats.get("backlog_count") or 0),
                    "in_progress": int(stats.get("in_progress_count") or 0),
                    "completed": int(stats.get("completed_count") or 0),
                    "paused": 0,
                    "dropped": 0,
                }
            else:
                tracked_books_sync = []

            cur.execute(
                """
                SELECT
                  c.target_id,
                  c.library_item_id,
                  c.title,
                  c.author,
                  c.series_name,
                  c.published_year,
                  c.asin,
                  c.cover_url,
                  c.collection_status,
                  COALESCE(pl.progress, 0) AS progress,
                  COALESCE(pl.is_finished, 0) AS is_finished
                FROM ui_collected_items c
                LEFT JOIN progress_latest pl
                  ON pl.target_id = c.target_id
                 AND pl.library_item_id = c.library_item_id
                 AND pl.episode_id = ''
                WHERE c.owner_user_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
            collected_books = []
            for row in cur.fetchall():
                progress_ratio = float(row.get("progress") or 0.0)
                is_finished = int(row.get("is_finished") or 0) == 1 or progress_ratio >= 0.98
                listening_status = "completed" if is_finished else ("in_progress" if progress_ratio > 0 else "not_started")
                collected_books.append(
                    {
                        **row,
                        "listening_status": listening_status,
                    }
                )
            collected_books_sorted = sorted(
                collected_books,
                key=lambda b: str(b.get("title") or "").casefold(),
            )

            cur.execute(
                """
                SELECT target_id, library_item_id, title, author, image_url, itunes_id, itunes_page_url, release_date
                FROM ui_podcast_shows
                WHERE owner_user_id = %s
                ORDER BY title ASC
                """,
                (user_id,),
            )
            podcasts = cur.fetchall()

            cur.execute(
                """
                SELECT
                  pe.target_id,
                  pe.library_item_id,
                  pe.episode_id,
                  pe.abs_episode_id,
                  pe.abs_presence,
                  pe.podcast_title,
                  pe.episode_title,
                  pe.author,
                  pe.image_url,
                  COALESCE(pl.progress, 0) AS progress,
                  COALESCE(pl.is_finished, 0) AS is_finished
                FROM ui_podcast_episodes pe
                LEFT JOIN progress_latest pl
                  ON pl.target_id = pe.target_id
                 AND pl.library_item_id = pe.library_item_id
                 AND pl.episode_id = COALESCE(pe.abs_episode_id, pe.episode_id)
                WHERE pe.owner_user_id = %s
                ORDER BY pe.updated_at DESC
                LIMIT 10
                """,
                (user_id,),
            )
            podcast_episode_rows = cur.fetchall()
            cur.execute(
                "SELECT COUNT(*) AS c FROM ui_podcast_episodes WHERE owner_user_id = %s",
                (user_id,),
            )
            podcast_episode_total = int((cur.fetchone() or {}).get("c") or 0)
            podcast_episodes = []
            for row in podcast_episode_rows:
                progress_ratio = float(row.get("progress") or 0.0)
                progress_pct = max(0.0, min(100.0, progress_ratio * 100.0))
                is_finished = int(row.get("is_finished") or 0) == 1 or progress_ratio >= 0.98
                status = "completed" if is_finished else ("in_progress" if progress_ratio > 0 else "not_started")
                podcast_episodes.append(
                    {
                        "target_id": row.get("target_id") or "",
                        "library_item_id": row.get("library_item_id") or "",
                        "episode_id": row.get("episode_id") or "",
                        "podcast_title": row.get("podcast_title") or "",
                        "episode_title": row.get("episode_title") or "",
                        "author": row.get("author") or "",
                        "image_url": row.get("image_url") or "",
                        "abs_presence": row.get("abs_presence") or "missing",
                        "progress_pct": round(progress_pct, 1),
                        "status": status,
                    }
                )

            cur.execute(
                """
                SELECT
                  pe.target_id,
                  pe.library_item_id,
                  pe.podcast_title,
                  pe.episode_id,
                  pe.abs_episode_id,
                  pe.abs_presence,
                  pe.episode_title,
                  pe.published_at,
                  COALESCE(pl.progress, 0) AS progress,
                  COALESCE(pl.is_finished, 0) AS is_finished
                FROM ui_podcast_episodes pe
                LEFT JOIN progress_latest pl
                  ON pl.target_id = pe.target_id
                 AND pl.library_item_id = pe.library_item_id
                 AND pl.episode_id = COALESCE(pe.abs_episode_id, pe.episode_id)
                WHERE pe.owner_user_id = %s
                ORDER BY pe.target_id, pe.library_item_id, pe.published_at, pe.episode_title
                """,
                (user_id,),
            )
            episode_rows_all = cur.fetchall()
            next_episode_map: dict[tuple[str, str], tuple[tuple[int, int, float, str], str]] = {}
            next_episode_map_any: dict[tuple[str, str], tuple[tuple[int, int, float, str], str]] = {}
            for row in episode_rows_all:
                target_id = str(row.get("target_id") or "")
                library_item_id = str(row.get("library_item_id") or "")
                key = (target_id, library_item_id)
                progress_ratio = float(row.get("progress") or 0.0)
                is_finished = int(row.get("is_finished") or 0) == 1 or progress_ratio >= 0.98
                if is_finished:
                    continue
                title = str(row.get("episode_title") or "")
                sort_key = podcast_episode_sort_key(title, str(row.get("published_at") or ""))
                existing_any = next_episode_map_any.get(key)
                if not existing_any or sort_key < existing_any[0]:
                    next_episode_map_any[key] = (sort_key, title)
                if str(row.get("abs_presence") or "missing") != "present":
                    continue
                existing = next_episode_map.get(key)
                if not existing or sort_key < existing[0]:
                    next_episode_map[key] = (sort_key, title)

            podcast_cards = []
            podcast_image_map: dict[tuple[str, str], str] = {}
            for p in podcasts:
                key = (str(p.get("target_id") or ""), str(p.get("library_item_id") or ""))
                next_episode = (next_episode_map.get(key) or next_episode_map_any.get(key) or ((0, 0, 0.0, ""), t("podcast.all_done")))[1]
                podcast_image_map[key] = str(p.get("image_url") or "")
                podcast_cards.append(
                    {
                        **p,
                        "next_episode": next_episode,
                    }
                )

            home_continue = [b for b in tracked_books_sync if b.get("status") == "in_progress"][:10]
            series_groups: dict[str, list[dict[str, Any]]] = {}
            for b in collected_books_sorted:
                series_name = str(b.get("series_name") or "").strip()
                if not series_name:
                    continue
                series_group = normalize_series_group_name(series_name)
                if not series_group:
                    continue
                target_id = str(b.get("target_id") or "")
                library_item_id = str(b.get("library_item_id") or "")
                status = str(b.get("listening_status") or "not_started")
                item = {
                    "target_id": target_id,
                    "library_item_id": library_item_id,
                    "title": str(b.get("title") or ""),
                    "author": str(b.get("author") or ""),
                    "series_name": series_group,
                    "published_year": int(b.get("published_year") or 0),
                    "asin": str(b.get("asin") or ""),
                    "status": status,
                    "cover_url": str(b.get("cover_url") or ""),
                }
                series_groups.setdefault(series_group.casefold(), []).append(item)

            home_next_series_books: list[dict[str, Any]] = []
            for _, items in series_groups.items():
                items.sort(key=lambda i: (int(i.get("published_year") or 0) or 9999, str(i.get("title") or "").casefold()))
                completed_idx = [idx for idx, item in enumerate(items) if item.get("status") == "completed"]
                if not completed_idx:
                    continue
                last_completed = max(completed_idx)
                candidate = next((it for idx, it in enumerate(items) if idx > last_completed and it.get("status") != "completed"), None)
                if not candidate:
                    candidate = next((it for it in items if it.get("status") != "completed"), None)
                if candidate:
                    home_next_series_books.append(candidate)
            home_next_series_books.sort(key=lambda i: (str(i.get("series_name") or "").casefold(), int(i.get("published_year") or 0), str(i.get("title") or "").casefold()))
            home_next_series_books = home_next_series_books[:10]

            podcast_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
            for row in episode_rows_all:
                target_id = str(row.get("target_id") or "")
                library_item_id = str(row.get("library_item_id") or "")
                key = (target_id, library_item_id)
                progress_ratio = float(row.get("progress") or 0.0)
                is_finished = int(row.get("is_finished") or 0) == 1 or progress_ratio >= 0.98
                podcast_groups.setdefault(key, []).append(
                    {
                        "target_id": target_id,
                        "library_item_id": library_item_id,
                        "podcast_title": str(row.get("podcast_title") or ""),
                        "episode_title": str(row.get("episode_title") or ""),
                        "published_at": str(row.get("published_at") or ""),
                        "is_finished": is_finished,
                    }
                )

            home_next_podcast_episodes: list[dict[str, Any]] = []
            for key, eps in podcast_groups.items():
                eps.sort(key=lambda ep: podcast_episode_sort_key(str(ep.get("episode_title") or ""), str(ep.get("published_at") or "")))
                completed_idx = [idx for idx, ep in enumerate(eps) if ep.get("is_finished")]
                if not completed_idx:
                    continue
                last_completed = max(completed_idx)
                candidate = next((ep for idx, ep in enumerate(eps) if idx > last_completed and not ep.get("is_finished")), None)
                if not candidate:
                    candidate = next((ep for ep in eps if not ep.get("is_finished")), None)
                if candidate:
                    home_next_podcast_episodes.append(
                        {
                            **candidate,
                            "image_url": podcast_image_map.get(key, ""),
                        }
                    )
            home_next_podcast_episodes.sort(key=lambda ep: (str(ep.get("podcast_title") or "").casefold(), podcast_episode_sort_key(str(ep.get("episode_title") or ""), str(ep.get("published_at") or ""))))
            home_next_podcast_episodes = home_next_podcast_episodes[:10]

            home_completed = [b for b in tracked_books_sync if b.get("status") == "completed"][:10]
            home_collected = collected_books[:10]
            home_podcasts = podcast_cards[:10]

    return render_template(
        "dashboard.html",
        user=user,
        tracked=tracked,
        counts=counts,
        recommendations=recommendations,
        q=q,
        provider=provider,
        search_results=search_results,
        search_error=search_error,
        sync_interval=settings_row.get("sync_interval_seconds", 300),
        accounts=accounts,
        sync_rows=sync_rows,
        sync_count=sync_count,
        sync_category_counts=sync_category_counts,
        tracked_books_sync=tracked_books_sync,
        collected_books=collected_books,
        collected_books_sorted=collected_books_sorted,
        podcasts=podcast_cards,
        podcast_episodes=podcast_episodes,
        podcast_episode_total=podcast_episode_total,
        media_view=media_view,
        home_continue=home_continue,
        home_next_series_books=home_next_series_books,
        home_next_podcast_episodes=home_next_podcast_episodes,
        home_completed=home_completed,
        home_collected=home_collected,
        home_podcasts=home_podcasts,
    )


@app.route("/podcasts/<target_id>/<library_item_id>")
@login_required
def podcast_detail(target_id: str, library_item_id: str):
    user = current_user()
    user_id = int(user["id"])
    only_unheard = str(request.args.get("filter") or "").strip().lower() == "unheard"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT target_id, library_item_id, title, author, image_url, itunes_id, itunes_page_url, release_date
                FROM ui_podcast_shows
                WHERE owner_user_id = %s
                  AND target_id = %s
                  AND library_item_id = %s
                LIMIT 1
                """,
                (user_id, target_id, library_item_id),
            )
            podcast = cur.fetchone()
            if not podcast:
                flash("Podcast not found.", "error")
                return redirect(url_for("dashboard", media="podcasts"))

            cur.execute(
                """
                SELECT
                  pe.episode_id,
                  pe.abs_episode_id,
                  pe.abs_presence,
                  pe.episode_title,
                  pe.published_at,
                  COALESCE(pl.progress, 0) AS progress,
                  COALESCE(pl.is_finished, 0) AS is_finished
                FROM ui_podcast_episodes pe
                LEFT JOIN progress_latest pl
                  ON pl.target_id = pe.target_id
                 AND pl.library_item_id = pe.library_item_id
                 AND pl.episode_id = COALESCE(pe.abs_episode_id, pe.episode_id)
                WHERE pe.owner_user_id = %s
                  AND pe.target_id = %s
                  AND pe.library_item_id = %s
                ORDER BY pe.published_at DESC, pe.episode_title ASC
                """,
                (user_id, target_id, library_item_id),
            )
            episode_rows = cur.fetchall()

    episodes = []
    for row in episode_rows:
        progress_ratio = float(row.get("progress") or 0.0)
        progress_pct = max(0.0, min(100.0, progress_ratio * 100.0))
        is_finished = int(row.get("is_finished") or 0) == 1 or progress_ratio >= 0.98
        status = "completed" if is_finished else ("in_progress" if progress_ratio > 0 else "not_started")
        episodes.append(
            {
                "episode_id": row.get("episode_id") or "",
                "abs_episode_id": row.get("abs_episode_id") or "",
                "abs_presence": row.get("abs_presence") or "missing",
                "episode_title": row.get("episode_title") or "",
                "published_at": row.get("published_at") or "",
                "episode_no": parse_episode_number(str(row.get("episode_title") or "")),
                "progress_pct": round(progress_pct, 1),
                "status": status,
            }
        )

    episodes.sort(key=lambda ep: podcast_episode_sort_key(str(ep.get("episode_title") or ""), str(ep.get("published_at") or "")))
    if only_unheard:
        episodes = [ep for ep in episodes if ep.get("status") != "completed"]

    return render_template(
        "podcast_detail.html",
        user=user,
        podcast=podcast,
        episodes=episodes,
        only_unheard=only_unheard,
    )


@app.route("/sync", methods=["GET", "POST"])
@login_required
def sync_settings():
    user = current_user()
    user_id = int(user["id"])
    edit_account_id = int((request.args.get("edit_account_id") or "0").strip() or 0)

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()

        with get_conn() as conn:
            with conn.cursor() as cur:
                if action == "save_account":
                    account_id = (request.form.get("account_id") or "").strip()
                    abs_url = normalize_url(request.form.get("abs_url") or "")
                    abs_username = (request.form.get("abs_username") or "").strip()
                    api_token = (request.form.get("api_token") or "").strip()
                    enabled = 1 if (request.form.get("enabled") == "1") else 0

                    if not abs_url or not abs_username:
                        flash("ABS URL and ABS username are required.", "error")
                    else:
                        update_id = int(account_id) if account_id else None
                        account_name_base = derive_account_name(abs_url, abs_username)
                        account_name = ensure_unique_account_name(cur, user_id, account_name_base, update_id)
                        if account_id:
                            if api_token:
                                cur.execute(
                                    """
                                    UPDATE ui_sync_accounts
                                    SET account_name=%s, abs_url=%s, abs_username=%s, api_token_enc=%s, api_token='',
                                        enabled=%s
                                    WHERE id=%s AND owner_user_id=%s
                                    """,
                                    (
                                        account_name,
                                        abs_url,
                                        abs_username,
                                        encrypt_token(api_token),
                                        enabled,
                                        int(account_id),
                                        user_id,
                                    ),
                                )
                            else:
                                cur.execute(
                                    """
                                    UPDATE ui_sync_accounts
                                    SET account_name=%s, abs_url=%s, abs_username=%s,
                                        enabled=%s
                                    WHERE id=%s AND owner_user_id=%s
                                    """,
                                    (
                                        account_name,
                                        abs_url,
                                        abs_username,
                                        enabled,
                                        int(account_id),
                                        user_id,
                                    ),
                                )
                        else:
                            if not api_token:
                                flash("API token is required for new accounts.", "error")
                            else:
                                cur.execute(
                                    """
                                    INSERT INTO ui_sync_accounts
                                    (owner_user_id, account_name, abs_url, abs_username, api_token, api_token_enc, target_id, server_id, principal_id, enabled)
                                    VALUES (%s,%s,%s,%s,'',%s,%s,%s,%s,%s)
                                    """,
                                    (
                                        user_id,
                                        account_name,
                                        abs_url,
                                        abs_username,
                                        encrypt_token(api_token),
                                        None,
                                        None,
                                        None,
                                        enabled,
                                    ),
                                )
                        flash("Sync account saved.", "ok")

                elif action == "delete_account":
                    account_id = int(request.form.get("account_id") or "0")
                    if account_id > 0:
                        cur.execute(
                            "DELETE FROM ui_sync_accounts WHERE id = %s AND owner_user_id = %s",
                            (account_id, user_id),
                        )
                        flash("Sync account removed.", "ok")

                interval = int((request.form.get("sync_interval_seconds") or "300").strip() or 300)
                if interval < 30:
                    interval = 30
                if interval > 86400:
                    interval = 86400
                cur.execute(
                    """
                    INSERT INTO ui_user_settings (user_id, sync_interval_seconds)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE sync_interval_seconds = VALUES(sync_interval_seconds)
                    """,
                    (user_id, interval),
                )

        write_targets_file()
        global_interval = recalc_global_sync_interval()
        flash(f"Sync interval stored. Effective global interval: {global_interval}s", "ok")
        return redirect(url_for("sync_settings"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT sync_interval_seconds FROM ui_user_settings WHERE user_id = %s", (user_id,))
            settings_row = cur.fetchone() or {"sync_interval_seconds": 300}
            cur.execute(
                """
                SELECT id, abs_url, abs_username, enabled, updated_at
                FROM ui_sync_accounts
                WHERE owner_user_id = %s
                ORDER BY abs_url, abs_username, id
                """,
                (user_id,),
            )
            accounts = cur.fetchall()
            edit_account = None
            if edit_account_id > 0:
                cur.execute(
                    """
                    SELECT id, abs_url, abs_username, enabled
                    FROM ui_sync_accounts
                    WHERE id = %s AND owner_user_id = %s
                    LIMIT 1
                    """,
                    (edit_account_id, user_id),
                )
                edit_account = cur.fetchone()

    return render_template(
        "sync.html",
        user=user,
        settings=settings_row,
        accounts=accounts,
        edit_account=edit_account,
    )


@app.route("/sync/run-now", methods=["POST"])
@login_required
def sync_run_now():
    request_manual_sync()
    flash("Manual sync requested. Worker will run immediately.", "ok")
    return redirect(url_for("sync_settings"))


@app.route("/sync/import-collected", methods=["POST"])
@login_required
def sync_import_collected():
    user_id = int(session["user_id"])
    stats = import_abs_catalog(user_id, import_books=True, import_podcasts=False, enrich_podcasts=False)
    flash(f"Collected import finished: {stats.get('books', 0)} audiobooks imported/updated.", "ok")
    return redirect(url_for("dashboard"))


@app.route("/sync/import-podcasts", methods=["POST"])
@login_required
def sync_import_podcasts():
    user_id = int(session["user_id"])
    stats = import_abs_catalog(user_id, import_books=False, import_podcasts=True, enrich_podcasts=True)
    flash(
        f"Podcast import finished: {stats.get('podcasts', 0)} podcasts and {stats.get('podcast_episodes', 0)} episodes imported/updated.",
        "ok",
    )
    return redirect(url_for("dashboard"))


@app.route("/sync/rebuild-progress", methods=["POST"])
@login_required
def sync_rebuild_progress():
    user_id = int(session["user_id"])
    stats = rebuild_progress_from_abs(user_id)
    flash(
        f"Progress rebuild finished: {stats.get('updated', 0)} updated, {stats.get('in_progress', 0)} in progress, {stats.get('completed', 0)} completed.",
        "ok",
    )
    return redirect(url_for("sync_settings"))


@app.route("/sync/cleanup-collected", methods=["POST"])
@login_required
def sync_cleanup_collected():
    user_id = int(session["user_id"])
    stats = cleanup_collected_library(user_id)
    flash(
        f"Collected cleanup finished: {stats.get('marked_missing', 0)} marked missing, {stats.get('merged_duplicates', 0)} duplicates merged, {stats.get('after', 0)} total.",
        "ok",
    )
    return redirect(url_for("sync_settings"))


@app.route("/matching", methods=["GET", "POST"])
@login_required
def matching_view():
    user = current_user()
    user_id = int(user["id"])

    if request.method == "POST":
        source_value = (request.form.get("source_item") or "").strip()
        ref_value = (request.form.get("reference_item") or "").strip()
        if "|" not in source_value or "|" not in ref_value:
            flash("Please select both source and reference items.", "error")
            return redirect(url_for("matching_view"))
        source_target_id, source_library_item_id = source_value.split("|", 1)
        ref_target_id, ref_library_item_id = ref_value.split("|", 1)
        ok, message = manual_match_items(user_id, source_target_id, source_library_item_id, ref_target_id, ref_library_item_id)
        flash(message, "ok" if ok else "error")
        return redirect(url_for("matching_view"))

    all_rows, unmatched_rows, _ = collect_matching_rows(user_id)
    unmatched_keys = {str(r.get("value_key") or "") for r in unmatched_rows}
    matched_rows = [r for r in all_rows if str(r.get("value_key") or "") not in unmatched_keys]
    return render_template(
        "matching.html",
        user=user,
        all_rows=all_rows,
        matched_rows=matched_rows,
        unmatched_rows=unmatched_rows,
    )


@app.route("/cover/<target_id>/<library_item_id>")
@login_required
def cover_proxy(target_id: str, library_item_id: str):
    user_id = int(session["user_id"])
    creds_map = get_user_target_credentials(user_id)
    target = creds_map.get(target_id)
    if not target:
        return ("", 404)

    try:
        resp = requests.get(
            f"{target['url']}/api/items/{library_item_id}/cover",
            headers={"Authorization": f"Bearer {target['token']}"},
            timeout=10,
        )
        if resp.status_code != 200:
            return ("", resp.status_code)
        return Response(resp.content, mimetype=resp.headers.get("Content-Type", "image/jpeg"))
    except Exception:
        return ("", 502)


@app.route("/abs/open/<target_id>/<library_item_id>")
@login_required
def open_abs_item(target_id: str, library_item_id: str):
    user_id = int(session["user_id"])
    creds_map = get_user_target_credentials(user_id)
    urls_map = get_user_target_urls(user_id)
    target = creds_map.get(target_id)
    base_url = urls_map.get(target_id) or (target.get("url") if target else "")
    if not base_url:
        flash("ABS target not found.", "error")
        return redirect(url_for("dashboard"))

    # Best effort: ask ABS to start/resume playback, then redirect to web item with autoplay query.
    if target and target.get("token"):
        abs_post_optional_json(base_url, str(target.get("token") or ""), f"/api/items/{library_item_id}/play", {})

    abs_url = build_abs_web_item_url(base_url, library_item_id)
    if not abs_url:
        flash("Unable to build ABS playback URL.", "error")
        return redirect(url_for("dashboard"))
    return redirect(abs_url, code=302)


@app.route("/abs/open-next-episode/<target_id>/<library_item_id>")
@login_required
def open_next_podcast_episode(target_id: str, library_item_id: str):
    user_id = int(session["user_id"])

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  pe.episode_id,
                  pe.abs_episode_id,
                  pe.abs_presence,
                  pe.episode_title,
                  pe.published_at,
                  COALESCE(pl.progress, 0) AS progress,
                  COALESCE(pl.is_finished, 0) AS is_finished
                FROM ui_podcast_episodes pe
                LEFT JOIN progress_latest pl
                  ON pl.target_id = pe.target_id
                 AND pl.library_item_id = pe.library_item_id
                 AND pl.episode_id = COALESCE(pe.abs_episode_id, pe.episode_id)
                WHERE pe.owner_user_id = %s
                  AND pe.target_id = %s
                  AND pe.library_item_id = %s
                """,
                (user_id, target_id, library_item_id),
            )
            rows = cur.fetchall()

    candidates: list[dict[str, Any]] = []
    for row in rows:
        progress_ratio = float(row.get("progress") or 0.0)
        is_finished = int(row.get("is_finished") or 0) == 1 or progress_ratio >= 0.98
        if is_finished:
            continue
        candidates.append(
            {
                "episode_id": str(row.get("episode_id") or ""),
                "abs_episode_id": str(row.get("abs_episode_id") or ""),
                "abs_presence": str(row.get("abs_presence") or "missing"),
                "episode_title": str(row.get("episode_title") or ""),
                "published_at": str(row.get("published_at") or ""),
            }
        )

    if not candidates:
        flash("No unheard episode found.", "error")
        return redirect(url_for("podcast_detail", target_id=target_id, library_item_id=library_item_id))

    candidates.sort(key=lambda ep: podcast_episode_sort_key(str(ep.get("episode_title") or ""), str(ep.get("published_at") or "")))
    present_candidates = [ep for ep in candidates if str(ep.get("abs_presence") or "missing") == "present" and str(ep.get("abs_episode_id") or "")]
    next_episode = present_candidates[0] if present_candidates else candidates[0]

    creds_map = get_user_target_credentials(user_id)
    urls_map = get_user_target_urls(user_id)
    target = creds_map.get(target_id)
    base_url = urls_map.get(target_id) or (target.get("url") if target else "")
    if not base_url:
        flash("ABS target not found.", "error")
        return redirect(url_for("podcast_detail", target_id=target_id, library_item_id=library_item_id))

    abs_url = build_abs_web_item_url(base_url, library_item_id)
    if not abs_url:
        flash("Unable to build ABS playback URL.", "error")
        return redirect(url_for("podcast_detail", target_id=target_id, library_item_id=library_item_id))

    abs_episode_id = str(next_episode.get("abs_episode_id") or "")
    if target and target.get("token") and abs_episode_id:
        abs_post_optional_json(
            base_url,
            str(target.get("token") or ""),
            f"/api/items/{library_item_id}/play",
            {"episodeId": abs_episode_id},
        )
        abs_url = append_query_param(abs_url, "episode", abs_episode_id)
        return redirect(abs_url, code=302)

    # Fallback if next episode does not exist in ABS
    flash("Next episode is not available in ABS. Showing podcast details.", "error")
    return redirect(url_for("podcast_detail", target_id=target_id, library_item_id=library_item_id, filter="unheard"))


@app.route("/books/mark-heard", methods=["POST"])
@login_required
def mark_heard():
    user_id = int(session["user_id"])
    title = (request.form.get("title") or "").strip()
    author = (request.form.get("author") or "").strip()
    asin = (request.form.get("asin") or "").strip()
    isbn = (request.form.get("isbn") or "").strip()
    series_name = (request.form.get("series_name") or "").strip()
    series_index_raw = (request.form.get("series_index") or "").strip()
    source = (request.form.get("source") or "manual").strip()

    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("dashboard"))

    enriched = enrich_with_audible(title, author, asin, isbn, series_name, series_index_raw)
    asin = enriched["asin"]
    isbn = enriched["isbn"]
    series_name = enriched["series_name"]
    series_index_raw = enriched["series_index"]
    source = source if source != "manual" else enriched["source"]

    series_index = None
    if series_index_raw:
        try:
            series_index = float(series_index_raw)
        except ValueError:
            series_index = None

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ui_tracked_books
                (owner_user_id, title, author, asin, isbn, series_name, series_index, status, progress, metadata_source)
                VALUES (%s,%s,%s,NULLIF(%s,''),NULLIF(%s,''),NULLIF(%s,''),%s,'heard',1,%s)
                ON DUPLICATE KEY UPDATE
                  author = VALUES(author),
                  series_name = VALUES(series_name),
                  series_index = VALUES(series_index),
                  status = 'heard',
                  progress = 1,
                  metadata_source = VALUES(metadata_source)
                """,
                (user_id, title, author, asin, isbn, series_name, series_index, source),
            )
    flash("Marked as heard.", "ok")
    return redirect(url_for("dashboard"))


@app.route("/books/mark-synced-heard", methods=["POST"])
@login_required
def mark_synced_heard():
    owner_user_id = int(session["user_id"])
    target_id = (request.form.get("target_id") or "").strip()
    library_item_id = (request.form.get("library_item_id") or "").strip()
    redirect_to = (request.form.get("redirect_to") or "dashboard").strip()
    if not target_id or not library_item_id:
        flash("Target and library item are required.", "error")
        return redirect(url_for("dashboard"))

    now_ms = int(time.time() * 1000)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT server_id, principal_id, user_id
                FROM target_state
                WHERE target_id = %s
                LIMIT 1
                """,
                (target_id,),
            )
            target_state = cur.fetchone() or {}

            cur.execute(
                """
                SELECT id, abs_username, target_id, server_id, principal_id
                FROM ui_sync_accounts
                WHERE owner_user_id = %s
                ORDER BY id
                """,
                (owner_user_id,),
            )
            account_rows = cur.fetchall()
            account_match = None
            for row in account_rows:
                resolved = (row.get("target_id") or f"u{owner_user_id}-a{row['id']}").strip()
                if resolved == target_id:
                    account_match = row
                    break

            server_id = (
                str(target_state.get("server_id") or "")
                or str((account_match or {}).get("server_id") or "")
                or target_id
            )
            principal_id = (
                str(target_state.get("principal_id") or "")
                or str((account_match or {}).get("principal_id") or "")
                or target_id
            )
            user_id = (
                str(target_state.get("user_id") or "")
                or str((account_match or {}).get("abs_username") or "")
                or f"ui-{owner_user_id}"
            )

            cur.execute(
                """
                SELECT COALESCE(canonical_key, '') AS canonical_key, COALESCE(duration_sec, 0) AS duration_sec
                FROM item_identity
                WHERE target_id = %s AND library_item_id = %s
                LIMIT 1
                """,
                (target_id, library_item_id),
            )
            identity = cur.fetchone() or {}
            canonical_key = str(identity.get("canonical_key") or "")
            duration = float(identity.get("duration_sec") or 0.0)

            cur.execute(
                """
                SELECT COALESCE(duration, 0) AS duration
                FROM progress_latest
                WHERE target_id = %s
                  AND library_item_id = %s
                  AND episode_id = ''
                ORDER BY last_update_ms DESC
                LIMIT 1
                """,
                (target_id, library_item_id),
            )
            latest = cur.fetchone() or {}
            duration_from_progress = float(latest.get("duration") or 0.0)
            if duration_from_progress > 0:
                duration = duration_from_progress
            if duration <= 0:
                creds_map = get_user_target_credentials(owner_user_id)
                cred = creds_map.get(target_id) or {}
                if cred.get("url") and cred.get("token"):
                    try:
                        detail = abs_get_json(cred["url"], cred["token"], f"/api/items/{library_item_id}")
                        item_media = (detail.get("media") or {}) if isinstance(detail, dict) else {}
                        duration = float(item_media.get("duration") or 0.0)
                    except Exception:
                        duration = duration
            current_time = duration if duration > 0 else 0.0

            cur.execute(
                """
                INSERT INTO progress_outbox
                (target_id, server_id, principal_id, user_id, library_item_id, episode_id, canonical_key, progress, current_time_sec, duration, is_finished, last_update_ms, status)
                VALUES (%s,%s,%s,%s,%s,'',NULLIF(%s,''),1,%s,%s,1,%s,'pending')
                """,
                (target_id, server_id, principal_id, user_id, library_item_id, canonical_key, current_time, duration, now_ms),
            )

            cur.execute(
                """
                INSERT INTO progress_latest
                (target_id, server_id, principal_id, user_id, library_item_id, episode_id, media_progress_id, canonical_key, progress, current_time_sec, duration, is_finished, started_at_ms, finished_at_ms, last_update_ms, source)
                VALUES (%s,%s,%s,%s,%s,'',%s,NULLIF(%s,''),1,%s,%s,1,NULL,%s,%s,'local_push')
                ON DUPLICATE KEY UPDATE
                  server_id = VALUES(server_id),
                  principal_id = VALUES(principal_id),
                  media_progress_id = VALUES(media_progress_id),
                  canonical_key = VALUES(canonical_key),
                  progress = VALUES(progress),
                  current_time_sec = VALUES(current_time_sec),
                  duration = VALUES(duration),
                  is_finished = VALUES(is_finished),
                  finished_at_ms = VALUES(finished_at_ms),
                  last_update_ms = VALUES(last_update_ms),
                  source = VALUES(source)
                """,
                (
                    target_id,
                    server_id,
                    principal_id,
                    user_id,
                    library_item_id,
                    f"ui-local-{now_ms}",
                    canonical_key,
                    current_time,
                    duration,
                    now_ms,
                    now_ms,
                ),
            )

            cur.execute(
                """
                INSERT INTO progress_history
                (target_id, server_id, principal_id, user_id, library_item_id, episode_id, media_progress_id, canonical_key, progress, current_time_sec, duration, is_finished, started_at_ms, finished_at_ms, last_update_ms, source)
                VALUES (%s,%s,%s,%s,%s,'',%s,NULLIF(%s,''),1,%s,%s,1,NULL,%s,%s,'local_push')
                """,
                (
                    target_id,
                    server_id,
                    principal_id,
                    user_id,
                    library_item_id,
                    f"ui-local-{now_ms}",
                    canonical_key,
                    current_time,
                    duration,
                    now_ms,
                    now_ms,
                ),
            )

    request_manual_sync()
    flash("Marked as heard and queued for ABS sync.", "ok")
    if redirect_to == "sync":
        return redirect(url_for("sync_settings"))
    return redirect(url_for("dashboard"))


@app.route("/books/mark-synced-unheard", methods=["POST"])
@login_required
def mark_synced_unheard():
    owner_user_id = int(session["user_id"])
    target_id = (request.form.get("target_id") or "").strip()
    library_item_id = (request.form.get("library_item_id") or "").strip()
    redirect_to = (request.form.get("redirect_to") or "dashboard").strip()
    if not target_id or not library_item_id:
        flash("Target and library item are required.", "error")
        return redirect(url_for("dashboard"))

    now_ms = int(time.time() * 1000)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT server_id, principal_id, user_id
                FROM target_state
                WHERE target_id = %s
                LIMIT 1
                """,
                (target_id,),
            )
            target_state = cur.fetchone() or {}

            cur.execute(
                """
                SELECT id, abs_username, target_id, server_id, principal_id
                FROM ui_sync_accounts
                WHERE owner_user_id = %s
                ORDER BY id
                """,
                (owner_user_id,),
            )
            account_rows = cur.fetchall()
            account_match = None
            for row in account_rows:
                resolved = (row.get("target_id") or f"u{owner_user_id}-a{row['id']}").strip()
                if resolved == target_id:
                    account_match = row
                    break

            server_id = (
                str(target_state.get("server_id") or "")
                or str((account_match or {}).get("server_id") or "")
                or target_id
            )
            principal_id = (
                str(target_state.get("principal_id") or "")
                or str((account_match or {}).get("principal_id") or "")
                or target_id
            )
            user_id = (
                str(target_state.get("user_id") or "")
                or str((account_match or {}).get("abs_username") or "")
                or f"ui-{owner_user_id}"
            )

            cur.execute(
                """
                SELECT COALESCE(canonical_key, '') AS canonical_key, COALESCE(duration_sec, 0) AS duration_sec
                FROM item_identity
                WHERE target_id = %s AND library_item_id = %s
                LIMIT 1
                """,
                (target_id, library_item_id),
            )
            identity = cur.fetchone() or {}
            canonical_key = str(identity.get("canonical_key") or "")
            duration = float(identity.get("duration_sec") or 0.0)

            cur.execute(
                """
                SELECT COALESCE(duration, 0) AS duration
                FROM progress_latest
                WHERE target_id = %s
                  AND library_item_id = %s
                  AND episode_id = ''
                ORDER BY last_update_ms DESC
                LIMIT 1
                """,
                (target_id, library_item_id),
            )
            latest = cur.fetchone() or {}
            duration_from_progress = float(latest.get("duration") or 0.0)
            if duration_from_progress > 0:
                duration = duration_from_progress

            cur.execute(
                """
                INSERT INTO progress_outbox
                (target_id, server_id, principal_id, user_id, library_item_id, episode_id, canonical_key, progress, current_time_sec, duration, is_finished, last_update_ms, status)
                VALUES (%s,%s,%s,%s,%s,'',NULLIF(%s,''),0,0,%s,0,%s,'pending')
                """,
                (target_id, server_id, principal_id, user_id, library_item_id, canonical_key, duration, now_ms),
            )

            cur.execute(
                """
                INSERT INTO progress_latest
                (target_id, server_id, principal_id, user_id, library_item_id, episode_id, media_progress_id, canonical_key, progress, current_time_sec, duration, is_finished, started_at_ms, finished_at_ms, last_update_ms, source)
                VALUES (%s,%s,%s,%s,%s,'',%s,NULLIF(%s,''),0,0,%s,0,NULL,NULL,%s,'local_push')
                ON DUPLICATE KEY UPDATE
                  server_id = VALUES(server_id),
                  principal_id = VALUES(principal_id),
                  media_progress_id = VALUES(media_progress_id),
                  canonical_key = VALUES(canonical_key),
                  progress = VALUES(progress),
                  current_time_sec = VALUES(current_time_sec),
                  duration = VALUES(duration),
                  is_finished = VALUES(is_finished),
                  finished_at_ms = VALUES(finished_at_ms),
                  last_update_ms = VALUES(last_update_ms),
                  source = VALUES(source)
                """,
                (
                    target_id,
                    server_id,
                    principal_id,
                    user_id,
                    library_item_id,
                    f"ui-local-unheard-{now_ms}",
                    canonical_key,
                    duration,
                    now_ms,
                ),
            )

            cur.execute(
                """
                INSERT INTO progress_history
                (target_id, server_id, principal_id, user_id, library_item_id, episode_id, media_progress_id, canonical_key, progress, current_time_sec, duration, is_finished, started_at_ms, finished_at_ms, last_update_ms, source)
                VALUES (%s,%s,%s,%s,%s,'',%s,NULLIF(%s,''),0,0,%s,0,NULL,NULL,%s,'local_push')
                """,
                (
                    target_id,
                    server_id,
                    principal_id,
                    user_id,
                    library_item_id,
                    f"ui-local-unheard-{now_ms}",
                    canonical_key,
                    duration,
                    now_ms,
                ),
            )

    request_manual_sync()
    flash("Marked as unheard and queued for ABS sync.", "ok")
    if redirect_to == "sync":
        return redirect(url_for("sync_settings"))
    return redirect(url_for("dashboard"))


@app.route("/books/manual", methods=["POST"])
@login_required
def add_manual_book():
    user_id = int(session["user_id"])
    title = (request.form.get("title") or "").strip()
    author = (request.form.get("author") or "").strip()
    asin = (request.form.get("asin") or "").strip()
    isbn = (request.form.get("isbn") or "").strip()
    series_name = (request.form.get("series_name") or "").strip()
    series_index_raw = (request.form.get("series_index") or "").strip()

    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("dashboard"))

    enriched = enrich_with_audible(title, author, asin, isbn, series_name, series_index_raw)
    asin = enriched["asin"]
    isbn = enriched["isbn"]
    series_name = enriched["series_name"]
    series_index_raw = enriched["series_index"]

    series_index = None
    if series_index_raw:
        try:
            series_index = float(series_index_raw)
        except ValueError:
            series_index = None

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ui_tracked_books
                (owner_user_id, title, author, asin, isbn, series_name, series_index, status, progress, metadata_source)
                VALUES (%s,%s,%s,NULLIF(%s,''),NULLIF(%s,''),NULLIF(%s,''),%s,'planned',0,%s)
                ON DUPLICATE KEY UPDATE
                  author = VALUES(author),
                  series_name = VALUES(series_name),
                  series_index = VALUES(series_index),
                  metadata_source = VALUES(metadata_source)
                """,
                (user_id, title, author, asin, isbn, series_name, series_index, enriched["source"]),
            )
    flash("Book added.", "ok")
    return redirect(url_for("dashboard"))


@app.route("/history")
@login_required
def history_view():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  pl.target_id, pl.principal_id, pl.user_id, pl.library_item_id, pl.canonical_key,
                  pl.progress, pl.is_finished, pl.last_update_ms, pl.source,
                  ii.title, ii.author, ii.asin
                FROM progress_latest pl
                LEFT JOIN item_identity ii
                  ON ii.target_id = pl.target_id
                 AND ii.library_item_id = pl.library_item_id
                WHERE pl.episode_id = ''
                ORDER BY last_update_ms DESC
                LIMIT 300
                """
            )
            rows = cur.fetchall()
    return render_template("history.html", rows=rows, user=current_user())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
