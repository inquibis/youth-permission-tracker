"""
Constants for the Youth Permission Tracker Alexa Skill
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_URL = os.getenv("API_URL", "http://api-youth.lthome.us")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))

# Alexa Configuration
ALEXA_SKILL_ID = os.getenv("ALEXA_SKILL_ID", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Response Messages
RESPONSE_MESSAGES = {
    # Launch/Setup
    "welcome": "Welcome to Youth Permission Tracker. I can help you manage activities and permissions. Are you a parent or a youth?",
    "welcome_parent": "Great! I'm set up for parent mode. To get started, I'll need your 6-digit permission code.",
    "welcome_youth": "Great! I'm set up for youth mode. To get started, I'll need your 6-digit permission code.",
    "permission_code_prompt": "Please provide your 6-digit permission code.",
    "permission_code_invalid": "That code isn't recognized. Please check and try again.",
    "pin_setup_prompt": "Now let's set up a 4-digit PIN to verify permission grants. What PIN would you like to use?",
    "pin_setup_confirm": "Your PIN is set. You'll need to enter this PIN when granting permissions to activities.",
    "setup_complete": "Setup complete! You're all set to use the skill.",
    
    # Activity Queries
    "no_activities": "You don't have any upcoming activities scheduled.",
    "activities_list_intro": "You have {count} upcoming activities. Here are the first few: ",
    "activity_item": "{name} on {date}",
    "activities_ask_details": "Would you like details about any of these?",
    
    "next_activity_intro": "Your next activity is ",
    "activity_details_template": "{name} is on {date} at {time} in {location}. {description}",
    "activity_cost": "The cost is {cost}.",
    "activity_overnight": "It's an overnight activity.",
    "activity_coed": "It's a coed activity.",
    
    # Permissions
    "permission_check_intro": "You have {count} activities that need your permission approval. ",
    "permission_grant_prompt": "Which activity would you like to approve?",
    "permission_ask_for_pin": "Please enter your 4-digit PIN to confirm.",
    "permission_granted": "Permission granted for {activity_name}.",
    "permission_denied": "Permission not granted.",
    "permission_check_failed": "I wasn't able to verify your PIN. Please try again.",
    
    # Errors
    "api_error": "I'm having trouble connecting to the service. Please try again in a moment.",
    "api_timeout": "The service is taking too long to respond. Please try again.",
    "auth_error": "There was an authentication error. Please set up again.",
    "generic_error": "Something went wrong. Please try again.",
    "help_text": "I can help you list your activities, find your next activity, get details about a specific activity, and manage permissions. What would you like to do?",
}

# Intent Names
INTENTS = {
    "launch": "LaunchRequest",
    "list_activities": "ListActivitiesIntent",
    "next_activity": "NextActivityIntent",
    "activity_details": "ActivityDetailsIntent",
    "check_permissions": "ActivitiesNeedingPermissionIntent",
    "grant_permission": "GrantPermissionIntent",
    "child_selection": "ChildSelectionIntent",
    "help": "AMAZON.HelpIntent",
    "stop": "AMAZON.StopIntent",
    "cancel": "AMAZON.CancelIntent",
}

# Slot Names
SLOTS = {
    "activity_name": "ActivityName",
    "activity_number": "ActivityNumber",
    "user_type": "UserType",
    "permission_code": "PermissionCode",
    "pin": "PIN",
    "child_name": "ChildName",
    "child_number": "ChildNumber",
}

# API Endpoints (relative to API_URL)
API_ENDPOINTS = {
    "token": "/token",
    "activities_all": "/activities-all",
    "activities_for_group": "/activity-groups",
    "activity_detail": "/activities/{activity_id}",
    "activities_for_parents": "/activities-all-parents",
    "activities_needing_approval": "/activities-pending-approval",
    "permission_grant": "/activity-permissions",
    "activity_permission_info": "/activities/permission-info/{activity_id}",
}

# Session Attribute Keys
SESSION_KEYS = {
    "user_type": "user_type",  # "parent" or "youth"
    "permission_code": "permission_code",
    "jwt_token": "jwt_token",
    "token_expiry": "token_expiry",
    "selected_child": "selected_child",  # {child_id, child_name, org_group}
    "children": "children",  # list of available children
    "setup_step": "setup_step",  # "awaiting_user_type", "awaiting_permission_code", "awaiting_pin", "complete"
    "pin": "pin",  # stored securely (hashed/salted in production)
    "recent_activities": "recent_activities",  # cache of last query result
    "org_group": "org_group",
}

# Max items to return in voice responses
MAX_ACTIVITIES_IN_RESPONSE = 3
MAX_PERMISSION_ITEMS_IN_RESPONSE = 5

# Time constants
TOKEN_REFRESH_BUFFER_MINUTES = 2  # Refresh token if within this buffer of expiry
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
