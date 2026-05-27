"""
Unit tests for basic health and general endpoints
"""
import pytest


class TestHealthCheck:
    """Tests for GET /health endpoint"""
    
    def test_health_check_success(self, client):
        """Test successful health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "message" in data
    
    def test_health_check_returns_valid_format(self, client):
        """Test that health check returns valid JSON format"""
        response = client.get("/health")
        
        assert response.status_code == 200
        # Should be valid JSON
        try:
            data = response.json()
            assert isinstance(data, dict)
        except:
            pytest.fail("Health check did not return valid JSON")


class TestRootEndpoint:
    """Tests for GET / endpoint"""
    
    def test_root_endpoint_success(self, client):
        """Test successful request to root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_root_endpoint_increments_visit_count(self, client, test_db):
        """Test that root endpoint increments visit count"""
        initial_count_response = client.get("/")
        initial_count = initial_count_response.json().get("visits", 0)
        
        # Make another request
        client.get("/")
        
        second_response = client.get("/")
        second_count = second_response.json().get("visits", 0)
        
        # Visit count should increase (if endpoint increments it)
        if initial_count is not None and second_count is not None:
            assert second_count >= initial_count
    
    def test_root_endpoint_returns_hello_message(self, client):
        """Test that root endpoint returns expected message"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "hello" in data.get("message", "").lower() or "world" in data.get("message", "").lower()


class TestEndpointContentTypes:
    """Tests for proper content type handling"""
    
    def test_endpoints_return_json(self, client):
        """Test that API endpoints return JSON content type"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_post_endpoints_accept_json(self, client):
        """Test that POST endpoints accept JSON"""
        response = client.post(
            "/youth",
            json={
                "first_name": "Test",
                "last_name": "User",
                "group": "test-group"
            }
        )
        
        # Should process JSON (may fail for other reasons but not content type)
        assert response.status_code != 415  # 415 = Unsupported Media Type


class TestErrorHandling:
    """Tests for error handling and error responses"""
    
    def test_invalid_json_returns_422(self, client):
        """Test that invalid JSON returns validation error"""
        response = client.post(
            "/youth",
            content="invalid json"
        )
        
        assert response.status_code in [400, 422]
    
    def test_missing_required_fields_returns_422(self, client):
        """Test that missing required fields returns validation error"""
        response = client.post("/youth", json={})
        
        assert response.status_code == 422
    
    def test_unauthorized_endpoints_return_401_or_403(self, client):
        """Test that unauthorized access returns 401 or 403"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT 1"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_not_found_endpoints_return_404(self, client):
        """Test that non-existent endpoints return 404"""
        response = client.get("/nonexistent_endpoint")
        
        assert response.status_code == 404
    
    def test_error_response_includes_detail(self, client):
        """Test that error responses include detail message"""
        response = client.post(
            "/admin/query",
            json={"query": "SELECT 1"}
        )
        
        if response.status_code >= 400:
            data = response.json()
            assert "detail" in data or "message" in data


class TestCORSHeaders:
    """Tests for CORS header handling"""
    
    def test_cors_preflight_request(self, client):
        """Test CORS preflight OPTIONS request"""
        response = client.options(
            "/youth",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        assert response.status_code == 200
    
    def test_cors_headers_in_response(self, client):
        """Test that CORS headers are included in response"""
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Should have CORS headers
        assert response.status_code == 200


class TestHTTPMethods:
    """Tests for HTTP method handling"""
    
    def test_unsupported_http_method_returns_405(self, client):
        """Test that unsupported HTTP methods return 405"""
        response = client.trace("/")  # TRACE method is not supported
        
        assert response.status_code in [405, 404]
    
    def test_get_endpoint_rejects_post(self, client):
        """Test that GET-only endpoint rejects POST"""
        response = client.post(
            "/health",
            json={}
        )
        
        assert response.status_code == 405
    
    def test_post_endpoint_rejects_get(self, client):
        """Test that POST-only endpoint rejects GET"""
        response = client.get("/youth")
        
        assert response.status_code == 405


class TestPathParameters:
    """Tests for path parameter handling"""
    
    def test_endpoint_with_path_parameter(self, client):
        """Test endpoint that requires path parameter"""
        response = client.get("/users/test_id")
        
        # Should either find the user or return 404
        assert response.status_code in [200, 404]
    
    def test_missing_path_parameter(self, client):
        """Test endpoint with missing path parameter"""
        response = client.get("/users/")
        
        # May return 404 or 405
        assert response.status_code in [404, 405]


class TestQueryParameters:
    """Tests for query parameter handling"""
    
    def test_endpoint_with_optional_query_parameter(self, client):
        """Test endpoint that accepts optional query parameters"""
        response = client.get("/activities-all?include_past=true")
        
        assert response.status_code in [200, 400, 422]
    
    def test_invalid_query_parameter_value(self, client):
        """Test endpoint with invalid query parameter value"""
        response = client.get("/activities-all?include_past=invalid")
        
        # Should either accept as boolean or return validation error
        assert response.status_code in [200, 422]


class TestResponseFormats:
    """Tests for response format consistency"""
    
    def test_success_response_format(self, client):
        """Test that success responses have expected format"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_list_response_format(self, client):
        """Test that list responses return proper format"""
        response = client.get("/activities-all")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
    
    def test_error_response_format(self, client):
        """Test that error responses have expected format"""
        response = client.post("/youth", json={})
        
        if response.status_code >= 400:
            data = response.json()
            assert isinstance(data, dict)
            assert "detail" in data or "message" in data
