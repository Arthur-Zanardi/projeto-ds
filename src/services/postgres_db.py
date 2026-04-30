from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.schema.schema_vetores import (
    DEFAULT_VISIBLE_FIELDS,
    default_profile_vectors,
    merge_interests_override,
    merge_physical_profile,
    normalize_profile_vectors,
    top_interests_summary,
)


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://matchai:matchai@127.0.0.1:5432/matchai",
)


def _connect():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError(
            "Dependencia psycopg ausente. Instale as dependencias do requirements.txt."
        ) from exc

    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _jsonb(value: Any):
    from psycopg.types.json import Jsonb

    return Jsonb(value)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(18)}"


def init_database() -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    display_name TEXT NOT NULL,
                    auth_provider TEXT NOT NULL DEFAULT 'password',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    deleted_at TIMESTAMPTZ
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    display_name TEXT NOT NULL DEFAULT '',
                    bio TEXT NOT NULL DEFAULT '',
                    profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    vector_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    visible_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
                    interests_override JSONB NOT NULL DEFAULT '{}'::jsonb,
                    photo_path TEXT NOT NULL DEFAULT '',
                    physical_questionnaire_completed BOOLEAN NOT NULL DEFAULT false,
                    accessibility_mode BOOLEAN NOT NULL DEFAULT false,
                    ui_font_scale DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                    theme_mode TEXT NOT NULL DEFAULT 'light',
                    chat_font_scale DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS photo_path TEXT NOT NULL DEFAULT ''")
            cur.execute(
                "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS physical_questionnaire_completed BOOLEAN NOT NULL DEFAULT false"
            )
            cur.execute(
                "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS accessibility_mode BOOLEAN NOT NULL DEFAULT false"
            )
            cur.execute(
                "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS ui_font_scale DOUBLE PRECISION NOT NULL DEFAULT 1.0"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_chat_messages (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    remetente TEXT NOT NULL CHECK (remetente IN ('usuario', 'ia')),
                    mensagem TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_vector_snapshots (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    vector_json JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS value_filters (
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    key TEXT NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT true,
                    min_value DOUBLE PRECISION,
                    max_value DOUBLE PRECISION,
                    max_delta DOUBLE PRECISION,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (user_id, key)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS matches (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    matched_user_id TEXT NOT NULL,
                    matched_name TEXT NOT NULL,
                    affinity DOUBLE PRECISION NOT NULL,
                    distance DOUBLE PRECISION NOT NULL,
                    explanation TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'matched',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (user_id, matched_user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS match_messages (
                    id BIGSERIAL PRIMARY KEY,
                    match_id TEXT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                    sender_user_id TEXT NOT NULL,
                    mensagem TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
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
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    expires_at TIMESTAMPTZ NOT NULL
                )
                """
            )


def create_user(
    email: str,
    password_hash: str | None,
    display_name: str,
    auth_provider: str = "password",
) -> dict[str, Any]:
    user_id = _new_id("user")
    normalized_email = email.lower().strip()
    name = (display_name or normalized_email.split("@", 1)[0]).strip()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, password_hash, display_name, auth_provider)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, normalized_email, password_hash, name, auth_provider),
            )
            user = dict(cur.fetchone())
            _ensure_profile(cur, user_id, name)
            return user


def _ensure_profile(cur, user_id: str, display_name: str) -> None:
    cur.execute(
        """
        INSERT INTO profiles (
            user_id, display_name, profile_json, vector_json,
            visible_fields, interests_override
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
        """,
        (
            user_id,
            display_name,
            _jsonb(default_profile_vectors()),
            _jsonb(default_profile_vectors()),
            _jsonb(DEFAULT_VISIBLE_FIELDS),
            _jsonb({}),
        ),
    )


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE email = %s AND deleted_at IS NULL",
                (email.lower().strip(),),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE id = %s AND deleted_at IS NULL",
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def upsert_google_user(email: str, display_name: str) -> dict[str, Any]:
    normalized_email = email.lower().strip()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, display_name, auth_provider)
                VALUES (%s, %s, %s, 'google')
                ON CONFLICT (email) DO UPDATE
                    SET display_name = EXCLUDED.display_name,
                        auth_provider = CASE
                            WHEN users.auth_provider = 'password' THEN users.auth_provider
                            ELSE 'google'
                        END
                RETURNING *
                """,
                (_new_id("user"), normalized_email, display_name),
            )
            user = dict(cur.fetchone())
            _ensure_profile(cur, user["id"], user["display_name"])
            return user


def get_profile(user_id: str) -> dict[str, Any]:
    with _connect() as conn:
        with conn.cursor() as cur:
            user = get_user_by_id(user_id)
            if not user:
                raise ValueError("Usuario nao encontrado.")
            _ensure_profile(cur, user_id, user["display_name"])
            cur.execute("SELECT * FROM profiles WHERE user_id = %s", (user_id,))
            row = dict(cur.fetchone())
            return _profile_row(row)


def _profile_row(row: dict[str, Any]) -> dict[str, Any]:
    profile_json = normalize_profile_vectors(row.get("profile_json"))
    interests_override = row.get("interests_override") or {}
    vector_json = merge_interests_override(row.get("vector_json") or profile_json, interests_override)
    visible_fields = {**DEFAULT_VISIBLE_FIELDS, **(row.get("visible_fields") or {})}
    vector_json = normalize_profile_vectors(vector_json)
    return {
        **row,
        "profile_json": profile_json,
        "vector_json": vector_json,
        "visible_fields": visible_fields,
        "interests_override": interests_override,
        "photo_path": row.get("photo_path") or "",
        "physical_questionnaire_completed": bool(row.get("physical_questionnaire_completed", False)),
        "accessibility_mode": bool(row.get("accessibility_mode", False)),
        "ui_font_scale": float(row.get("ui_font_scale") or 1.0),
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
    }
    fields = {key: value for key, value in updates.items() if key in allowed and value is not None}
    if not fields:
        return get_profile(user_id)

    assignments: list[str] = []
    params: list[Any] = []
    for key, value in fields.items():
        assignments.append(f"{key} = %s")
        if key in {"visible_fields", "interests_override"}:
            params.append(_jsonb(value))
        else:
            params.append(value)

    params.append(user_id)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE profiles
                SET {", ".join(assignments)}, updated_at = now()
                WHERE user_id = %s
                RETURNING *
                """,
                params,
            )
            row = dict(cur.fetchone())
            if "display_name" in fields:
                cur.execute(
                    "UPDATE users SET display_name = %s WHERE id = %s",
                    (fields["display_name"], user_id),
                )
            return _profile_row(row)


def save_profile_vectors(user_id: str, profile_json: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_profile_vectors(profile_json)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE profiles
                SET profile_json = %s, vector_json = %s, updated_at = now()
                WHERE user_id = %s
                RETURNING *
                """,
                (_jsonb(normalized), _jsonb(normalized), user_id),
            )
            row = dict(cur.fetchone())
            cur.execute(
                """
                INSERT INTO profile_vector_snapshots (user_id, vector_json)
                VALUES (%s, %s)
                """,
                (user_id, _jsonb(normalized)),
            )
            return _profile_row(row)


def save_physical_profile(user_id: str, physical: dict[str, Any]) -> dict[str, Any]:
    current = get_profile(user_id)
    merged = merge_physical_profile(current.get("vector_json"), physical)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE profiles
                SET profile_json = %s,
                    vector_json = %s,
                    physical_questionnaire_completed = true,
                    updated_at = now()
                WHERE user_id = %s
                RETURNING *
                """,
                (_jsonb(merged), _jsonb(merged), user_id),
            )
            row = dict(cur.fetchone())
            cur.execute(
                """
                INSERT INTO profile_vector_snapshots (user_id, vector_json)
                VALUES (%s, %s)
                """,
                (user_id, _jsonb(merged)),
            )
            return _profile_row(row)


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
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO profile_chat_messages (user_id, remetente, mensagem)
                VALUES (%s, %s, %s)
                """,
                (user_id, remetente, mensagem),
            )


def list_profile_chat_messages(user_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, remetente, mensagem, created_at
                FROM profile_chat_messages
                WHERE user_id = %s
                ORDER BY id ASC
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def upsert_value_filters(user_id: str, filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            for item in filters:
                cur.execute(
                    """
                    INSERT INTO value_filters
                        (user_id, key, active, min_value, max_value, max_delta, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (user_id, key) DO UPDATE SET
                        active = EXCLUDED.active,
                        min_value = EXCLUDED.min_value,
                        max_value = EXCLUDED.max_value,
                        max_delta = EXCLUDED.max_delta,
                        updated_at = now()
                    """,
                    (
                        user_id,
                        item["key"],
                        bool(item.get("active", True)),
                        item.get("min_value"),
                        item.get("max_value"),
                        item.get("max_delta"),
                    ),
                )
    return list_value_filters(user_id)


def list_value_filters(user_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT key, active, min_value, max_value, max_delta
                FROM value_filters
                WHERE user_id = %s
                ORDER BY key ASC
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def create_or_update_match(
    user_id: str,
    matched_user_id: str,
    matched_name: str,
    affinity: float,
    distance: float,
    explanation: str,
) -> dict[str, Any]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO matches
                    (id, user_id, matched_user_id, matched_name, affinity, distance, explanation)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, matched_user_id) DO UPDATE SET
                    affinity = EXCLUDED.affinity,
                    distance = EXCLUDED.distance,
                    explanation = EXCLUDED.explanation,
                    created_at = now()
                RETURNING *
                """,
                (
                    _new_id("match"),
                    user_id,
                    matched_user_id,
                    matched_name,
                    affinity,
                    distance,
                    explanation,
                ),
            )
            return dict(cur.fetchone())


def list_matches(user_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM matches
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def get_match(match_id: str, user_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM matches
                WHERE id = %s AND user_id = %s
                """,
                (match_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def save_match_message(match_id: str, sender_user_id: str, mensagem: str) -> dict[str, Any]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO match_messages (match_id, sender_user_id, mensagem)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (match_id, sender_user_id, mensagem),
            )
            return dict(cur.fetchone())


def list_match_messages(match_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM match_messages
                WHERE match_id = %s
                ORDER BY id ASC
                """,
                (match_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def create_oauth_session(state: str) -> None:
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO oauth_login_sessions (state, expires_at)
                VALUES (%s, %s)
                ON CONFLICT (state) DO UPDATE SET
                    token = NULL,
                    email = NULL,
                    display_name = NULL,
                    error = NULL,
                    created_at = now(),
                    expires_at = EXCLUDED.expires_at
                """,
                (state, expires_at),
            )


def complete_oauth_session(
    state: str,
    token: str,
    email: str,
    display_name: str,
) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE oauth_login_sessions
                SET token = %s, email = %s, display_name = %s, error = NULL
                WHERE state = %s
                """,
                (token, email, display_name, state),
            )


def fail_oauth_session(state: str, error: str) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE oauth_login_sessions
                SET error = %s
                WHERE state = %s
                """,
                (error, state),
            )


def get_oauth_session(state: str) -> dict[str, Any] | None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM oauth_login_sessions
                WHERE state = %s AND expires_at > now()
                """,
                (state,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def export_user_data(user_id: str) -> dict[str, Any]:
    return {
        "user": get_user_by_id(user_id),
        "profile": get_profile(user_id),
        "value_filters": list_value_filters(user_id),
        "profile_chat_messages": list_profile_chat_messages(user_id),
        "matches": list_matches(user_id),
    }


def delete_profile_data(user_id: str) -> dict[str, str]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM profile_chat_messages WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM profile_vector_snapshots WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM value_filters WHERE user_id = %s", (user_id,))
            cur.execute(
                "DELETE FROM match_messages WHERE match_id IN (SELECT id FROM matches WHERE user_id = %s)",
                (user_id,),
            )
            cur.execute("DELETE FROM matches WHERE user_id = %s", (user_id,))
            cur.execute(
                """
                UPDATE profiles
                SET bio = '',
                    profile_json = %s,
                    vector_json = %s,
                    visible_fields = %s,
                    interests_override = '{}'::jsonb,
                    photo_path = '',
                    physical_questionnaire_completed = false,
                    updated_at = now()
                WHERE user_id = %s
                """,
                (
                    _jsonb(default_profile_vectors()),
                    _jsonb(default_profile_vectors()),
                    _jsonb(DEFAULT_VISIBLE_FIELDS),
                    user_id,
                ),
            )
    return {"mensagem": "Dados de perfil apagados com sucesso."}


def migrate_sqlite_to_postgres(
    sqlite_path: str = "banco_relacional.db",
    legacy_email: str = "legado@matchai.local",
) -> dict[str, Any]:
    db_path = Path(sqlite_path)
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite nao encontrado: {sqlite_path}")

    init_database()
    user = get_user_by_email(legacy_email)
    if not user:
        user = create_user(
            email=legacy_email,
            password_hash=None,
            display_name="Perfil legado",
            auth_provider="legacy",
        )

    sqlite_conn = sqlite3.connect(str(db_path))
    sqlite_conn.row_factory = sqlite3.Row
    try:
        messages = sqlite_conn.execute(
            """
            SELECT remetente, mensagem
            FROM historico_chat
            ORDER BY id ASC
            """
        ).fetchall()
        vectors = sqlite_conn.execute(
            """
            SELECT vetores_json
            FROM vetores_salvos
            ORDER BY id ASC
            """
        ).fetchall()
    finally:
        sqlite_conn.close()

    for row in messages:
        save_profile_chat_message(user["id"], row["remetente"], row["mensagem"])

    latest_profile: dict[str, Any] | None = None
    for row in vectors:
        try:
            latest_profile = json.loads(row["vetores_json"])
        except json.JSONDecodeError:
            continue

    if latest_profile:
        save_profile_vectors(user["id"], latest_profile)

    return {
        "legacy_user_id": user["id"],
        "messages_imported": len(messages),
        "vectors_seen": len(vectors),
    }
