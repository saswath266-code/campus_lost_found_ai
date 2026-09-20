import os
import sqlite3
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SQLITE_DB = os.getenv("SQLITE_DB", "campus.db")


def using_postgres():
    return bool(DATABASE_URL)


def connect():
    if using_postgres():
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                description TEXT,
                location TEXT,
                event_time TEXT,
                image TEXT,
                status TEXT DEFAULT 'searching',
                created_at TEXT
            )
        """) if using_postgres() else conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                description TEXT,
                location TEXT,
                event_time TEXT,
                image TEXT,
                status TEXT DEFAULT 'searching',
                created_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def add_item(item_type, name, category, description, location, event_time, image):
    conn = connect()
    try:
        conn.execute("""
            INSERT INTO items
            (type, name, category, description, location, event_time, image, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """ if using_postgres() else """
            INSERT INTO items
            (type, name, category, description, location, event_time, image, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_type, name, category, description, location, event_time, image,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()
    finally:
        conn.close()


def get_items(item_type=None):
    conn = connect()
    try:
        if item_type:
            rows = conn.execute(
                "SELECT * FROM items WHERE type=%s ORDER BY id DESC" if using_postgres() else
                "SELECT * FROM items WHERE type=? ORDER BY id DESC", (item_type,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM items ORDER BY id DESC").fetchall()
        return rows
    finally:
        conn.close()


def get_item(item_id):
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM items WHERE id=%s" if using_postgres() else
            "SELECT * FROM items WHERE id=?", (item_id,)
        ).fetchone()
    finally:
        conn.close()


def update_status(item_id, status):
    conn = connect()
    try:
        conn.execute(
            "UPDATE items SET status=%s WHERE id=%s" if using_postgres() else
            "UPDATE items SET status=? WHERE id=?", (status, item_id)
        )
        conn.commit()
    finally:
        conn.close()
