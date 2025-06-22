import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Sample user payload
user_payload = {
    "first_name": "John",
    "last_name": "Doe",
    "guardian_name": "Jane Doe",
    "guardian_email": "jane@example.com",
    "guardian_cell": "555-5555",
    "user_email": "john@example.com",
    "user_cell": "555-1234",
    "is_active": True,
    "groups": ["young man", "teacher"]
}

def test_create_user():
    res = client.post("/users", json=user_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["first_name"] == user_payload["first_name"]
    assert "id" in data

def test_get_users():
    res = client.get("/users")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(user["first_name"] == "John" for user in data)
