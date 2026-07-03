"""
ActivityDetailsIntent Handler - Gets details about a specific activity
"""

import logging
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from utils.constants import RESPONSE_MESSAGES
from utils.response_formatter import ResponseFormatter
from models.session import SessionState
from api.client import APIClient

logger = logging.getLogger(__name__)


class ActivityDetailsIntentHandler:
    """Handle ActivityDetailsIntent - get details about specific activity"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        """Check if this handler should handle the request"""
        return handler_input.request_envelope.request.intent.name == "ActivityDetailsIntent"
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Handle activity details request"""
        logger.info("ActivityDetailsIntent received")
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        # Check if user is authenticated
        if not session_state.is_setup_complete():
            speech_text = "Please complete setup first. " + RESPONSE_MESSAGES["welcome"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(speech_text) \
                .response
        
        # Get slots
        intent = handler_input.request_envelope.request.intent
        
        # Try to get activity by name or number
        activity = None
        activity_name_slot = intent.slots.get("activity_name")
        activity_number_slot = intent.slots.get("activity_number")
        
        if activity_name_slot and activity_name_slot.value:
            # User said activity name
            activity = self._find_activity_by_name(
                session_state.recent_activities or [],
                activity_name_slot.value
            )
        elif activity_number_slot and activity_number_slot.value:
            # User said activity number
            try:
                activity_index = int(activity_number_slot.value) - 1
                if session_state.recent_activities and 0 <= activity_index < len(session_state.recent_activities):
                    activity = session_state.recent_activities[activity_index]
            except (ValueError, IndexError):
                pass
        
        if not activity:
            speech_text = "I couldn't find that activity. Please try listing activities first."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # If we have activity ID but not full details, fetch them
        activity_id = activity.get("activity_id")
        if activity_id and len(activity.get("description", "")) < 50:
            # Fetch full details
            success, full_activity, error = self.api_client.get_activity_details(activity_id)
            if success and full_activity:
                activity = full_activity
            else:
                logger.debug(f"Could not fetch full activity details: {error}")
        
        # Format for voice
        speech_text = ResponseFormatter.format_activity_details(activity)
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Is there anything else you'd like to know?") \
            .response
    
    @staticmethod
    def _find_activity_by_name(activities, search_name):
        """Find activity by name (case-insensitive partial match)"""
        search_lower = search_name.lower()
        
        for activity in activities:
            activity_name = (activity.get("activity_name") or activity.get("name", "")).lower()
            if search_lower in activity_name or activity_name in search_lower:
                return activity
        
        return None
