"""
NextActivityIntent Handler - Gets the next upcoming activity
"""

import logging
from datetime import datetime
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from utils.constants import RESPONSE_MESSAGES
from utils.response_formatter import ResponseFormatter
from models.session import SessionState
from api.client import APIClient

logger = logging.getLogger(__name__)


class NextActivityIntentHandler:
    """Handle NextActivityIntent - get next upcoming activity"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        """Check if this handler should handle the request"""
        return handler_input.request_envelope.request.intent.name == "NextActivityIntent"
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Handle next activity request"""
        logger.info("NextActivityIntent received")
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        # Check if user is authenticated
        if not session_state.is_setup_complete():
            speech_text = "Please complete setup first. " + RESPONSE_MESSAGES["welcome"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(speech_text) \
                .response
        
        # Get activities based on user type
        if session_state.is_parent() and session_state.selected_child:
            # Parent viewing child's activities
            success, activities, error = self.api_client.get_activities_for_youth(
                session_state.selected_child.permission_code
            )
        elif session_state.is_youth() and session_state.permission_code:
            # Youth viewing their activities
            success, activities, error = self.api_client.get_activities_for_youth(
                session_state.permission_code
            )
        else:
            speech_text = "Unable to retrieve activities. Please try again."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        if not success:
            logger.error(f"Failed to retrieve activities: {error}")
            speech_text = error or RESPONSE_MESSAGES["api_error"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        if not activities:
            speech_text = RESPONSE_MESSAGES["no_activities"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Find the next activity by sorting by date
        next_activity = self._find_next_activity(activities)
        
        if not next_activity:
            speech_text = RESPONSE_MESSAGES["no_activities"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Format for voice
        activity_details = ResponseFormatter.format_activity_details(next_activity)
        speech_text = RESPONSE_MESSAGES["next_activity_intro"] + activity_details
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Would you like more details about this activity?") \
            .response
    
    @staticmethod
    def _find_next_activity(activities):
        """Find the next upcoming activity by date"""
        now = datetime.now()
        upcoming_activities = []
        
        for activity in activities:
            date_str = activity.get("date_start") or activity.get("date", "")
            if not date_str:
                continue
            
            try:
                # Parse date
                if "T" in date_str:
                    activity_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    activity_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                # Only include future activities
                if activity_date >= now:
                    upcoming_activities.append((activity_date, activity))
            except (ValueError, TypeError) as e:
                logger.debug(f"Error parsing activity date '{date_str}': {e}")
                continue
        
        if not upcoming_activities:
            return None
        
        # Sort by date and return the first one
        upcoming_activities.sort(key=lambda x: x[0])
        return upcoming_activities[0][1]
