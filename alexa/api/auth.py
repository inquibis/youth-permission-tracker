"""
Authentication module for Youth Permission Tracker API
Handles JWT tokens, permission codes, and hybrid authentication
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages authentication with the Youth Permission Tracker API"""
    
    def __init__(self, api_url: str, api_timeout: int = 10):
        """
        Initialize the authentication manager
        
        Args:
            api_url: Base URL of the API (e.g., http://api-youth.lthome.us)
            api_timeout: Request timeout in seconds
        """
        self.api_url = api_url
        self.api_timeout = api_timeout
        self.current_token = None
        self.token_expiry = None
    
    def get_jwt_token(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Authenticate with username and password to get JWT token
        
        Args:
            username: Username for API
            password: Password for API
            
        Returns:
            Tuple of (success: bool, token: str or None, error_message: str or None)
        """
        try:
            token_url = urljoin(self.api_url, "/token")
            payload = {
                "username": username,
                "password": password,
            }
            
            response = requests.post(
                token_url,
                data=payload,
                timeout=self.api_timeout,
                headers={"Accept": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                if token:
                    # Token expires in 30 minutes, set expiry with 2-minute buffer
                    self.current_token = token
                    self.token_expiry = (datetime.now() + timedelta(minutes=28)).isoformat()
                    logger.info("Successfully obtained JWT token")
                    return True, token, None
                else:
                    return False, None, "No token in response"
            else:
                error_msg = f"Authentication failed: {response.status_code}"
                logger.error(error_msg)
                return False, None, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = "Authentication request timed out"
            logger.error(error_msg)
            return False, None, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during authentication: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during authentication: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def validate_permission_code(self, permission_code: str) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Validate a permission code format and optionally against the API
        
        Args:
            permission_code: 6-digit permission code
            
        Returns:
            Tuple of (is_valid: bool, youth_info: dict or None, error_message: str or None)
        """
        # Basic format validation: 6 digits
        if not permission_code or len(permission_code) != 6 or not permission_code.isdigit():
            return False, None, "Permission code must be 6 digits"
        
        # Additional validation could include API lookup to verify code exists
        # For now, just validate format
        logger.info(f"Permission code format validated: {permission_code[:2]}****")
        return True, {"permission_code": permission_code}, None
    
    def is_token_valid(self, token: Optional[str], token_expiry: Optional[str]) -> bool:
        """
        Check if a JWT token is still valid
        
        Args:
            token: JWT token string
            token_expiry: Expiry datetime as ISO format string
            
        Returns:
            True if token is valid and not expired, False otherwise
        """
        if not token or not token_expiry:
            return False
        
        try:
            expiry = datetime.fromisoformat(token_expiry)
            is_valid = datetime.now() < expiry
            if not is_valid:
                logger.debug("Token has expired")
            return is_valid
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing token expiry: {e}")
            return False
    
    def get_valid_token(self, token: Optional[str], token_expiry: Optional[str],
                       username: Optional[str] = None, password: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Get a valid token, refreshing if necessary
        
        Args:
            token: Current JWT token (may be expired)
            token_expiry: Current token expiry time
            username: Username for refreshing token (if needed)
            password: Password for refreshing token (if needed)
            
        Returns:
            Tuple of (success: bool, token: str or None, error_message: str or None)
        """
        if self.is_token_valid(token, token_expiry):
            logger.debug("Existing token is still valid")
            return True, token, None
        
        # Token is expired or missing, need to refresh
        if username and password:
            logger.info("Token expired or missing, attempting refresh")
            return self.get_jwt_token(username, password)
        else:
            return False, None, "Token is invalid and credentials not provided for refresh"


class HybridAuthManager(AuthManager):
    """
    Extended auth manager supporting hybrid authentication:
    - Permission code (6 digits) for initial access
    - Optional upgrade to username/password for full features
    """
    
    def __init__(self, api_url: str, api_timeout: int = 10):
        super().__init__(api_url, api_timeout)
        self.permission_code_cache = {}  # Cache for permission code lookups
    
    def setup_with_permission_code(self, permission_code: str) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Set up session using permission code (6-digit code)
        This is the primary authentication method for parents/youth
        
        Args:
            permission_code: 6-digit permission code
            
        Returns:
            Tuple of (success: bool, user_info: dict or None, error_message: str or None)
        """
        is_valid, user_info, error = self.validate_permission_code(permission_code)
        
        if not is_valid:
            return False, None, error
        
        # Permission code is valid, user can proceed
        # We don't need a JWT token for permission-code-based access in MVP
        logger.info("User authenticated with permission code")
        return True, user_info, None
    
    def upgrade_to_full_auth(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upgrade from permission code auth to full username/password auth
        This enables more features and is an optional upgrade path
        
        Args:
            username: Username for full auth
            password: Password for full auth
            
        Returns:
            Tuple of (success: bool, token: str or None, error_message: str or None)
        """
        return self.get_jwt_token(username, password)
