
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "booking.db")

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY,
        date TEXT NOT NULL,
        time_start TEXT NOT NULL,
        time_end TEXT NOT NULL,
        zone TEXT,
        capacity INTEGER NOT NULL,
        booked_count INTEGER NOT NULL DEFAULT 0
    )""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY,
        user_id TEXT NOT NULL,
        slot_id INTEGER NOT NULL,
        address TEXT,
        note TEXT,
        status TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(slot_id) REFERENCES slots(id)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bookings_slot ON bookings(slot_id)")
    return conn

conn = init_db()

@contextmanager
def tx():
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

def query(sql, params=()):
    cur = conn.execute(sql, params)
    return cur.fetchall()

def execute(sql, params=()):
    cur = conn.execute(sql, params)
    return cur.lastrowid
