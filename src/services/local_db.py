from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from src.schema.schema_vetores import (
    DEFAULT_VISIBLE_FIELDS,
    default_profile_vectors,
    merge_interests_override,
    merge_physical_profile,
    normalize_profile_vectors,
    top_interests_summary,
)


DB_PATH = os.getenv("MATCHAI_SQLITE_PATH", "matchai_local.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(18)}"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def init_database() -> None:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                display_name TEXT NOT NULL,
                auth_provider TEXT NOT NULL DEFAULT 'password',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL DEFAULT '',
                bio TEXT NOT NULL DEFAULT '',
                profile_json TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                visible_fields TEXT NOT NULL,
                interests_override TEXT NOT NULL,
                photo_path TEXT NOT NULL DEFAULT '',
                physical_questionnaire_completed INTEGER NOT NULL DEFAULT 0,
                gender_identity TEXT NOT NULL DEFAULT 'nao_informar',
                interested_in TEXT NOT NULL DEFAULT 'nao_informar',
                accessibility_mode INTEGER NOT NULL DEFAULT 0,
                ui_font_scale REAL NOT NULL DEFAULT 1.0,
                theme_mode TEXT NOT NULL DEFAULT 'light',
                chat_font_scale REAL NOT NULL DEFAULT 1.0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for statement in (
            "ALTER TABLE profiles ADD COLUMN photo_path TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE profiles ADD COLUMN physical_questionnaire_completed INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE profiles ADD COLUMN gender_identity TEXT NOT NULL DEFAULT 'nao_informar'",
            "ALTER TABLE profiles ADD COLUMN interested_in TEXT NOT NULL DEFAULT 'nao_informar'",
            "ALTER TABLE profiles ADD COLUMN accessibility_mode INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE profiles ADD COLUMN ui_font_scale REAL NOT NULL DEFAULT 1.0",
            "ALTER TABLE profiles ADD COLUMN theme_mode TEXT NOT NULL DEFAULT 'light'",
            "ALTER TABLE profiles ADD COLUMN chat_font_scale REAL NOT NULL DEFAULT 1.0",
        ):
            try:
                cur.execute(statement)
            except sqlite3.OperationalError:
                pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                remetente TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_vector_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS value_filters (
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                min_value REAL,
                max_value REAL,
                max_delta REAL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, key)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                matched_user_id TEXT NOT NULL,
                matched_name TEXT NOT NULL,
                affinity REAL NOT NULL,
                distance REAL NOT NULL,
                explanation TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'matched',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, matched_user_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS match_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                sender_user_id TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_login_sessions (
                state TEXT PRIMARY KEY,
                token TEXT,
                email TEXT,
                display_name TEXT,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def create_user(
    email: str,
    password_hash: str | None,
    display_name: str,
    auth_provider: str = "password",
) -> dict[str, Any]:
    init_database()
    user_id = _new_id("user")
    normalized_email = email.lower().strip()
    name = (display_name or normalized_email.split("@", 1)[0]).strip()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (id, email, password_hash, display_name, auth_provider)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, normalized_email, password_hash, name, auth_provider),
        )
        _ensure_profile(cur, user_id, name)
        conn.commit()
    return get_user_by_id(user_id) or {}


def _ensure_profile(cur, user_id: str, display_name: str) -> None:
    cur.execute("SELECT user_id FROM profiles WHERE user_id = ?", (user_id,))
    if cur.fetchone():
        return
    defaults = default_profile_vectors()
    cur.execute(
        """
        INSERT INTO profiles (
            user_id, display_name, profile_json, vector_json,
            visible_fields, interests_override
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            display_name,
            _json(defaults),
            _json(defaults),
            _json(DEFAULT_VISIBLE_FIELDS),
            _json({}),
        ),
    )


def get_user_by_email(email: str) -> dict[str, Any] | None:
    init_database()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND deleted_at IS NULL",
            (email.lower().strip(),),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    init_database()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ? AND deleted_at IS NULL",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def upsert_google_user(email: str, display_name: str) -> dict[str, Any]:
    user = get_user_by_email(email)
    if user:
        with _connect() as conn:
            conn.execute(
                "UPDATE users SET display_name = ? WHERE id = ?",
                (display_name, user["id"]),
            )
            conn.commit()
        return get_user_by_id(user["id"]) or user
    return create_user(email, None, display_name, "google")


def get_profile(user_id: str) -> dict[str, Any]:
    init_database()
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Usuário não encontrado.")
    with _connect() as conn:
        cur = conn.cursor()
        _ensure_profile(cur, user_id, user["display_name"])
        conn.commit()
        row = cur.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return _profile_row(dict(row))


def _profile_row(row: dict[str, Any]) -> dict[str, Any]:
    profile_json = normalize_profile_vectors(_load_json(row.get("profile_json"), {}))
    interests_override = _load_json(row.get("interests_override"), {})
    vector_json = merge_interests_override(
        _load_json(row.get("vector_json"), profile_json),
        interests_override,
    )
    vector_json = normalize_profile_vectors(vector_json)
    visible_fields = {**DEFAULT_VISIBLE_FIELDS, **_load_json(row.get("visible_fields"), {})}
    return {
        **row,
        "profile_json": profile_json,
        "vector_json": vector_json,
        "visible_fields": visible_fields,
        "interests_override": interests_override,
        "physical_questionnaire_completed": bool(row.get("physical_questionnaire_completed")),
        "gender_identity": row.get("gender_identity") or "nao_informar",
        "interested_in": row.get("interested_in") or "nao_informar",
        "accessibility_mode": bool(row.get("accessibility_mode")),
        "ui_font_scale": float(row.get("ui_font_scale") or 1.0),
        "chat_font_scale": float(row.get("chat_font_scale") or 1.0),
        "top_interests_summary": top_interests_summary(vector_json),
    }


def update_profile(user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "display_name",
        "bio",
        "theme_mode",
        "chat_font_scale",
        "ui_font_scale",
        "accessibility_mode",
        "visible_fields",
        "interests_override",
        "photo_path",
        "physical_questionnaire_completed",
        "gender_identity",
        "interested_in",
    }
    fields = {key: value for key, value in updates.items() if key in allowed and value is not None}
    if not fields:
        return get_profile(user_id)

    assignments = []
    params: list[Any] = []
    for key, value in fields.items():
        assignments.append(f"{key} = ?")
        if key in {"visible_fields", "interests_override"}:
            params.append(_json(value))
        elif key in {"accessibility_mode", "physical_questionnaire_completed"}:
            params.append(1 if value else 0)
        else:
            params.append(value)
    params.append(user_id)

    with _connect() as conn:
        conn.execute(
            f"UPDATE profiles SET {', '.join(assignments)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            params,
        )
        if "display_name" in fields:
            conn.execute(
                "UPDATE users SET display_name = ? WHERE id = ?",
                (fields["display_name"], user_id),
            )
        conn.commit()
    return get_profile(user_id)


def save_profile_vectors(user_id: str, profile_json: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_profile_vectors(profile_json)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE profiles
            SET profile_json = ?, vector_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (_json(normalized), _json(normalized), user_id),
        )
        conn.execute(
            "INSERT INTO profile_vector_snapshots (user_id, vector_json) VALUES (?, ?)",
            (user_id, _json(normalized)),
        )
        conn.commit()
    return get_profile(user_id)


def save_physical_profile(user_id: str, physical: dict[str, Any]) -> dict[str, Any]:
    current = get_profile(user_id)
    merged = merge_physical_profile(current.get("vector_json"), physical)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE profiles
            SET profile_json = ?, vector_json = ?,
                physical_questionnaire_completed = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (_json(merged), _json(merged), user_id),
        )
        conn.execute(
            "INSERT INTO profile_vector_snapshots (user_id, vector_json) VALUES (?, ?)",
            (user_id, _json(merged)),
        )
        conn.commit()
    return get_profile(user_id)


def update_profile_photo(user_id: str, photo_path: str) -> dict[str, Any]:
    return update_profile(user_id, {"photo_path": photo_path})


def get_profile_readiness(user_id: str) -> dict[str, Any]:
    profile = get_profile(user_id)
    messages = list_profile_chat_messages(user_id)
    user_messages = [item for item in messages if item.get("remetente") == "usuario"]
    missing: list[str] = []
    if not profile.get("physical_questionnaire_completed"):
        missing.append("questionario_fisico")
    if len(user_messages) < 3:
        missing.append("conversa_ia")
    return {
        "ready": not missing,
        "missing": missing,
        "physical_questionnaire_completed": profile.get("physical_questionnaire_completed", False),
        "user_message_count": len(user_messages),
        "minimum_user_messages": 3,
    }


def save_profile_chat_message(user_id: str, remetente: str, mensagem: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO profile_chat_messages (user_id, remetente, mensagem) VALUES (?, ?, ?)",
            (user_id, remetente, mensagem),
        )
        conn.commit()


def list_profile_chat_messages(user_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, remetente, mensagem, created_at
            FROM profile_chat_messages
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def upsert_value_filters(user_id: str, filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with _connect() as conn:
        for item in filters:
            conn.execute(
                """
                INSERT INTO value_filters
                    (user_id, key, active, min_value, max_value, max_delta, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, key) DO UPDATE SET
                    active = excluded.active,
                    min_value = excluded.min_value,
                    max_value = excluded.max_value,
                    max_delta = excluded.max_delta,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    item["key"],
                    1 if item.get("active", True) else 0,
                    item.get("min_value"),
                    item.get("max_value"),
                    item.get("max_delta"),
                ),
            )
        conn.commit()
    return list_value_filters(user_id)


def list_value_filters(user_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT key, active, min_value, max_value, max_delta
            FROM value_filters
            WHERE user_id = ?
            ORDER BY key ASC
            """,
            (user_id,),
        ).fetchall()
        result = [dict(row) for row in rows]
        for item in result:
            item["active"] = bool(item["active"])
        return result


def create_or_update_match(
    user_id: str,
    matched_user_id: str,
    matched_name: str,
    affinity: float,
    distance: float,
    explanation: str,
) -> dict[str, Any]:
    with _connect() as conn:
        existing = conn.execute(
            "SELECT id FROM matches WHERE user_id = ? AND matched_user_id = ?",
            (user_id, matched_user_id),
        ).fetchone()
        match_id = existing["id"] if existing else _new_id("match")
        conn.execute(
            """
            INSERT INTO matches
                (id, user_id, matched_user_id, matched_name, affinity, distance, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, matched_user_id) DO UPDATE SET
                affinity = excluded.affinity,
                distance = excluded.distance,
                explanation = excluded.explanation,
                created_at = CURRENT_TIMESTAMP
            """,
            (match_id, user_id, matched_user_id, matched_name, affinity, distance, explanation),
        )
        conn.commit()
    return get_match(match_id, user_id) or {}


def list_matches(user_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM matches WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_match(match_id: str, user_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM matches WHERE id = ? AND user_id = ?",
            (match_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def save_match_message(match_id: str, sender_user_id: str, mensagem: str) -> dict[str, Any]:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO match_messages (match_id, sender_user_id, mensagem) VALUES (?, ?, ?)",
            (match_id, sender_user_id, mensagem),
        )
        message_id = cur.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM match_messages WHERE id = ?", (message_id,)).fetchone()
        return dict(row)


def list_match_messages(match_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM match_messages WHERE match_id = ? ORDER BY id ASC",
            (match_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def create_oauth_session(state: str) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO oauth_login_sessions (state, expires_at)
            VALUES (?, ?)
            ON CONFLICT(state) DO UPDATE SET
                token = NULL,
                email = NULL,
                display_name = NULL,
                error = NULL,
                created_at = CURRENT_TIMESTAMP,
                expires_at = excluded.expires_at
            """,
            (state, expires_at.isoformat()),
        )
        conn.commit()


def complete_oauth_session(state: str, token: str, email: str, display_name: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE oauth_login_sessions
            SET token = ?, email = ?, display_name = ?, error = NULL
            WHERE state = ?
            """,
            (token, email, display_name, state),
        )
        conn.commit()


def fail_oauth_session(state: str, error: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE oauth_login_sessions SET error = ? WHERE state = ?",
            (error, state),
        )
        conn.commit()


def get_oauth_session(state: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM oauth_login_sessions WHERE state = ?",
            (state,),
        ).fetchone()
        if not row:
            return None
        session = dict(row)
        try:
            expires_at = datetime.fromisoformat(session["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                return None
        except ValueError:
            return None
        return session


def export_user_data(user_id: str) -> dict[str, Any]:
    return {
        "user": get_user_by_id(user_id),
        "profile": get_profile(user_id),
        "value_filters": list_value_filters(user_id),
        "profile_chat_messages": list_profile_chat_messages(user_id),
        "matches": list_matches(user_id),
    }


def delete_profile_data(user_id: str) -> dict[str, str]:
    defaults = default_profile_vectors()
    with _connect() as conn:
        conn.execute("DELETE FROM profile_chat_messages WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM profile_vector_snapshots WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM value_filters WHERE user_id = ?", (user_id,))
        conn.execute(
            "DELETE FROM match_messages WHERE match_id IN (SELECT id FROM matches WHERE user_id = ?)",
            (user_id,),
        )
        conn.execute("DELETE FROM matches WHERE user_id = ?", (user_id,))
        conn.execute(
            """
            UPDATE profiles
            SET bio = '',
                profile_json = ?,
                vector_json = ?,
                visible_fields = ?,
                interests_override = ?,
                photo_path = '',
                physical_questionnaire_completed = 0,
                gender_identity = 'nao_informar',
                interested_in = 'nao_informar',
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (_json(defaults), _json(defaults), _json(DEFAULT_VISIBLE_FIELDS), _json({}), user_id),
        )
        conn.commit()
    return {"mensagem": "Dados de perfil apagados com sucesso."}
