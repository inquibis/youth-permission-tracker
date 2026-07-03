"""
Unit tests for Youth Permission Tracker Alexa Skill
Tests API client, auth manager, and response formatting
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Test API Client
class TestAPIClient(unittest.TestCase):
    """Test the API client"""
    
    def setUp(self):
        """Set up test fixtures"""
        from api.client import APIClient
        self.api_client = APIClient("http://test.api.local", timeout=5)
    
    @patch('requests.get')
    def test_get_all_activities_success(self, mock_get):
        """Test successful activity retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "activity_id": "1",
                "name": "Soccer",
                "date": "2026-12-15",
                "requires_permission": False
            }
        ]
        mock_get.return_value = mock_response
        
        success, activities, error = self.api_client.get_all_activities()
        
        self.assertTrue(success)
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["name"], "Soccer")
        self.assertIsNone(error)
    
    @patch('requests.get')
    def test_get_all_activities_failure(self, mock_get):
        """Test failed activity retrieval"""
        mock_get.side_effect = Exception("Connection error")
        
        success, activities, error = self.api_client.get_all_activities()
        
        self.assertFalse(success)
        self.assertIsNone(activities)
        self.assertIsNotNone(error)
    
    @patch('requests.post')
    def test_grant_permission_success(self, mock_post):
        """Test successful permission grant"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "granted"}
        mock_post.return_value = mock_response
        
        success, result, error = self.api_client.grant_permission("youth1", "activity1", "123456")
        
        self.assertTrue(success)
        self.assertEqual(result["status"], "granted")
        self.assertIsNone(error)


# Test Authentication Manager
class TestAuthManager(unittest.TestCase):
    """Test the authentication manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        from api.auth import HybridAuthManager
        self.auth_manager = HybridAuthManager("http://test.api.local", timeout=5)
    
    def test_validate_permission_code_valid(self):
        """Test valid permission code validation"""
        is_valid, info, error = self.auth_manager.validate_permission_code("123456")
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        self.assertEqual(info["permission_code"], "123456")
    
    def test_validate_permission_code_invalid_format(self):
        """Test invalid permission code format"""
        test_cases = [
            "12345",      # Too short
            "1234567",    # Too long
            "abcdef",     # Not digits
            "",           # Empty
            None,         # None
        ]
        
        for code in test_cases:
            is_valid, info, error = self.auth_manager.validate_permission_code(code)
            self.assertFalse(is_valid, f"Code {code} should be invalid")
            self.assertIsNotNone(error)
    
    def test_is_token_valid(self):
        """Test token validity check"""
        # Valid token
        future_time = (datetime.now() + timedelta(minutes=10)).isoformat()
        is_valid = self.auth_manager.is_token_valid("test_token", future_time)
        self.assertTrue(is_valid)
        
        # Expired token
        past_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        is_valid = self.auth_manager.is_token_valid("test_token", past_time)
        self.assertFalse(is_valid)
        
        # Missing token
        is_valid = self.auth_manager.is_token_valid(None, future_time)
        self.assertFalse(is_valid)


# Test Response Formatter
class TestResponseFormatter(unittest.TestCase):
    """Test response formatting for voice output"""
    
    def setUp(self):
        """Set up test fixtures"""
        from utils.response_formatter import ResponseFormatter
        self.formatter = ResponseFormatter()
    
    def test_format_date(self):
        """Test date formatting"""
        date_str = "2026-12-15"
        formatted = self.formatter.format_date(date_str)
        
        self.assertIn("December", formatted)
        self.assertIn("15", formatted)
        self.assertIn("th", formatted)
    
    def test_format_time(self):
        """Test time formatting"""
        # 24-hour format
        time_str = "14:30"
        formatted = self.formatter.format_time(time_str)
        
        self.assertIn("2", formatted)
        self.assertIn("PM", formatted)
    
    def test_format_cost(self):
        """Test cost formatting"""
        cost_values = [
            (5.0, "five dollars"),
            (5.5, "five dollars and fifty cents"),
            (0.0, "zero dollars"),
        ]
        
        for cost, expected_phrase in cost_values:
            formatted = self.formatter.format_cost(cost)
            self.assertIn(expected_phrase, formatted.lower(), f"Cost {cost} should include '{expected_phrase}'")
    
    def test_format_activity_list(self):
        """Test activity list formatting"""
        activities = [
            {"name": "Soccer", "date": "2026-12-15"},
            {"name": "Pizza Night", "date": "2026-12-18"},
            {"name": "Hike", "date": "2026-12-22"},
        ]
        
        formatted = self.formatter.format_activity_list(activities, max_items=3)
        
        self.assertIn("3 upcoming activities", formatted)
        self.assertIn("Soccer", formatted)
        self.assertIn("Pizza Night", formatted)
        self.assertIn("Hike", formatted)
    
    def test_format_activity_list_empty(self):
        """Test empty activity list formatting"""
        formatted = self.formatter.format_activity_list([])
        
        self.assertIn("don't have any upcoming activities", formatted)
    
    def test_format_activity_details(self):
        """Test activity details formatting"""
        activity = {
            "activity_name": "Soccer Practice",
            "date_start": "2026-12-15",
            "start_time": "14:00",
            "end_time": "16:00",
            "location": "Central Park",
            "description": "Come join us for soccer!",
            "is_overnight": False,
            "is_coed": False,
            "total_cost": 5.0,
        }
        
        formatted = self.formatter.format_activity_details(activity)
        
        self.assertIn("Soccer Practice", formatted)
        self.assertIn("December", formatted)
        self.assertIn("Central Park", formatted)
        self.assertIn("soccer", formatted.lower())
        self.assertIn("five dollars", formatted.lower())


# Test Session State
class TestSessionState(unittest.TestCase):
    """Test session state management"""
    
    def setUp(self):
        """Set up test fixtures"""
        from models.session import SessionState, ChildInfo
        self.SessionState = SessionState
        self.ChildInfo = ChildInfo
    
    def test_session_state_initialization(self):
        """Test session state initialization"""
        state = self.SessionState()
        
        self.assertIsNone(state.user_type)
        self.assertEqual(state.setup_step, "awaiting_user_type")
        self.assertFalse(state.is_setup_complete())
    
    def test_session_state_serialization(self):
        """Test session state to/from dict conversion"""
        child = self.ChildInfo(
            child_id="youth1",
            child_name="Emma",
            org_group="young women",
            permission_code="123456"
        )
        
        state = self.SessionState(
            user_type="parent",
            permission_code="123456",
            selected_child=child,
            setup_step="complete",
            pin="1234"
        )
        
        # Convert to dict and back
        state_dict = state.to_dict()
        restored_state = self.SessionState.from_dict(state_dict)
        
        self.assertEqual(restored_state.user_type, "parent")
        self.assertEqual(restored_state.permission_code, "123456")
        self.assertEqual(restored_state.selected_child.child_name, "Emma")
        self.assertTrue(restored_state.is_setup_complete())
    
    def test_is_parent(self):
        """Test parent detection"""
        parent_state = self.SessionState(user_type="parent")
        youth_state = self.SessionState(user_type="youth")
        
        self.assertTrue(parent_state.is_parent())
        self.assertFalse(youth_state.is_parent())
    
    def test_is_token_expired(self):
        """Test token expiry check"""
        state = self.SessionState()
        
        # No token
        self.assertTrue(state.is_token_expired())
        
        # Future expiry
        future_time = (datetime.now() + timedelta(minutes=10)).isoformat()
        state.token_expiry = future_time
        self.assertFalse(state.is_token_expired())
        
        # Past expiry
        past_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        state.token_expiry = past_time
        self.assertTrue(state.is_token_expired())


# Test Constants
class TestConstants(unittest.TestCase):
    """Test configuration constants"""
    
    def test_constants_loaded(self):
        """Test that constants are properly loaded"""
        from utils.constants import (
            API_URL, RESPONSE_MESSAGES, INTENTS, SLOTS,
            API_ENDPOINTS, SESSION_KEYS
        )
        
        # Verify key constants exist
        self.assertIsNotNone(API_URL)
        self.assertIsNotNone(RESPONSE_MESSAGES)
        self.assertIsNotNone(INTENTS)
        self.assertIsNotNone(SLOTS)
        self.assertIsNotNone(API_ENDPOINTS)
        self.assertIsNotNone(SESSION_KEYS)
        
        # Verify some key messages exist
        self.assertIn("welcome", RESPONSE_MESSAGES)
        self.assertIn("no_activities", RESPONSE_MESSAGES)
        self.assertIn("help_text", RESPONSE_MESSAGES)
        self.assertIn("permission_granted", RESPONSE_MESSAGES)


# Integration Tests
class TestIntegration(unittest.TestCase):
    """Integration tests for end-to-end flows"""
    
    @patch('requests.get')
    @patch('requests.post')
    def test_permission_grant_flow(self, mock_post, mock_get):
        """Test complete permission grant flow"""
        from api.client import APIClient
        from api.auth import HybridAuthManager
        
        api_client = APIClient("http://test.api.local")
        auth_manager = HybridAuthManager("http://test.api.local")
        
        # Step 1: Validate permission code
        is_valid, user_info, error = auth_manager.validate_permission_code("123456")
        self.assertTrue(is_valid)
        
        # Step 2: Get activities needing permission
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "activity_id": "act1",
                "activity_name": "Campout",
                "requires_permission": True,
            }
        ]
        mock_get.return_value = mock_response
        
        success, activities, error = api_client.get_activities_needing_permission("123456")
        self.assertTrue(success)
        self.assertEqual(len(activities), 1)
        
        # Step 3: Grant permission
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        success, result, error = api_client.grant_permission("youth1", "act1", "123456")
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
