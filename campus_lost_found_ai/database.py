"""MySQL persistence for CampusFind AI.

The module keeps database access small and parameterized. It deliberately uses
the existing ``items`` table and adds ``match_reviews`` only for the office
workflow, where a potential pair and its AI evidence need an audit trail.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error

load_dotenv()

ITEM_TYPES = {"lost", "found"}
ITEM_STATUSES = {"searching", "under_review", "verified", "returned", "rejected"}
MATCH_DECISIONS = {"potential", "under_review", "verified", "rejected"}
_DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class DatabaseError(RuntimeError):
    """A safe, user-facing database error without connection credentials."""


def _settings() -> dict[str, Any]:
    """Read settings when a connection is opened so tests and deployments work."""

    database = os.getenv("MYSQL_DATABASE", "campus_lost_found").strip()
    if not _DATABASE_NAME.fullmatch(database):
        raise DatabaseError("MYSQL_DATABASE may contain only letters, numbers, and underscores.")

    try:
        port = int(os.getenv("MYSQL_PORT", "3306"))
    except ValueError as exc:
        raise DatabaseError("MYSQL_PORT must be a valid number.") from exc

    try:
        timeout = int(os.getenv("MYSQL_CONNECT_TIMEOUT", "8"))
    except ValueError as exc:
        raise DatabaseError("MYSQL_CONNECT_TIMEOUT must be a valid number.") from exc

    return {
        "host": os.getenv("MYSQL_HOST", "localhost").strip() or "localhost",
        "port": port,
        "user": os.getenv("MYSQL_USER", "root").strip() or "root",
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": database,
        "connection_timeout": timeout,
    }


def _raise_database_error(error: Error) -> DatabaseError:
    # Do not include driver messages: they can contain host names or credentials.
    return DatabaseError("The CampusFind database is unavailable. Check the MySQL service and settings.")


def connect_server():
    """Connect to MySQL without selecting the application database."""

    settings = _settings()
    settings.pop("database")
    try:
        return mysql.connector.connect(**settings)
    except Error as error:
        raise _raise_database_error(error) from error


def connect():
    """Connect to the configured CampusFind database."""

    try:
        return mysql.connector.connect(**_settings())
    except Error as error:
        raise _raise_database_error(error) from error


def _close(cursor=None, connection=None) -> None:
    if cursor is not None:
        try:
            cursor.close()
        except Error:
            pass
    if connection is not None:
        try:
            connection.close()
        except Error:
            pass


def init_db() -> None:
    """Create the database and schema, including safe migrations for older demos."""

    server_connection = server_cursor = connection = cursor = None
    settings = _settings()
    database = settings["database"]
    try:
        server_connection = connect_server()
        server_cursor = server_connection.cursor()
        server_cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{database}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        server_connection.commit()

        connection = connect()
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                type VARCHAR(20) NOT NULL,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                description TEXT,
                location VARCHAR(255),
                event_time VARCHAR(100),
                image VARCHAR(500),
                status VARCHAR(50) NOT NULL DEFAULT 'searching',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_items_type_status (type, status),
                INDEX idx_items_created_at (created_at)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
        )

        # Older copies of the hackathon prototype may have been created before
        # status and created_at gained safe defaults.
        cursor.execute("SHOW COLUMNS FROM items")
        existing_columns = {row[0] for row in cursor.fetchall()}
        if "status" not in existing_columns:
            cursor.execute("ALTER TABLE items ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'searching'")
        if "created_at" not in existing_columns:
            cursor.execute("ALTER TABLE items ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS match_reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lost_item_id INT NOT NULL,
                found_item_id INT NOT NULL,
                input_fingerprint CHAR(64) NOT NULL,
                analysis_json LONGTEXT,
                evidence_confidence TINYINT UNSIGNED NULL,
                analysis_state VARCHAR(30) NOT NULL DEFAULT 'completed',
                decision VARCHAR(30) NOT NULL DEFAULT 'potential',
                reviewed_by VARCHAR(100) NULL,
                reviewed_at DATETIME NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_match_pair (lost_item_id, found_item_id),
                INDEX idx_review_decision (decision)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
        )
        connection.commit()
    except Error as error:
        if connection is not None:
            connection.rollback()
        raise _raise_database_error(error) from error
    finally:
        _close(cursor, connection)
        _close(server_cursor, server_connection)


def add_item(
    item_type: str,
    name: str,
    category: str,
    description: str,
    location: str,
    event_time: str,
    image: str,
) -> int:
    if item_type not in ITEM_TYPES:
        raise ValueError("Invalid item type.")

    connection = cursor = None
    try:
        connection = connect()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO items (type, name, category, description, location, event_time, image, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'searching', NOW())
            """,
            (item_type, name, category, description, location, event_time, image),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except Error as error:
        if connection is not None:
            connection.rollback()
        raise _raise_database_error(error) from error
    finally:
        _close(cursor, connection)


def get_items(
    item_type: str | None = None,
    *,
    query: str = "",
    status: str | None = None,
    category: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch items with optional, fully parameterized public/admin filters."""

    if item_type is not None and item_type not in ITEM_TYPES:
        raise ValueError("Invalid item type.")
    if status is not None and status not in ITEM_STATUSES:
        raise ValueError("Invalid item status.")

    clauses: list[str] = []
    params: list[Any] = []
    if item_type:
        clauses.append("type = %s")
        params.append(item_type)
    if status:
        clauses.append("status = %s")
        params.append(status)
    if category:
        clauses.append("category = %s")
        params.append(category)
    if query:
        clauses.append("(name LIKE %s OR category LIKE %s OR description LIKE %s OR location LIKE %s)")
        term = f"%{query.strip()}%"
        params.extend([term, term, term, term])

    sql = "SELECT * FROM items"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC, id DESC"
    if limit is not None:
        sql += " LIMIT %s"
        params.append(max(1, min(int(limit), 100)))

    connection = cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    except Error as error:
        raise _raise_database_error(error) from error
    finally:
        _close(cursor, connection)


def get_item(item_id: int) -> dict[str, Any] | None:
    connection = cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
        return cursor.fetchone()
    except Error as error:
        raise _raise_database_error(error) from error
    finally:
        _close(cursor, connection)


def update_status(item_id: int, status: str) -> bool:
    if status not in ITEM_STATUSES:
        raise ValueError("Invalid item status.")
    connection = cursor = None
    try:
        connection = connect()
        cursor = connection.cursor()
        cursor.execute("UPDATE items SET status = %s WHERE id = %s", (status, item_id))
        connection.commit()
        return cursor.rowcount > 0
    except Error as error:
        if connection is not None:
            connection.rollback()
        raise _raise_database_error(error) from error
    finally:
        _close(cursor, connection)


def _decode_review(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    raw_analysis = row.pop("analysis_json", None)
    try:
        row["assessment"] = json.loads(raw_analysis) if raw_analysis else None
    except (TypeError, json.JSONDecodeError):
        row["assessment"] = None
    return row


def get_match_review(lost_item_id: int, found_item_id: int) -> dict[str, Any] | None:
    connection = cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM match_reviews WHERE lost_item_id = %s AND found_item_id = %s",
            (lost_item_id, found_item_id),
        )
        return _decode_review(cursor.fetchone())
    except Error as error:
        raise _raise_database_error(error) from error
    finally:
        _close(cursor, connection)


def get_match_review_by_id(review_id: int) -> dict[str, Any] | None:
    connection = cursor = None
    try:
        connection = connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM match_reviews WHERE id = %s", (review_id,))
        return _decode_review(cursor.fetchone())
    except Error as error:
        raise _raise_database_error(error) from error
    finally:
        _close(cursor, connection)


def save_match_review(
    lost_item_id: int,
    found_item_id: int,
    fingerprint: str,
    assessment: dict[str, Any],
    evidence_confidence: int,
) -> int:
    """Cache completed AI evidence without overwriting a staff decision."""

    connection = cursor = None
    try:
        connection = connect()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO match_reviews
                (lost_item_id, found_item_id, input_fingerprint, analysis_json, evidence_confidence, analysis_state)
            VALUES (%s, %s, %s, %s, %s, 'completed')
            ON DUPLICATE KEY UPDATE
                input_fingerprint = VALUES(input_fingerprint),
                analysis_json = VALUES(analysis_json),
                evidence_confidence = VALUES(evidence_confidence),
                analysis_state = 'completed'
            """,
            (
                lost_item_id,
                found_item_id,
                fingerprint,
                json.dumps(assessment, ensure_ascii=False),
                max(0, min(100, int(evidence_confidence))),
            ),
        )
        connection.commit()
        cursor.execute(
            "SELECT id FROM match_reviews WHERE lost_item_id = %s AND found_item_id = %s",
            (lost_item_id, found_item_id),
        )
        return int(cursor.fetchone()[0])
    except Error as error:
        if connection is not None:
            connection.rollback()
        raise _raise_database_error(error) from error
    finally:
        _close(cursor, connection)


def set_match_decision(review_id: int, decision: str, reviewed_by: str) -> bool:
    if decision not in MATCH_DECISIONS:
        raise ValueError("Invalid match decision.")
    connection = cursor = None
    try:
        connection = connect()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE match_reviews
            SET decision = %s, reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s
            """,
            (decision, reviewed_by[:100], review_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    except Error as error:
        if connection is not None:
            connection.rollback()
        raise _raise_database_error(error) from error
    finally:
        _close(cursor, connection)
