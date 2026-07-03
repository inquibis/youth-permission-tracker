"""
ListActivitiesIntent Handler - Lists upcoming activities for the user
"""

import logging
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from utils.constants import RESPONSE_MESSAGES, MAX_ACTIVITIES_IN_RESPONSE
from utils.response_formatter import ResponseFormatter
from models.session import SessionState
from api.client import APIClient

logger = logging.getLogger(__name__)


class ListActivitiesIntentHandler:
    """Handle ListActivitiesIntent - list upcoming activities"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        """Check if this handler should handle the request"""
        return handler_input.request_envelope.request.intent.name == "ListActivitiesIntent"
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Handle list activities request"""
        logger.info("ListActivitiesIntent received")
        
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
        
        # Format and cache activities for later reference
        session_state.recent_activities = activities
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        # Format activities for voice
        speech_text = ResponseFormatter.format_activity_list(
            activities,
            max_items=MAX_ACTIVITIES_IN_RESPONSE
        )
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Would you like more details or help with something else?") \
            .response
