import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "audit.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
