import pytest
from fastapi.testclient import TestClient
from api.main import app  # Adjust import path as needed

client = TestClient(app)

def test_get_activity():
    response = client.get("/activity?id=123")
    assert response.status_code == 200
    data = response.json()
    assert data["activity_id"] == "123"
    assert "activity_name" in data

def test_post_activity_permission_minimal():
    payload = {
        "activity_id": "123",
        "allergies": "None",
        "signature": None
    }
    response = client.post("/activity-permission", json=payload)
    assert response.status_code == 200
    resp_json = response.json()
    assert resp_json["status"] == "success"
    assert "entry_id" in resp_json
