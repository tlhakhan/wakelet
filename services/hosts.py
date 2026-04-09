import sqlite3
from dataclasses import dataclass
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "hosts.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hosts (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL,
                mac     TEXT NOT NULL
            )
            """
        )


@dataclass
class Host:
    id: int
    name: str
    mac: str


def list_hosts() -> list[Host]:
    with _connect() as conn:
        rows = conn.execute("SELECT id, name, mac FROM hosts ORDER BY name").fetchall()
    return [Host(**row) for row in rows]


def add_host(name: str, mac: str) -> None:
    with _connect() as conn:
        conn.execute("INSERT INTO hosts (name, mac) VALUES (?, ?)", (name, mac))


def get_host(host_id: int) -> Host | None:
    with _connect() as conn:
        row = conn.execute("SELECT id, name, mac FROM hosts WHERE id = ?", (host_id,)).fetchone()
    return Host(**row) if row else None


def remove_host(host_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM hosts WHERE id = ?", (host_id,))
