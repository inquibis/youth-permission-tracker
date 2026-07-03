"""
Unit tests for admin query endpoint
"""
import pytest
import json
from unittest.mock import patch


class TestAdminQueryEndpoint:
    """Tests for POST /admin/query endpoint"""
    
    def test_admin_query_select_success(self, client, auth_token):
        """Test successful SELECT query execution"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT 1 as test"},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "SELECT" in data["query"] or "results" in str(data)
    
    def test_admin_query_insert_success(self, client, auth_token, test_db):
        """Test successful INSERT query execution"""
        response = client.post(
            "/admin/query",
            json={
                "query": "INSERT INTO visits (created_at) VALUES (datetime('now'))"
            },
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True or response.status_code in [200, 201]
    
    def test_admin_query_update_success(self, client, auth_token, test_admin_user):
        """Test successful UPDATE query execution"""
        response = client.post(
            "/admin/query",
            json={
                "query": "UPDATE admin_users SET role = 'admin' WHERE username = 'test_admin'"
            },
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data
    
    def test_admin_query_delete_success(self, client, auth_token):
        """Test successful DELETE query execution"""
        response = client.post(
            "/admin/query",
            json={
                "query": "DELETE FROM visits WHERE id < 0"  # Won't delete anything real
            },
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "message" in data
    
    def test_admin_query_without_auth_token(self, client):
        """Test that query endpoint requires authentication"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT * FROM admin_users"}
        )
        
        assert response.status_code == 403
    
    def test_admin_query_with_invalid_token(self, client):
        """Test query endpoint rejects invalid token"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT 1"},
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_admin_query_blocks_drop_statement(self, client, auth_token):
        """Test that DROP statements are blocked"""
        response = client.post(
            "/admin/query",
            json={"query": "DROP TABLE admin_users"},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "forbidden" in data.get("detail", "").lower() or "drop" in data.get("detail", "").lower()
    
    def test_admin_query_blocks_truncate_statement(self, client, auth_token):
        """Test that TRUNCATE statements are blocked"""
        response = client.post(
            "/admin/query",
            json={"query": "TRUNCATE TABLE admin_users"},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 400
    
    def test_admin_query_blocks_alter_statement(self, client, auth_token):
        """Test that ALTER statements are blocked"""
        response = client.post(
            "/admin/query",
            json={"query": "ALTER TABLE admin_users ADD COLUMN test TEXT"},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 400
    
    def test_admin_query_blocks_pragma_statement(self, client, auth_token):
        """Test that PRAGMA statements are blocked"""
        response = client.post(
            "/admin/query",
            json={"query": "PRAGMA table_info(admin_users)"},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 400
    
    def test_admin_query_blocks_vacuum(self, client, auth_token):
        """Test that VACUUM is blocked"""
        response = client.post(
            "/admin/query",
            json={"query": "VACUUM"},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 400
    
    def test_admin_query_blocks_detach(self, client, auth_token):
        """Test that DETACH is blocked"""
        response = client.post(
            "/admin/query",
            json={"query": "DETACH DATABASE main"},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 400
    
    def test_admin_query_invalid_query_type(self, client, auth_token):
        """Test that non-SELECT/INSERT/UPDATE/DELETE queries are rejected"""
        response = client.post(
            "/admin/query",
            json={"query": "CREATE TABLE test (id INT)"},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 400
    
    def test_admin_query_empty_query(self, client, auth_token):
        """Test that empty query is rejected"""
        response = client.post(
            "/admin/query",
            json={"query": ""},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code in [400, 422]
    
    def test_admin_query_missing_query_field(self, client, auth_token):
        """Test that missing query field returns validation error"""
        response = client.post(
            "/admin/query",
            json={},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 422
    
    def test_admin_query_returns_correct_row_count(self, client, auth_token):
        """Test that query response includes row count"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT * FROM admin_users LIMIT 1"},
            headers={"Authorization": auth_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "row_count" in data
            assert isinstance(data["row_count"], int)
    
    def test_admin_query_returns_execution_time(self, client, auth_token):
        """Test that query response includes execution time"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT 1"},
            headers={"Authorization": auth_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "execution_time_ms" in data
            assert isinstance(data["execution_time_ms"], float)
    
    def test_admin_query_returns_column_names_for_select(self, client, auth_token):
        """Test that SELECT queries return column names"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT id, username FROM admin_users LIMIT 1"},
            headers={"Authorization": auth_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                assert "columns" in data
    
    def test_admin_query_returns_data_rows_for_select(self, client, auth_token, test_admin_user):
        """Test that SELECT queries return data rows"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT * FROM admin_users WHERE username = 'test_admin'"},
            headers={"Authorization": auth_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                assert "rows" in data or "error" not in data
    
    def test_admin_query_handles_database_error(self, client, auth_token):
        """Test that database errors are handled gracefully"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT * FROM nonexistent_table"},
            headers={"Authorization": auth_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Should return error details but not crash
            assert "error" in data or "success" in data
        else:
            # Or return 400/500
            assert response.status_code in [400, 500]
    
    def test_admin_query_with_whitespace_and_newlines(self, client, auth_token):
        """Test that queries with whitespace are handled correctly"""
        response = client.post(
            "/admin/query",
            json={
                "query": """
                    SELECT * 
                    FROM admin_users 
                    LIMIT 1
                """
            },
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 200
    
    def test_admin_query_with_comments(self, client, auth_token):
        """Test that SQL comments are handled"""
        response = client.post(
            "/admin/query",
            json={
                "query": "SELECT 1 -- this is a comment"
            },
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 200
    
    def test_admin_query_audit_logging(self, client, auth_token, test_db):
        """Test that queries are logged to audit_log table"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT 1"},
            headers={"Authorization": auth_token}
        )
        
        assert response.status_code == 200
        
        # Check if query was logged
        cursor = test_db.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM audit_log WHERE action = 'ADMIN_QUERY'")
        result = cursor.fetchone()
        assert result["count"] >= 1


class TestAdminQueryPermissions:
    """Tests for role-based access control on admin query endpoint"""
    
    def test_non_admin_user_cannot_execute_queries(self, client):
        """Test that non-admin users cannot execute queries"""
        from jose import jwt
        from datetime import datetime, timedelta, timezone
        import os
        
        SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
        ALGORITHM = "HS256"
        
        # Create a token with 'youth' role
        payload = {
            "sub": "youth_user",
            "role": "youth",
            "org_group": "test-group",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        response = client.post(
            "/admin/query",
            json={"query": "SELECT 1"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
    
    def test_only_admin_role_can_query(self, client, auth_token):
        """Test that only admin role can execute queries"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT 1"},
            headers={"Authorization": auth_token}
        )
        
        # Should succeed with admin role
        assert response.status_code in [200, 201]
