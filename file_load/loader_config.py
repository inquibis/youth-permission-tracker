"""
Configuration for Youth Data Loader
"""

import os
from pathlib import Path

# API Configuration
API_BASE_URL = os.getenv("YOUTH_API_URL", "http://localhost:5000")
"""Base URL for the youth-permission-tracker API. Can be overridden via YOUTH_API_URL environment variable."""

API_ENDPOINT_YOUTH = f"{API_BASE_URL}/youth"
"""POST endpoint for creating youth accounts."""

API_ENDPOINT_USERS = f"{API_BASE_URL}/users"
"""POST endpoint for submitting medical/permission data (Phase 2)."""

# Loader Configuration
DATA_FILE = Path(__file__).parent / "youth_data.json"
"""Path to the youth data JSON file."""

LOG_FILE = Path(__file__).parent / "loader.log"
"""Path to the loader log file."""

# Retry Configuration
MAX_RETRIES = 3
"""Maximum number of retry attempts for failed API calls."""

RETRY_DELAY_SECONDS = 2
"""Delay in seconds between retry attempts."""

# Request Configuration
REQUEST_TIMEOUT_SECONDS = 30
"""Timeout for API requests in seconds."""

# Batch Configuration
BATCH_SIZE = 10
"""Number of youth to process before checking progress. Set to 0 to disable batching."""

# Error Handling
SKIP_ON_DUPLICATE = True
"""Skip entries with duplicate usernames (409 Conflict) and continue processing."""

SKIP_ON_VALIDATION_ERROR = False
"""Skip entries that fail validation and continue processing."""

SKIP_ON_API_ERROR = False
"""Skip entries that fail on API error and continue processing."""

# Output Configuration
VERBOSE = True
"""Print detailed progress information."""

DRY_RUN = False
"""When True, validate data and show what would be loaded without making API calls."""

# Schema Configuration
SCHEMA_FILE = Path(__file__).parent / "youth_import_schema.json"
"""Path to the JSON schema for validation."""

REQUIRED_FIELDS = ["first_name", "last_name", "group"]
"""Fields that must be present in each youth entry."""

# Group Validation
ALLOWED_GROUPS = ["Priest", "Teacher", "YM", "YW"]
"""Valid group values."""
