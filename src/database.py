import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "data/morning.db")

def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            provider TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at REAL
        );
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id TEXT PRIMARY KEY,
            public_key BLOB,
            sign_count INTEGER DEFAULT 0,
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS cache_status (
            source TEXT PRIMARY KEY,
            last_success REAL,
            last_error TEXT,
            data TEXT
        );
    """)
    conn.commit()
    conn.close()
