import sqlite3
from datetime import datetime

DB = "campus.db"

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    conn.execute("""
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
    conn.close()

def add_item(item_type, name, category, description, location, event_time, image):
    conn = connect()
    conn.execute("""
        INSERT INTO items
        (type, name, category, description, location, event_time, image, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item_type, name, category, description, location,
        event_time, image, datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    conn.commit()
    conn.close()

def get_items(item_type=None):
    conn = connect()
    if item_type:
        rows = conn.execute(
            "SELECT * FROM items WHERE type=? ORDER BY id DESC", (item_type,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM items ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def get_item(item_id):
    conn = connect()
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return row

def update_status(item_id, status):
    conn = connect()
    conn.execute("UPDATE items SET status=? WHERE id=?", (status, item_id))
    conn.commit()
    conn.close()
