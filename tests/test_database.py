import os
import tempfile
from unittest.mock import patch

def test_init_db_creates_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        with patch("src.database.DB_PATH", db_path):
            from src.database import init_db, get_db
            init_db()
            conn = get_db()
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t["name"] for t in tables]
            assert "oauth_tokens" in table_names
            assert "cache_status" in table_names
            conn.close()
