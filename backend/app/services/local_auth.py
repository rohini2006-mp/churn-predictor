from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DB_PATH = Path(os.getenv("LOCAL_AUTH_DB", "data/local_auth.sqlite3"))
SESSIONS: dict[str, dict[str, str]] = {}


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """create table if not exists users (
        id text primary key, email text unique not null, display_name text not null,
        password_hash text not null, created_at text not null)"""
    )
    connection.commit()
    return connection


def _hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def _verify(password: str, encoded: str) -> bool:
    salt_text, digest_text = encoded.split("$", 1)
    salt = base64.urlsafe_b64decode(salt_text.encode())
    expected = base64.urlsafe_b64decode(digest_text.encode())
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return hmac.compare_digest(actual, expected)


def _user(row: sqlite3.Row) -> dict[str, str]:
    return {"id": row["id"], "email": row["email"], "display_name": row["display_name"]}


def signup(email: str, password: str, display_name: str) -> dict[str, str]:
    user = {
        "id": str(uuid4()),
        "email": email.strip().lower(),
        "display_name": display_name.strip(),
    }
    connection = _db()
    try:
        connection.execute(
            "insert into users (id,email,display_name,password_hash,created_at) values (?,?,?,?,?)",
            (user["id"], user["email"], user["display_name"], _hash(password), datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("An account with this email already exists") from exc
    finally:
        connection.close()
    return user


def login(email: str, password: str) -> dict[str, str] | None:
    connection = _db()
    row = connection.execute("select * from users where email = ?", (email.strip().lower(),)).fetchone()
    connection.close()
    if row is None or not _verify(password, row["password_hash"]):
        return None
    return _user(row)


def create_session(user: dict[str, str]) -> str:
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = user
    return token


def get_session(token: str | None) -> dict[str, str] | None:
    return SESSIONS.get(token or "")


def delete_session(token: str | None) -> None:
    if token:
        SESSIONS.pop(token, None)