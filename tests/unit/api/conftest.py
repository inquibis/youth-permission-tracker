"""
Pytest configuration and fixtures for API unit tests
"""
import pytest
import sqlite3
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add api_base to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../api_base'))

from main import app
from db import DatabaseEngine
from schema import YouthCreationRequest, LoginRequest


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Create minimal schema for testing
    cursor = conn.cursor()
    
    # admin_users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            org_group TEXT NOT NULL,
            user_id TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # youth_medical table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS youth_medical (
            youth_id TEXT PRIMARY KEY,
            permission_code TEXT NOT NULL,
            youth TEXT NOT NULL,
            parent_guardian TEXT NOT NULL,
            medical TEXT NOT NULL,
            emergency_contact TEXT NOT NULL,
            signature TEXT NOT NULL,
            signed_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # activities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            activity_id TEXT PRIMARY KEY,
            activity_name TEXT NOT NULL,
            date_start TEXT NOT NULL,
            date_end TEXT NOT NULL,
            drivers TEXT,
            description TEXT,
            groups TEXT NOT NULL,
            requires_permission INTEGER DEFAULT 1,
            bishop_approval INTEGER,
            stake_approval INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # interest_survey table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interest_survey (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            youth_id TEXT NOT NULL,
            interests TEXT NOT NULL,
            org_group TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # concern_survey table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concern_survey (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concerns TEXT NOT NULL,
            org_group TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # audit_log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_username TEXT,
            actor_role TEXT,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            success INTEGER NOT NULL,
            details TEXT,
            client_ip TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # visits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_db(test_db):
    """Mock database for dependency injection"""
    def get_db_mock():
        return test_db
    
    yield get_db_mock


@pytest.fixture
def client(mock_db):
    """Create a test client with mocked database"""
    # Mock the DatabaseEngine dependency
    with patch('main.DB.get_db', mock_db):
        client = TestClient(app)
        yield client


@pytest.fixture
def auth_token():
    """Generate a valid JWT token for testing"""
    from jose import jwt
    from datetime import datetime, timedelta, timezone
    
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
    ALGORITHM = "HS256"
    
    payload = {
        "sub": "test_admin",
        "role": "admin",
        "org_group": "test-group",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return f"Bearer {token}"


@pytest.fixture
def test_admin_user(test_db):
    """Create a test admin user in the database"""
    cursor = test_db.cursor()
    cursor.execute("""
        INSERT INTO admin_users (username, password, role, org_group, user_id)
        VALUES (?, ?, ?, ?, ?)
    """, ("test_admin", "password123", "admin", "test-group", "admin_001"))
    test_db.commit()
    return {"username": "test_admin", "password": "password123", "role": "admin"}


@pytest.fixture
def test_youth_user(test_db):
    """Create a test youth user in the database"""
    cursor = test_db.cursor()
    cursor.execute("""
        INSERT INTO admin_users (username, password, role, org_group, user_id)
        VALUES (?, ?, ?, ?, ?)
    """, ("john_doe", "password123", "youth", "test-group", "youth_001"))
    test_db.commit()
    return {"username": "john_doe", "password": "password123", "role": "youth"}


@pytest.fixture
def test_activity(test_db):
    """Create a test activity in the database"""
    import json
    from datetime import datetime, timedelta
    
    cursor = test_db.cursor()
    start_date = (datetime.now() + timedelta(days=7)).isoformat()
    end_date = (datetime.now() + timedelta(days=8)).isoformat()
    
    cursor.execute("""
        INSERT INTO activities (activity_id, activity_name, date_start, date_end, drivers, description, groups)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("act_001", "Test Activity", start_date, end_date, "Driver Name", "Test Description", json.dumps(["test-group"])))
    test_db.commit()
    return {
        "activity_id": "act_001",
        "activity_name": "Test Activity",
        "date_start": start_date,
        "date_end": end_date
    }
