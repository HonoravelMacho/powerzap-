"""Camada de persistência local com SQLite."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "powerzap",
)
DB_PATH = os.path.join(DB_DIR, "powerzap.db")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def conn():
    os.makedirs(DB_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#2196f3'
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL,
    text TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    tag_id INTEGER REFERENCES tags(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pendente',
    sent_at TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_status_time
    ON messages(status, scheduled_at);
"""


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)


# ---------------- Configurações ----------------

DEFAULT_SETTINGS = {
    "evolution_url": "http://localhost:8080",
    "api_key": "powerzap",
    "instance": "powerzap",
}


def get_settings() -> dict:
    init_db()
    with conn() as c:
        rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}
    return {**DEFAULT_SETTINGS, **rows}


def set_setting(key: str, value: str):
    with conn() as c:
        c.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


# ---------------- Etiquetas ----------------

def list_tags():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM tags ORDER BY name")]


def create_tag(name: str, color: str):
    with conn() as c:
        c.execute("INSERT INTO tags(name, color) VALUES(?, ?)", (name, color))


def update_tag(tag_id: int, name: str, color: str):
    with conn() as c:
        c.execute(
            "UPDATE tags SET name=?, color=? WHERE id=?", (name, color, tag_id)
        )


def delete_tag(tag_id: int):
    with conn() as c:
        c.execute("DELETE FROM tags WHERE id=?", (tag_id,))


# ---------------- Mensagens ----------------

def list_messages(day: str | None = None):
    query = (
        "SELECT m.*, t.name AS tag_name, t.color AS tag_color "
        "FROM messages m LEFT JOIN tags t ON t.id = m.tag_id "
    )
    params: list = []
    if day:
        query += "WHERE date(m.scheduled_at) = ? "
        params.append(day)
    query += "ORDER BY m.scheduled_at DESC"
    with conn() as c:
        return [dict(r) for r in c.execute(query, params)]


def list_pending(now: str):
    with conn() as c:
        return [
            dict(r)
            for r in c.execute(
                "SELECT * FROM messages "
                "WHERE status='pendente' AND scheduled_at <= ? "
                "ORDER BY scheduled_at",
                (now,),
            )
        ]


def create_message(number: str, text: str, scheduled_at: str, tag_id: int | None):
    with conn() as c:
        c.execute(
            "INSERT INTO messages(number, text, scheduled_at, tag_id, created_at) "
            "VALUES(?, ?, ?, ?, ?)",
            (number, text, scheduled_at, tag_id, _now()),
        )


def update_message(msg_id: int, number: str, text: str, scheduled_at: str, tag_id: int | None):
    with conn() as c:
        c.execute(
            "UPDATE messages SET number=?, text=?, scheduled_at=?, tag_id=? WHERE id=?",
            (number, text, scheduled_at, tag_id, msg_id),
        )


def delete_message(msg_id: int):
    with conn() as c:
        c.execute("DELETE FROM messages WHERE id=?", (msg_id,))


def mark_sent(msg_id: int):
    with conn() as c:
        c.execute(
            "UPDATE messages SET status='enviada', sent_at=? WHERE id=?",
            (_now(), msg_id),
        )


def mark_failed(msg_id: int, error: str):
    with conn() as c:
        c.execute(
            "UPDATE messages SET status='falhou', error=? WHERE id=?",
            (error[:500], msg_id),
        )
