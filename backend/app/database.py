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
            connection.row_factory = sqlite3.Row
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

                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL
                            CHECK (role IN ('citizen', 'field_worker', 'admin')),
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(support_requests)"
                    )
                }
                if "contact_consent" not in columns:
                    connection.execute(
                        """ALTER TABLE support_requests
                           ADD COLUMN contact_consent INTEGER NOT NULL DEFAULT 0"""
                    )

    def create_user(
        self, email: str, password_hash: str, role: str = "citizen"
    ) -> dict[str, Any]:
        if role not in {"citizen", "field_worker", "admin"}:
            raise ValueError("Unsupported user role")
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                cursor = connection.execute(
                    "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
                    (email.lower(), password_hash, role),
                )
                row = connection.execute(
                    "SELECT id, email, role, created_at FROM users WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
                return dict(row)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
                (email.lower(),),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT id, email, role, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def create_support_request(self, values: dict[str, Any]) -> dict[str, Any]:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO support_requests (
                        facility_id, requester_name, contact, requested_at,
                        request_type, note, status, contact_consent
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (
                        values["facility_id"],
                        values["requester_name"],
                        values["contact"],
                        values["requested_at"],
                        values["request_type"],
                        values["note"],
                        int(values["contact_consent"]),
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM support_requests WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
                return self._decode_support_request(dict(row))

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
            return [self._decode_support_request(dict(row)) for row in rows]

    def get_support_request(self, request_id: int) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM support_requests WHERE id = ?", (request_id,)
            ).fetchone()
            return self._decode_support_request(dict(row)) if row is not None else None

    def update_support_request_status(
        self, request_id: int, status: str
    ) -> dict[str, Any] | None:
        if status not in {"pending", "approved", "rejected", "completed"}:
            raise ValueError("Unsupported support request status")
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                cursor = connection.execute(
                    "UPDATE support_requests SET status = ? WHERE id = ?",
                    (status, request_id),
                )
                if cursor.rowcount == 0:
                    return None
                row = connection.execute(
                    "SELECT * FROM support_requests WHERE id = ?", (request_id,)
                ).fetchone()
                return self._decode_support_request(dict(row))

    @staticmethod
    def _decode_support_request(row: dict[str, Any]) -> dict[str, Any]:
        row["contact_consent"] = bool(row["contact_consent"])
        return row

    def demand_signals(self, minimum_count: int = 3) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT facility_id, request_type, status, COUNT(*) AS count
                FROM support_requests
                GROUP BY facility_id, request_type, status
                HAVING COUNT(*) >= ?
                ORDER BY facility_id, request_type, status
                """,
                (minimum_count,),
            ).fetchall()
            return [dict(row) for row in rows]

    def field_feedback_summary(self) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT cell_id, checklist FROM field_checks ORDER BY cell_id"
            ).fetchall()

        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            summary = grouped.setdefault(
                row["cell_id"],
                {"cell_id": row["cell_id"], "checked_count": 0, "items": {}},
            )
            summary["checked_count"] += 1
            checklist = json.loads(row["checklist"])
            for item, response in checklist.items():
                if response is None:
                    continue
                summary["items"][item] = summary["items"].get(item, 0) + 1

        return [
            {
                "cell_id": summary["cell_id"],
                "checked_count": summary["checked_count"],
                "checklist_responses": [
                    {"item_index": index, "response_count": count}
                    for index, (_, count) in enumerate(
                        sorted(summary["items"].items()), start=1
                    )
                ],
            }
            for _, summary in sorted(grouped.items())
        ]

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
