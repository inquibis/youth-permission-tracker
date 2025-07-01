from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_activity_information():
    payload = {
        "activity_name": "Campfire Night",
        "description": "Outdoor evening activity",
        "groups": ["priest", "young_man"],
        "drivers": ["Alice", "Bob"],
        "budget": [
            {"item": "Snacks", "amount": 45.00},
            {"item": "Wood", "amount": 30.00}
        ],
        "date_start": "2025-08-01",
        "date_end": "2025-08-02",
        "purpose": "Team building and outdoor skills"
    }
    response = client.post("/api/activity-information", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "activity_id" in data

def test_get_activity_information_by_name():
    # Assuming the previous test inserted "Campfire Night"
    response = client.get("/api/activity-information", params={"activity_name": "Campfire Night"})
    assert response.status_code == 200
    data = response.json()
    assert data["activity_name"] == "Campfire Night"
    assert "budget" in data and isinstance(data["budget"], list)
