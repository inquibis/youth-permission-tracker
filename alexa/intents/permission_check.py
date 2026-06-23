"""
ActivitiesNeedingPermissionIntent Handler - Lists activities requiring parental permission
"""

import logging
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from utils.constants import RESPONSE_MESSAGES, MAX_PERMISSION_ITEMS_IN_RESPONSE
from utils.response_formatter import ResponseFormatter
from models.session import SessionState
from api.client import APIClient

logger = logging.getLogger(__name__)


class ActivitiesNeedingPermissionIntentHandler:
    """Handle ActivitiesNeedingPermissionIntent - check activities needing permission"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        """Check if this handler should handle the request"""
        return handler_input.request_envelope.request.intent.name == "ActivitiesNeedingPermissionIntent"
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Handle activities needing permission request"""
        logger.info("ActivitiesNeedingPermissionIntent received")
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        # Check if user is authenticated
        if not session_state.is_setup_complete():
            speech_text = "Please complete setup first. " + RESPONSE_MESSAGES["welcome"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(speech_text) \
                .response
        
        # This is a parent-only feature
        if not session_state.is_parent():
            speech_text = "This feature is only available for parents."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Get activities needing permission
        if not session_state.selected_child:
            speech_text = "No child selected. Please set up your child first."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        success, activities, error = self.api_client.get_activities_needing_permission(
            session_state.selected_child.permission_code
        )
        
        if not success:
            logger.error(f"Failed to retrieve activities needing permission: {error}")
            speech_text = error or RESPONSE_MESSAGES["api_error"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Cache activities for permission grant handler
        session_state.recent_activities = activities
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        # Format for voice
        speech_text = ResponseFormatter.format_permission_list(
            activities,
            max_items=MAX_PERMISSION_ITEMS_IN_RESPONSE
        )
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Which activity would you like to approve?") \
            .response
