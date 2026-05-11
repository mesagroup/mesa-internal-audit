"""
Inizializza il database SQLite e carica i controlli default dal POC.
Eseguire una volta: python -m db.init_db
"""
import json
import sys
from pathlib import Path

# allow running as script from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import get_conn, DB_PATH
from core.controls_tree import CONTROLS_TREE

SCHEMA = Path(__file__).parent / "schema.sql"


def init_db(force: bool = False) -> None:
    if force and DB_PATH.exists():
        DB_PATH.unlink()

    conn = get_conn()
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()
    _seed_controls(conn)
    conn.close()
    print(f"DB pronto: {DB_PATH}")


def _seed_controls(conn) -> None:
    count = conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0]
    if count > 0:
        return
    for c in CONTROLS_TREE:
        conn.execute(
            """INSERT OR IGNORE INTO controls
               (id, title, area, description, check_points, expected_documents)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                c.id, c.title, c.area, c.description,
                json.dumps(c.check_points, ensure_ascii=False),
                json.dumps(c.expected_documents, ensure_ascii=False),
            ),
        )
    conn.commit()
    print(f"  {len(CONTROLS_TREE)} controlli default caricati.")


if __name__ == "__main__":
    init_db()
