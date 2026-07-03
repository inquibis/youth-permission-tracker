"""
API Client for Youth Permission Tracker
Handles all communication with the backend API
"""

import requests
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urljoin
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class APIClient:
    """Client for interacting with the Youth Permission Tracker API"""
    
    def __init__(self, api_url: str, api_timeout: int = 10):
        """
        Initialize the API client
        
        Args:
            api_url: Base URL of the API (e.g., http://api-youth.lthome.us)
            api_timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.api_timeout = api_timeout
    
    def _make_request(self, method: str, endpoint: str, 
                     json_data: Optional[Dict] = None,
                     params: Optional[Dict] = None,
                     headers: Optional[Dict] = None,
                     token: Optional[str] = None) -> Tuple[bool, Optional[Any], Optional[str]]:
        """
        Make HTTP request to API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative path)
            json_data: JSON body for POST/PUT requests
            params: Query parameters
            headers: Additional headers
            token: JWT token for authorization
            
        Returns:
            Tuple of (success: bool, data: dict or None, error_message: str or None)
        """
        try:
            url = urljoin(self.api_url + "/", endpoint.lstrip("/"))
            request_headers = headers or {}
            request_headers["Accept"] = "application/json"
            
            if token:
                request_headers["Authorization"] = f"Bearer {token}"
            
            logger.debug(f"{method} {url}")
            
            if method.upper() == "GET":
                response = requests.get(
                    url,
                    params=params,
                    headers=request_headers,
                    timeout=self.api_timeout
                )
            elif method.upper() == "POST":
                response = requests.post(
                    url,
                    json=json_data,
                    params=params,
                    headers=request_headers,
                    timeout=self.api_timeout
                )
            elif method.upper() == "PUT":
                response = requests.put(
                    url,
                    json=json_data,
                    params=params,
                    headers=request_headers,
                    timeout=self.api_timeout
                )
            else:
                return False, None, f"Unsupported HTTP method: {method}"
            
            # Handle different response codes
            if response.status_code == 200:
                return True, response.json(), None
            elif response.status_code == 201:
                return True, response.json(), None
            elif response.status_code == 400:
                error_msg = response.json().get("detail", "Bad request")
                return False, None, f"Bad request: {error_msg}"
            elif response.status_code == 401:
                return False, None, "Unauthorized - please re-authenticate"
            elif response.status_code == 404:
                return False, None, "Not found"
            elif response.status_code >= 500:
                return False, None, "Server error - please try again later"
            else:
                return False, None, f"API returned status {response.status_code}"
        
        except requests.exceptions.Timeout:
            error_msg = "API request timed out"
            logger.error(error_msg)
            return False, None, error_msg
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except ValueError as e:
            error_msg = f"Invalid JSON response: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def get_all_activities(self, include_past: bool = False, 
                          org_group: Optional[str] = None) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
        """
        Get list of all activities
        
        Args:
            include_past: Include past activities
            org_group: Filter by org group (optional)
            
        Returns:
            Tuple of (success: bool, activities: list or None, error_message: str or None)
        """
        params = {
            "include_past": str(include_past).lower(),
        }
        if org_group:
            params["org_group"] = org_group
        
        success, data, error = self._make_request("GET", "/activities-all", params=params)
        
        if success and isinstance(data, list):
            logger.info(f"Retrieved {len(data)} activities")
            return True, data, None
        
        return success, None, error
    
    def get_activity_details(self, activity_id: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Get detailed information about a specific activity
        
        Args:
            activity_id: Activity ID
            
        Returns:
            Tuple of (success: bool, activity: dict or None, error_message: str or None)
        """
        endpoint = f"/activities/{activity_id}"
        success, data, error = self._make_request("GET", endpoint)
        
        if success:
            logger.info(f"Retrieved details for activity {activity_id}")
            return True, data, None
        
        return success, None, error
    
    def get_activities_for_youth(self, permission_code: str) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
        """
        Get activities for a youth based on permission code
        Used for parents to see activities their children are invited to
        
        Args:
            permission_code: Youth's 6-digit permission code
            
        Returns:
            Tuple of (success: bool, activities: list or None, error_message: str or None)
        """
        params = {
            "permission_code": permission_code,
        }
        
        success, data, error = self._make_request("GET", "/activities-all-parents", params=params)
        
        if success and isinstance(data, list):
            logger.info(f"Retrieved {len(data)} activities for youth")
            return True, data, None
        
        return success, None, error
    
    def get_activities_needing_permission(self, permission_code: str) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
        """
        Get activities that need parental permission
        
        Args:
            permission_code: Youth's 6-digit permission code
            
        Returns:
            Tuple of (success: bool, activities: list or None, error_message: str or None)
        """
        success, all_activities, error = self.get_activities_for_youth(permission_code)
        
        if not success:
            return False, None, error
        
        # Filter to only activities that require permission
        activities_needing_permission = [
            activity for activity in all_activities
            if activity.get("requires_permission", False)
        ]
        
        logger.info(f"Found {len(activities_needing_permission)} activities needing permission")
        return True, activities_needing_permission, None
    
    def grant_permission(self, youth_id: str, activity_id: str, 
                        permission_code: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Grant parental permission for a youth to participate in an activity
        
        Args:
            youth_id: Youth ID
            activity_id: Activity ID
            permission_code: Permission code for verification
            
        Returns:
            Tuple of (success: bool, result: dict or None, error_message: str or None)
        """
        payload = {
            "youth_id": youth_id,
            "activity_id": activity_id,
            "permission_code": permission_code,
        }
        
        success, data, error = self._make_request("POST", "/activity-permissions", json_data=payload)
        
        if success:
            logger.info(f"Permission granted for youth {youth_id} for activity {activity_id}")
            return True, data, None
        
        return success, None, error
    
    def get_permission_info(self, activity_id: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Get permission requirements for a specific activity
        
        Args:
            activity_id: Activity ID
            
        Returns:
            Tuple of (success: bool, info: dict or None, error_message: str or None)
        """
        endpoint = f"/activities/permission-info/{activity_id}"
        success, data, error = self._make_request("GET", endpoint)
        
        if success:
            return True, data, None
        
        return success, None, error
    
    def get_activities_for_group(self, org_group: str, token: Optional[str] = None) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
        """
        Get all activities for a specific organization group
        
        Args:
            org_group: Organization group name (e.g., "younger young women")
            token: JWT token for authentication (optional)
            
        Returns:
            Tuple of (success: bool, activities: list or None, error_message: str or None)
        """
        params = {
            "org_group": org_group,
        }
        
        success, data, error = self._make_request("GET", "/activity-groups", params=params, token=token)
        
        if success and isinstance(data, list):
            logger.info(f"Retrieved {len(data)} activities for group {org_group}")
            return True, data, None
        
        return success, None, error
