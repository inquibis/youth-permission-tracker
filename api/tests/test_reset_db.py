from unittest.mock import patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@patch("reset_db.Base.metadata.drop_all")
@patch("reset_db.Base.metadata.create_all")
def test_reset_db_dev_mode(mock_create, mock_drop, monkeypatch):
    monkeypatch.setenv("ENV", "dev")
    import reset_db
    mock_drop.assert_called()
    mock_create.assert_called()