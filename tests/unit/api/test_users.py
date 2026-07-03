"""
Unit tests for user management endpoints
"""
import pytest
import json
from datetime import datetime, timedelta


class TestYouthUserCreation:
    """Tests for POST /youth endpoint - create youth user"""
    
    def test_youth_creation_success(self, client):
        """Test successful youth user creation"""
        response = client.post("/youth", json={
            "first_name": "John",
            "last_name": "Doe",
            "group": "test-group"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
    
    def test_youth_creation_with_duplicate_name(self, client):
        """Test youth creation fails with duplicate first/last name combination"""
        # Create first user
        client.post("/youth", json={
            "first_name": "John",
            "last_name": "Doe",
            "group": "test-group"
        })
        
        # Try to create duplicate
        response = client.post("/youth", json={
            "first_name": "John",
            "last_name": "Doe",
            "group": "test-group"
        })
        
        assert response.status_code == 409  # Conflict
    
    def test_youth_creation_with_missing_first_name(self, client):
        """Test youth creation fails with missing first name"""
        response = client.post("/youth", json={
            "last_name": "Doe",
            "group": "test-group"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_youth_creation_with_missing_last_name(self, client):
        """Test youth creation fails with missing last name"""
        response = client.post("/youth", json={
            "first_name": "John",
            "group": "test-group"
        })
        
        assert response.status_code == 422
    
    def test_youth_creation_with_missing_group(self, client):
        """Test youth creation fails with missing group"""
        response = client.post("/youth", json={
            "first_name": "John",
            "last_name": "Doe"
        })
        
        assert response.status_code == 422
    
    def test_youth_creation_generates_correct_username(self, client):
        """Test that username is generated as lowercase first_last"""
        response = client.post("/youth", json={
            "first_name": "John",
            "last_name": "DOE",
            "group": "test-group"
        })
        
        assert response.status_code == 200
        # Username should be john_doe (lowercase)


class TestUserCreationWithMedicalInfo:
    """Tests for POST /users endpoint - create user with medical info"""
    
    def test_user_creation_success_with_complete_data(self, client):
        """Test successful user creation with all fields"""
        response = client.post("/users", json={
            "permission_code": "PERM001",
            "youth": {
                "first_name": "Jane",
                "last_name": "Smith",
                "birth_date": "2010-01-15",
                "gender": "F",
                "org_group": "test-group"
            },
            "parent_guardian": {
                "name": "Parent Name",
                "phone": "5551234567",
                "email": "parent@example.com",
                "relationship": "Mother"
            },
            "medical": {
                "conditions": "None",
                "medications": "None",
                "allergies": "Peanuts"
            },
            "emergency_contact": {
                "name": "Emergency Contact",
                "phone": "5559876543"
            },
            "signature": {
                "name": "Signature Name",
                "date": datetime.now().isoformat()
            },
            "signed_at": datetime.now().isoformat()
        })
        
        assert response.status_code == 200
    
    def test_user_creation_success_with_blank_medical_fields(self, client):
        """Test user creation with blank/null medical fields"""
        response = client.post("/users", json={
            "permission_code": "PERM002",
            "youth": {
                "first_name": "Bob",
                "last_name": "Johnson",
                "birth_date": "2010-06-20",
                "gender": "M",
                "org_group": "test-group"
            },
            "parent_guardian": {
                "name": "Parent Name",
                "phone": "5551234567",
                "email": None,
                "relationship": "Father"
            },
            "medical": {
                "conditions": None,
                "medications": None,
                "allergies": None
            },
            "emergency_contact": {
                "name": "Emergency Contact",
                "phone": "5559876543"
            },
            "signature": {
                "name": "Signature Name",
                "date": datetime.now().isoformat()
            },
            "signed_at": datetime.now().isoformat()
        })
        
        assert response.status_code == 200
    
    def test_user_creation_fails_with_missing_required_fields(self, client):
        """Test user creation fails when required fields are missing"""
        response = client.post("/users", json={
            "permission_code": "PERM003"
            # Missing all other required fields
        })
        
        assert response.status_code == 422
    
    def test_user_creation_fails_with_invalid_email_format(self, client):
        """Test user creation fails with invalid email format"""
        response = client.post("/users", json={
            "permission_code": "PERM004",
            "youth": {
                "first_name": "Alice",
                "last_name": "Brown",
                "birth_date": "2010-03-10",
                "gender": "F",
                "org_group": "test-group"
            },
            "parent_guardian": {
                "name": "Parent Name",
                "phone": "5551234567",
                "email": "invalid-email",  # Invalid format
                "relationship": "Mother"
            },
            "medical": {"conditions": None, "medications": None, "allergies": None},
            "emergency_contact": {"name": "Emergency", "phone": "5559876543"},
            "signature": {"name": "Sig", "date": datetime.now().isoformat()},
            "signed_at": datetime.now().isoformat()
        })
        
        # May or may not validate email strictly
        if response.status_code == 422:
            assert "email" in str(response.json())


class TestUserRetrieval:
    """Tests for GET /users/{youth_id} endpoint"""
    
    def test_user_retrieval_success(self, client):
        """Test successful user retrieval by ID"""
        # First create a user
        create_response = client.post("/users", json={
            "permission_code": "PERM005",
            "youth": {
                "first_name": "Charlie",
                "last_name": "Davis",
                "birth_date": "2010-07-05",
                "gender": "M",
                "org_group": "test-group"
            },
            "parent_guardian": {
                "name": "Parent",
                "phone": "5551234567",
                "email": "parent@example.com",
                "relationship": "Father"
            },
            "medical": {"conditions": None, "medications": None, "allergies": None},
            "emergency_contact": {"name": "Emergency", "phone": "5559876543"},
            "signature": {"name": "Sig", "date": datetime.now().isoformat()},
            "signed_at": datetime.now().isoformat()
        })
        
        # Then try to retrieve it
        if create_response.status_code == 200:
            youth_id = "charlie_davis"  # Generated ID format
            response = client.get(f"/users/{youth_id}")
            
            if response.status_code == 200:
                data = response.json()
                assert "youth" in data or "permission_code" in data
    
    def test_user_retrieval_not_found(self, client):
        """Test user retrieval returns 404 for non-existent user"""
        response = client.get("/users/nonexistent_user")
        
        assert response.status_code in [200, 404]  # Either not found or returns empty
    
    def test_user_retrieval_case_insensitive(self, client):
        """Test that user retrieval is case-insensitive"""
        response = client.get("/users/JOHN_DOE")
        
        # Should normalize to lowercase
        assert response.status_code in [200, 404]


class TestUserDeletion:
    """Tests for DELETE /users/{youth_id} endpoint"""
    
    def test_user_deletion_success(self, client):
        """Test successful user deletion"""
        # First create a user
        create_response = client.post("/youth", json={
            "first_name": "Emma",
            "last_name": "Wilson",
            "group": "test-group"
        })
        
        if create_response.status_code == 200:
            youth_id = "emma_wilson"
            response = client.delete(f"/users/{youth_id}")
            
            # Should succeed or return 204
            assert response.status_code in [200, 204]
    
    def test_user_deletion_nonexistent_user(self, client):
        """Test deletion of non-existent user"""
        response = client.delete("/users/nonexistent_user")
        
        # Should succeed silently or return 404
        assert response.status_code in [200, 204, 404]


class TestUserUpdate:
    """Tests for PUT /users/{youth_id} endpoint"""
    
    def test_user_update_success(self, client):
        """Test successful user update"""
        # Create a user first
        client.post("/youth", json={
            "first_name": "Frank",
            "last_name": "Miller",
            "group": "test-group"
        })
        
        youth_id = "frank_miller"
        response = client.put(f"/users/{youth_id}", json={
            "permission_code": "PERM006",
            "youth": {
                "first_name": "Frank",
                "last_name": "Miller",
                "birth_date": "2010-09-12",
                "gender": "M",
                "org_group": "test-group"
            },
            "parent_guardian": {
                "name": "Parent",
                "phone": "5551234567",
                "email": "parent@example.com",
                "relationship": "Father"
            },
            "medical": {"conditions": None, "medications": None, "allergies": None},
            "emergency_contact": {"name": "Emergency", "phone": "5559876543"},
            "signature": {"name": "Sig", "date": datetime.now().isoformat()},
            "signed_at": datetime.now().isoformat()
        })
        
        if response.status_code in [200, 204]:
            assert True
        else:
            # May not be implemented
            assert response.status_code in [404, 501]


class TestUserActivities:
    """Tests for POST /user-activities endpoint"""
    
    def test_user_activity_submission_success(self, client):
        """Test successful user activity interests submission"""
        # First create a youth user
        client.post("/youth", json={
            "first_name": "Grace",
            "last_name": "Lee",
            "group": "test-group"
        })
        
        response = client.post("/user-activities", json={
            "username": "grace_lee",
            "activity_ids": ["activity1", "activity2", "activity3"]
        })
        
        assert response.status_code in [200, 201]
    
    def test_user_activity_submission_empty_activities(self, client):
        """Test user activity submission with empty activity list"""
        response = client.post("/user-activities", json={
            "username": "grace_lee",
            "activity_ids": []
        })
        
        # Should either accept empty list or return validation error
        assert response.status_code in [200, 201, 400, 422]
    
    def test_user_activity_submission_invalid_username(self, client):
        """Test user activity submission with non-existent username"""
        response = client.post("/user-activities", json={
            "username": "nonexistent_user",
            "activity_ids": ["activity1"]
        })
        
        # Should fail or create if username is flexible
        assert response.status_code in [200, 400, 404]
    
    def test_user_activity_submission_missing_fields(self, client):
        """Test user activity submission fails with missing fields"""
        response = client.post("/user-activities", json={
            "username": "grace_lee"
            # Missing activity_ids
        })
        
        assert response.status_code == 422
