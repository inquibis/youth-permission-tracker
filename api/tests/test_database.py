import os
import importlib
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_database_url_selection(monkeypatch):
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("SQLITE_PATH", "sqlite:///test_local.db")
    import database
    assert "sqlite" in database.DATABASE_URL
    importlib.reload(database)