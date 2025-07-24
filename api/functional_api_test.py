from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

DUMMY_HEADERS = {
    "Authorization": "Bearer faketoken"
}

TEST_USER = {
    "first_name": "Test",
    "last_name": "User",
    "guardian_name": "Parent",
    "guardian_email": "parent@example.com",
    "guardian_cell": "+1234567890",
    "user_email": "testuser@example.com",
    "user_cell": "+1234567899",
    "is_active": True,
    "groups": ["Deacon"],
    "role": "admin",
    "guardian_password": "secret"
}

TEST_ACTIVITY = {
    "activity_name": "Test Hike",
    "date_start": "2025-08-01T09:00:00",
    "date_end": "2025-08-01T17:00:00",
    "drivers": ["Leader A"],
    "description": "Testing outdoor hike",
    "groups": ["Deacon"]
}

TEST_NEED = {
    "group_name": "Deacon",
    "need": "More chaperones",
    "priority": 2,
    "created_by": 1
}

TEST_USER_INT = {
    "first_name": "Interest",
    "last_name": "Tester",
    "guardian_name": "Parent",
    "guardian_email": "parent2@example.com",
    "guardian_cell": "+1234567891",
    "user_email": "interest@example.com",
    "user_cell": "+1234567892",
    "is_active": True,
    "groups": ["Teacher"],
    "role": "admin",
    "guardian_password": "secret"
}


def run_functional_test_sequence():
    print("🔄 Starting functional test...")

    #######  USERS
    print("🧪 Creating user...")
    res = client.post("/users", headers=DUMMY_HEADERS, json=TEST_USER)
    assert res.status_code == 200, f"Failed to create user: {res.text}"
    user_id = res.json()["user_id"]
    print("🛠️ Modifying user...")
    TEST_USER["first_name"] = "Updated"
    res = client.put(f"/users/{user_id}", headers=DUMMY_HEADERS, json=TEST_USER)
    assert res.status_code == 200, f"Failed to update user: {res.text}"
    assert res.json()["first_name"] == "Updated"
    print("📄 Listing users...")
    res = client.get("/users", headers=DUMMY_HEADERS)
    assert res.status_code == 200 and any(u["user_id"] == user_id for u in res.json()), "User not listed"


    ###### ACTIVITY RESOURCES
    print("Testing activity ideas")
    res = client.get("/activity-ideas", headers=DUMMY_HEADERS)
    assert res.status_code == 200, f"Failed to get list: {res.text}"
    lst = res.json()
    assert "Child care" in res.text

    print("🔄 Starting user-interest functional tests...")
    # 1. Create test user
    print("👤 Creating user for interest tracking...")
    res = client.post("/users", headers=DUMMY_HEADERS, json=TEST_USER_INT)
    assert res.status_code == 200, f"Failed to create user: {res.text}"
    user_id = res.json()["user_id"]
    full_name = f"{TEST_USER_INT['first_name']} {TEST_USER_INT['last_name']}"
    # 2. Submit user interests
    print("📝 Submitting interest data...")
    interest_payload = {
        "name": full_name,
        "activities": ["Rocketry", "Photography"]
    }
    res = client.post("/user-interest", headers=DUMMY_HEADERS, json=interest_payload)
    assert res.status_code == 200
    assert res.json()["activities_saved"] == 2
    # 3. List all user interests
    print("📋 Listing all user interests...")
    res = client.get("/user-interest", headers=DUMMY_HEADERS)
    assert res.status_code == 200
    result = res.json()
    matched = [r for r in result if r["name"] == full_name]
    assert matched and set(matched[0]["activities"]) >= {"Rocketry", "Photography"}
    # 4. Clean up user
    print("🧹 Deleting test user...")
    res = client.delete(f"/users/{user_id}", headers=DUMMY_HEADERS)
    assert res.status_code == 200
    print("✅ User-interest functional test passed!")

    print("🔄 Testing identified-needs endpoints...")
    # 1. Create a need
    print("📌 Creating a need...")
    res = client.post("/identified-needs", headers=DUMMY_HEADERS, json=TEST_NEED)
    assert res.status_code == 200, f"Failed to create need: {res.text}"
    need_id = res.json()["id"]
    assert res.json()["need"] == TEST_NEED["need"]
    # 2. Get needs for group
    print("📋 Fetching needs for group...")
    res = client.get("/identified-needs/Deacon", headers=DUMMY_HEADERS)
    assert res.status_code == 200
    assert any(n["id"] == need_id for n in res.json()), "Need not found in group listing"
    # 3. Update the need
    print("🛠️ Updating the need...")
    updated = {
        "group_name": "Deacon",
        "need": "Updated chaperone request",
        "priority": 1
    }
    res = client.put(f"/identified-needs/{need_id}", headers=DUMMY_HEADERS, json=updated)
    assert res.status_code == 200
    assert res.json()["need"] == "Updated chaperone request"
    # 4. Delete the need
    print("🗑️ Deleting the need...")
    res = client.delete(f"/identified-needs/{need_id}", headers=DUMMY_HEADERS)
    assert res.status_code == 200
    # 5. Confirm it's gone
    print("🔍 Confirming deletion...")
    res = client.get("/identified-needs/Deacon", headers=DUMMY_HEADERS)
    assert all(n["id"] != need_id for n in res.json()), "Need was not deleted"
    print("✅ Identified-needs functional test passed!")


    ###### ACTIVITIES
    print("🏕️ Creating activity...")
    res = client.post("/activity", headers=DUMMY_HEADERS, json=TEST_ACTIVITY)
    assert res.status_code == 200, f"Failed to create activity: {res.text}"
    activity_id = res.json()["id"]
    print("🔍 Fetching activity...")
    res = client.get(f"/activity?id={activity_id}", headers=DUMMY_HEADERS)
    assert res.status_code == 200, "Failed to retrieve activity"
    print("🧹 Deleting activity...")
    res = client.delete(f"/activity/{activity_id}", headers=DUMMY_HEADERS)
    assert res.status_code == 200, "Failed to delete activity"


    ######  CLEANUP
    print("🗑️ Deleting user...")
    res = client.delete(f"/users/{user_id}", headers=DUMMY_HEADERS)
    assert res.status_code == 200, "Failed to delete user"
    print("✅ Functional test passed successfully!")


if __name__ == "__main__":
    run_functional_test_sequence()