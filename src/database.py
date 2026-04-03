import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("thermal_sentinel.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            container_id TEXT NOT NULL,
            timestamp    TEXT NOT NULL,
            status       TEXT NOT NULL,
            peak_temp    REAL DEFAULT 0.0,
            image_path   TEXT,
            leak_x1      INTEGER,
            leak_y1      INTEGER,
            leak_x2      INTEGER,
            leak_y2      INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS container_stats (
            container_id  TEXT PRIMARY KEY,
            total_scans   INTEGER DEFAULT 0,
            leak_count    INTEGER DEFAULT 0,
            last_seen     TEXT,
            avg_peak_temp REAL DEFAULT 0.0,
            flagged       INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_tickets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            container_id TEXT NOT NULL,
            scan_id      INTEGER,
            created_at   TEXT NOT NULL,
            severity     TEXT NOT NULL,
            status       TEXT DEFAULT 'OPEN',
            notes        TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized!")

def insert_scan(container_id, status, peak_temp, image_path=None, leak_coords=None):
    conn = get_connection()
    cursor = conn.cursor()
    lx1, ly1, lx2, ly2 = leak_coords if leak_coords else (None, None, None, None)

    cursor.execute("""
        INSERT INTO scans (container_id, timestamp, status, peak_temp,
                           image_path, leak_x1, leak_y1, leak_x2, leak_y2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (container_id, datetime.now().isoformat(), status,
          peak_temp, image_path, lx1, ly1, lx2, ly2))

    scan_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO container_stats (container_id, total_scans, leak_count,
                                      last_seen, avg_peak_temp)
        VALUES (?, 1, ?, ?, ?)
        ON CONFLICT(container_id) DO UPDATE SET
            total_scans   = total_scans + 1,
            leak_count    = leak_count + ?,
            last_seen     = excluded.last_seen,
            avg_peak_temp = (avg_peak_temp * total_scans + ?) / (total_scans + 1)
    """, (
        container_id,
        1 if "LEAK" in status or "WARNING" in status else 0,
        datetime.now().isoformat(),
        peak_temp,
        1 if "LEAK" in status or "WARNING" in status else 0,
        peak_temp
    ))

    conn.commit()
    conn.close()
    return scan_id

def insert_ticket(container_id, scan_id, severity, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO maintenance_tickets
            (container_id, scan_id, created_at, severity, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (container_id, scan_id, datetime.now().isoformat(), severity, notes))
    cursor.execute(
        "UPDATE container_stats SET flagged = 1 WHERE container_id = ?",
        (container_id,)
    )
    conn.commit()
    conn.close()

def get_all_scans(limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM scans ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_flagged_containers():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM container_stats WHERE flagged = 1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_open_tickets():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM maintenance_tickets WHERE status = 'OPEN' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]