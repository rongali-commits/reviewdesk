from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat()


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class Storage:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(
        self,
        business: dict[str, Any],
        sequence: list[dict[str, Any]],
        *,
        seed_demo_data: bool = False,
    ) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sequence (
                    step INTEGER PRIMARY KEY,
                    delay_hours INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT NOT NULL DEFAULT '',
                    service TEXT NOT NULL DEFAULT '',
                    service_date TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'manual',
                    status TEXT NOT NULL DEFAULT 'pending',
                    reminders_enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    opened_at TEXT,
                    responded_at TEXT
                );

                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                    sequence_step INTEGER NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    sent_at TEXT,
                    provider TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    last_error TEXT,
                    UNIQUE(contact_id, sequence_step)
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER NOT NULL UNIQUE REFERENCES contacts(id) ON DELETE CASCADE,
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                    comment TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    testimonial_consent INTEGER NOT NULL DEFAULT 0,
                    featured INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    public_clicked_at TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_requests_due
                    ON requests(status, scheduled_at);
                CREATE INDEX IF NOT EXISTS idx_contacts_created
                    ON contacts(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_feedback_created
                    ON feedback(created_at DESC);
                """
            )
            existing = connection.execute("SELECT id FROM settings WHERE id = 1").fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO settings (id, payload, updated_at) VALUES (1, ?, ?)",
                    (json.dumps(business), iso()),
                )
            sequence_count = connection.execute("SELECT COUNT(*) FROM sequence").fetchone()[0]
            if sequence_count == 0:
                connection.executemany(
                    """
                    INSERT INTO sequence (step, delay_hours, name, subject, body, enabled)
                    VALUES (:step, :delay_hours, :name, :subject, :body, :enabled)
                    """,
                    [{**item, "enabled": int(item.get("enabled", True))} for item in sequence],
                )
        if seed_demo_data:
            self.seed_demo()

    def seed_demo(self) -> None:
        with self.connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
            if count:
                return

        samples = [
            {
                "name": "Olivia Martin",
                "email": "olivia@example.com",
                "service": "Brake inspection",
                "service_date": "2026-08-27",
                "status": "responded",
                "rating": 5,
                "comment": (
                    "Clear communication, fair pricing, and my car was ready exactly when "
                    "promised."
                ),
                "featured": True,
                "public_clicked": True,
            },
            {
                "name": "Daniel Brooks",
                "email": "daniel@example.com",
                "service": "Scheduled maintenance",
                "service_date": "2026-08-25",
                "status": "responded",
                "rating": 5,
                "comment": (
                    "The team explained what was urgent and what could wait. No pressure at all."
                ),
                "featured": True,
                "public_clicked": True,
            },
            {
                "name": "Sofia Reyes",
                "email": "sofia@example.com",
                "service": "Air conditioning repair",
                "service_date": "2026-08-24",
                "status": "responded",
                "rating": 4,
                "comment": "Friendly service and a smooth booking experience from start to finish.",
                "featured": True,
                "public_clicked": False,
            },
            {
                "name": "Marcus Lee",
                "email": "marcus@example.com",
                "service": "Tire replacement",
                "service_date": "2026-08-23",
                "status": "responded",
                "rating": 3,
                "comment": (
                    "Good work overall. A text update during the wait would have made it even "
                    "better."
                ),
                "featured": False,
                "public_clicked": False,
            },
            {
                "name": "Ava Patel",
                "email": "ava@example.com",
                "service": "Battery replacement",
                "service_date": "2026-08-28",
                "status": "opened",
            },
            {
                "name": "Ethan Wilson",
                "email": "ethan@example.com",
                "service": "Oil change",
                "service_date": "2026-08-28",
                "status": "requested",
            },
        ]
        created_ids: list[int] = []
        for sample in samples:
            contact = self.create_contact(
                {
                    "name": sample["name"],
                    "email": sample["email"],
                    "phone": "",
                    "service": sample["service"],
                    "service_date": sample["service_date"],
                    "source": "demo",
                    "reminders_enabled": True,
                }
            )
            created_ids.append(contact["id"])
            if sample["status"] in {"requested", "opened", "responded"}:
                with self.connect() as connection:
                    connection.execute(
                        """
                        UPDATE requests
                        SET status = 'sent', sent_at = ?, provider = 'demo'
                        WHERE contact_id = ? AND sequence_step = 1
                        """,
                        (iso(), contact["id"]),
                    )
                    connection.execute(
                        "UPDATE contacts SET status = 'requested' WHERE id = ?",
                        (contact["id"],),
                    )
            if sample["status"] in {"opened", "responded"}:
                self.mark_opened(contact["token"])
            if sample["status"] == "responded":
                self.submit_feedback(
                    contact["token"],
                    {
                        "rating": sample["rating"],
                        "comment": sample["comment"],
                        "display_name": sample["name"],
                        "testimonial_consent": True,
                    },
                )
                with self.connect() as connection:
                    connection.execute(
                        "UPDATE feedback SET featured = ? WHERE contact_id = ?",
                        (int(sample["featured"]), contact["id"]),
                    )
                if sample.get("public_clicked"):
                    self.record_public_click(contact["token"])

    def ping(self) -> bool:
        with self.connect() as connection:
            return connection.execute("SELECT 1").fetchone()[0] == 1

    def get_settings(self) -> dict[str, Any]:
        with self.connect() as connection:
            payload = connection.execute("SELECT payload FROM settings WHERE id = 1").fetchone()
        return json.loads(payload["payload"])

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute(
                "UPDATE settings SET payload = ?, updated_at = ? WHERE id = 1",
                (json.dumps(payload), iso()),
            )
        return self.get_settings()

    def get_sequence(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM sequence ORDER BY step").fetchall()
        return [{**dict(row), "enabled": bool(row["enabled"])} for row in rows]

    def update_sequence(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with self.connect() as connection:
            for item in items:
                connection.execute(
                    """
                    UPDATE sequence
                    SET delay_hours = :delay_hours, name = :name, subject = :subject,
                        body = :body, enabled = :enabled
                    WHERE step = :step
                    """,
                    {**item, "enabled": int(item["enabled"])},
                )
        return self.get_sequence()

    def create_contact(self, payload: dict[str, Any]) -> dict[str, Any]:
        token = secrets.token_urlsafe(18)
        created_at = iso()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO contacts (
                    token, name, email, phone, service, service_date, source,
                    status, reminders_enabled, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    token,
                    payload["name"],
                    payload["email"],
                    payload.get("phone", ""),
                    payload.get("service", ""),
                    payload.get("service_date", ""),
                    payload.get("source", "manual"),
                    int(payload.get("reminders_enabled", True)),
                    created_at,
                ),
            )
            contact_id = cursor.lastrowid
            sequence = connection.execute(
                "SELECT step, delay_hours FROM sequence WHERE enabled = 1 ORDER BY step"
            ).fetchall()
            for item in sequence:
                scheduled_at = iso(utc_now() + timedelta(hours=item["delay_hours"]))
                connection.execute(
                    """
                    INSERT INTO requests (contact_id, sequence_step, scheduled_at)
                    VALUES (?, ?, ?)
                    """,
                    (contact_id, item["step"], scheduled_at),
                )
            connection.execute(
                """
                INSERT INTO events (contact_id, event_type, metadata, created_at)
                VALUES (?, 'contact.created', ?, ?)
                """,
                (contact_id, json.dumps({"source": payload.get("source", "manual")}), created_at),
            )
            row = connection.execute(
                "SELECT * FROM contacts WHERE id = ?", (contact_id,)
            ).fetchone()
        return self._contact(row)

    def create_contacts(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.create_contact(item) for item in items]

    def _contact(self, row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["reminders_enabled"] = bool(value["reminders_enabled"])
        return value

    def get_contact_by_token(self, token: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM contacts WHERE token = ?", (token,)).fetchone()
        return self._contact(row) if row else None

    def list_contacts(self, limit: int = 200) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.*,
                       f.rating,
                       f.comment,
                       (SELECT COUNT(*) FROM requests r
                        WHERE r.contact_id = c.id AND r.status = 'sent') AS messages_sent
                FROM contacts c
                LEFT JOIN feedback f ON f.contact_id = c.id
                ORDER BY c.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [{**dict(row), "reminders_enabled": bool(row["reminders_enabled"])} for row in rows]

    def mark_opened(self, token: str) -> dict[str, Any] | None:
        opened_at = iso()
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM contacts WHERE token = ?", (token,)).fetchone()
            if row is None:
                return None
            if row["status"] not in {"responded"}:
                connection.execute(
                    """
                    UPDATE contacts
                    SET status = 'opened', opened_at = COALESCE(opened_at, ?)
                    WHERE id = ?
                    """,
                    (opened_at, row["id"]),
                )
            connection.execute(
                """
                INSERT INTO events (contact_id, event_type, metadata, created_at)
                VALUES (?, 'request.opened', '{}', ?)
                """,
                (row["id"], opened_at),
            )
        return self.get_contact_by_token(token)

    def submit_feedback(self, token: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        created_at = iso()
        with self.connect() as connection:
            contact = connection.execute(
                "SELECT * FROM contacts WHERE token = ?", (token,)
            ).fetchone()
            if contact is None:
                return None
            existing = connection.execute(
                "SELECT id FROM feedback WHERE contact_id = ?", (contact["id"],)
            ).fetchone()
            if existing:
                return {"duplicate": True, "contact_id": contact["id"]}
            cursor = connection.execute(
                """
                INSERT INTO feedback (
                    contact_id, rating, comment, display_name,
                    testimonial_consent, featured, created_at
                ) VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    contact["id"],
                    payload["rating"],
                    payload["comment"],
                    payload["display_name"],
                    int(payload.get("testimonial_consent", False)),
                    created_at,
                ),
            )
            connection.execute(
                """
                UPDATE contacts
                SET status = 'responded', responded_at = ?, reminders_enabled = 0
                WHERE id = ?
                """,
                (created_at, contact["id"]),
            )
            connection.execute(
                """
                UPDATE requests SET status = 'suppressed'
                WHERE contact_id = ? AND status = 'pending'
                """,
                (contact["id"],),
            )
            connection.execute(
                """
                INSERT INTO events (contact_id, event_type, metadata, created_at)
                VALUES (?, 'feedback.submitted', ?, ?)
                """,
                (contact["id"], json.dumps({"rating": payload["rating"]}), created_at),
            )
            row = connection.execute(
                "SELECT * FROM feedback WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return self._feedback(row)

    def record_public_click(self, token: str) -> bool:
        clicked_at = iso()
        with self.connect() as connection:
            contact = connection.execute(
                "SELECT id FROM contacts WHERE token = ?", (token,)
            ).fetchone()
            if contact is None:
                return False
            connection.execute(
                """
                UPDATE feedback SET public_clicked_at = COALESCE(public_clicked_at, ?)
                WHERE contact_id = ?
                """,
                (clicked_at, contact["id"]),
            )
            connection.execute(
                """
                INSERT INTO events (contact_id, event_type, metadata, created_at)
                VALUES (?, 'public_review.clicked', '{}', ?)
                """,
                (contact["id"], clicked_at),
            )
        return True

    def _feedback(self, row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["testimonial_consent"] = bool(value["testimonial_consent"])
        value["featured"] = bool(value["featured"])
        return value

    def list_feedback(self, limit: int = 200) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT f.*, c.email, c.service, c.service_date
                FROM feedback f
                JOIN contacts c ON c.id = f.contact_id
                ORDER BY f.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._feedback(row) for row in rows]

    def feature_feedback(self, feedback_id: int, featured: bool) -> dict[str, Any] | None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE feedback
                SET featured = CASE WHEN testimonial_consent = 1 THEN ? ELSE 0 END
                WHERE id = ?
                """,
                (int(featured), feedback_id),
            )
            row = connection.execute(
                "SELECT * FROM feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
        return self._feedback(row) if row else None

    def public_testimonials(self, limit: int = 12) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT f.display_name, f.rating, f.comment, f.created_at, c.service
                FROM feedback f
                JOIN contacts c ON c.id = f.contact_id
                WHERE f.testimonial_consent = 1 AND f.featured = 1
                ORDER BY f.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def due_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT r.id, r.sequence_step, c.id AS contact_id, c.token, c.name, c.email,
                       s.subject, s.body
                FROM requests r
                JOIN contacts c ON c.id = r.contact_id
                JOIN sequence s ON s.step = r.sequence_step
                WHERE r.status = 'pending'
                  AND r.scheduled_at <= ?
                  AND c.reminders_enabled = 1
                  AND c.status != 'responded'
                  AND s.enabled = 1
                ORDER BY r.scheduled_at
                LIMIT ?
                """,
                (iso(), limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_message_sent(self, request_id: int, provider: str) -> None:
        sent_at = iso()
        with self.connect() as connection:
            request = connection.execute(
                "SELECT contact_id FROM requests WHERE id = ?", (request_id,)
            ).fetchone()
            connection.execute(
                """
                UPDATE requests
                SET status = 'sent', sent_at = ?, provider = ?, last_error = NULL
                WHERE id = ?
                """,
                (sent_at, provider, request_id),
            )
            if request:
                connection.execute(
                    """
                    UPDATE contacts SET status = 'requested'
                    WHERE id = ? AND status = 'pending'
                    """,
                    (request["contact_id"],),
                )
                connection.execute(
                    """
                    INSERT INTO events (contact_id, event_type, metadata, created_at)
                    VALUES (?, 'request.sent', ?, ?)
                    """,
                    (request["contact_id"], json.dumps({"provider": provider}), sent_at),
                )

    def mark_message_failed(self, request_id: int, error: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE requests SET status = 'failed', last_error = ? WHERE id = ?",
                (error[:500], request_id),
            )

    def overview(self) -> dict[str, Any]:
        with self.connect() as connection:
            totals = connection.execute(
                """
                SELECT
                    COUNT(*) AS contacts,
                    SUM(CASE WHEN status IN ('requested', 'opened', 'responded') THEN 1 ELSE 0 END)
                        AS requested,
                    SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) AS opened,
                    SUM(CASE WHEN responded_at IS NOT NULL THEN 1 ELSE 0 END) AS responded
                FROM contacts
                """
            ).fetchone()
            ratings = connection.execute(
                """
                SELECT COUNT(*) AS responses,
                       ROUND(AVG(rating), 1) AS average_rating,
                       SUM(CASE WHEN public_clicked_at IS NOT NULL THEN 1 ELSE 0 END)
                           AS public_clicks
                FROM feedback
                """
            ).fetchone()
            sent = connection.execute(
                "SELECT COUNT(*) FROM requests WHERE status = 'sent'"
            ).fetchone()[0]
        requested = totals["requested"] or 0
        responded = totals["responded"] or 0
        return {
            "contacts": totals["contacts"] or 0,
            "requested": requested,
            "opened": totals["opened"] or 0,
            "responded": responded,
            "response_rate": round((responded / requested * 100), 1) if requested else 0,
            "average_rating": ratings["average_rating"] or 0,
            "public_clicks": ratings["public_clicks"] or 0,
            "messages_sent": sent,
        }

    def events(self, limit: int = 30) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT e.*, c.name AS contact_name
                FROM events e
                LEFT JOIN contacts c ON c.id = e.contact_id
                ORDER BY e.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
