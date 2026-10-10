import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS support_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        facility_id TEXT NOT NULL,
                        requester_name TEXT NOT NULL,
                        contact TEXT NOT NULL,
                        requested_at TEXT NOT NULL,
                        request_type TEXT NOT NULL
                            CHECK (request_type IN ('companion', 'mobility')),
                        note TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_support_requests_status
                        ON support_requests(status, id DESC);

                    CREATE TABLE IF NOT EXISTS field_checks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cell_id TEXT NOT NULL,
                        checklist TEXT NOT NULL,
                        checked_at TEXT NOT NULL,
                        note TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_field_checks_cell_id
                        ON field_checks(cell_id, id DESC);
                    """
                )

    def create_support_request(self, values: dict[str, Any]) -> dict[str, Any]:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO support_requests (
                        facility_id, requester_name, contact, requested_at,
                        request_type, note, status
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
                    """,
                    (
                        values["facility_id"],
                        values["requester_name"],
                        values["contact"],
                        values["requested_at"],
                        values["request_type"],
                        values["note"],
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM support_requests WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
                return dict(row)

    def list_support_requests(
        self, status: str | None = None
    ) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM support_requests ORDER BY id DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM support_requests WHERE status = ? ORDER BY id DESC",
                    (status,),
                ).fetchall()
            return [dict(row) for row in rows]

    def get_support_request(self, request_id: int) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM support_requests WHERE id = ?", (request_id,)
            ).fetchone()
            return dict(row) if row is not None else None

    def create_field_check(self, values: dict[str, Any]) -> dict[str, Any]:
        checklist = json.dumps(values["checklist"], ensure_ascii=False)
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO field_checks (cell_id, checklist, checked_at, note)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        values["cell_id"],
                        checklist,
                        values["checked_at"],
                        values["note"],
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM field_checks WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
                return self._decode_field_check(dict(row))

    def list_field_checks(self, cell_id: str) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM field_checks WHERE cell_id = ? ORDER BY id DESC",
                (cell_id,),
            ).fetchall()
            return [self._decode_field_check(dict(row)) for row in rows]

    @staticmethod
    def _decode_field_check(row: dict[str, Any]) -> dict[str, Any]:
        row["checklist"] = json.loads(row["checklist"])
        return row
