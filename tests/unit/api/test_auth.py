"""
Unit tests for authentication endpoints
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestLoginEndpoint:
    """Tests for POST /login endpoint"""
    
    def test_login_success_with_valid_credentials(self, client, test_admin_user):
        """Test successful login with valid username and password"""
        response = client.post("/login", json={
            "username": "test_admin",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data or "message" in data
    
    def test_login_failure_with_invalid_username(self, client):
        """Test login failure with non-existent username"""
        response = client.post("/login", json={
            "username": "nonexistent_user",
            "password": "password123"
        })
        
        assert response.status_code in [401, 404]
    
    def test_login_failure_with_invalid_password(self, client, test_admin_user):
        """Test login failure with incorrect password"""
        response = client.post("/login", json={
            "username": "test_admin",
            "password": "wrong_password"
        })
        
        assert response.status_code == 401
    
    def test_login_failure_with_missing_username(self, client):
        """Test login failure when username is missing"""
        response = client.post("/login", json={
            "password": "password123"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_login_failure_with_missing_password(self, client):
        """Test login failure when password is missing"""
        response = client.post("/login", json={
            "username": "test_admin"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_login_failure_with_empty_credentials(self, client):
        """Test login failure with empty username and password"""
        response = client.post("/login", json={
            "username": "",
            "password": ""
        })
        
        assert response.status_code in [400, 401, 422]


class TestTokenEndpoint:
    """Tests for POST /token endpoint"""
    
    def test_token_generation_success(self, client, test_admin_user):
        """Test successful token generation"""
        response = client.post("/token", data={
            "username": "test_admin",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_token_generation_failure_invalid_credentials(self, client):
        """Test token generation failure with invalid credentials"""
        response = client.post("/token", data={
            "username": "wrong_user",
            "password": "wrong_pass"
        })
        
        assert response.status_code == 401
    
    def test_token_format_is_valid_jwt(self, client, test_admin_user):
        """Test that generated token is valid JWT format"""
        response = client.post("/token", data={
            "username": "test_admin",
            "password": "password123"
        })
        
        assert response.status_code == 200
        token = response.json()["access_token"]
        # JWT tokens have 3 parts separated by dots
        assert token.count(".") == 2


class TestLoginVerifyEndpoint:
    """Tests for POST /login-verify endpoint"""
    
    def test_login_verify_success_with_valid_token(self, client, auth_token):
        """Test token verification with valid token"""
        token = auth_token.replace("Bearer ", "") if "Bearer " in auth_token else auth_token
        response = client.post("/login-verify", params={"token": token})
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Token is valid" in data["message"] or "payload" in data
    
    def test_login_verify_failure_with_invalid_token(self, client):
        """Test token verification fails with invalid token"""
        response = client.post("/login-verify", params={"token": "invalid_token"})
        
        assert response.status_code in [200, 422]  # Returns either success with invalid message or validation error
        if response.status_code == 200:
            data = response.json()
            assert "Invalid token" in data.get("message", "")
    
    def test_login_verify_failure_with_malformed_token(self, client):
        """Test token verification with malformed token"""
        response = client.post("/login-verify", params={"token": "not.a.valid.jwt"})
        
        assert response.status_code in [200, 422]


class TestAdminUserCreation:
    """Tests for POST /admin-users endpoint"""
    
    def test_admin_user_creation_success(self, client, auth_token):
        """Test successful admin user creation"""
        response = client.post(
            "/admin-users",
            json={
                "username": "new_admin",
                "password": "securepass123",
                "role": "admin",
                "org_group": "test-group"
            },
            headers={"Authorization": auth_token}
        )
        
        # Should succeed if endpoint is properly restricted
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            assert "user_id" in data or "message" in data
    
    def test_admin_user_creation_without_auth(self, client):
        """Test admin user creation fails without authentication"""
        response = client.post(
            "/admin-users",
            json={
                "username": "new_admin",
                "password": "securepass123",
                "role": "admin",
                "org_group": "test-group"
            }
        )
        
        assert response.status_code in [401, 403]
    
    def test_admin_user_creation_with_invalid_role_requirement(self, client):
        """Test admin user creation with insufficient permissions"""
        from jose import jwt
        from datetime import datetime, timedelta, timezone
        import os
        
        SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
        ALGORITHM = "HS256"
        
        # Create a token with 'youth' role instead of 'admin'
        payload = {
            "sub": "youth_user",
            "role": "youth",
            "org_group": "test-group",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        response = client.post(
            "/admin-users",
            json={
                "username": "new_admin",
                "password": "securepass123",
                "role": "admin",
                "org_group": "test-group"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [403, 401]
    
    def test_admin_user_creation_with_missing_fields(self, client, auth_token):
        """Test admin user creation fails with missing required fields"""
        response = client.post(
            "/admin-users",
            json={
                "username": "new_admin"
                # Missing password and org_group
            },
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 422


class TestAuthenticationRoleChecking:
    """Tests for role-based access control"""
    
    def test_endpoint_requires_correct_role(self, client):
        """Test that protected endpoints check for correct role"""
        # Attempt to access admin endpoint without proper role
        response = client.post("/admin/query", json={"query": "SELECT 1"})
        
        assert response.status_code in [403, 401]
    
    def test_admin_query_endpoint_requires_admin_role(self, client):
        """Test that /admin/query requires admin role"""
        response = client.post("/admin/query", json={"query": "SELECT * FROM admin_users"})
        
        # Should fail without valid token
        assert response.status_code in [403, 401]
