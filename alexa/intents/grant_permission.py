"""
GrantPermissionIntent Handler - Grants parental permission for an activity
"""

import logging
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from utils.constants import RESPONSE_MESSAGES
from models.session import SessionState
from api.client import APIClient

logger = logging.getLogger(__name__)


class GrantPermissionIntentHandler:
    """Handle GrantPermissionIntent - grant permission for activity"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        """Check if this handler should handle the request"""
        return handler_input.request_envelope.request.intent.name == "GrantPermissionIntent"
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Handle permission grant request"""
        logger.info("GrantPermissionIntent received")
        
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
        
        # Get selected activity (by name or number)
        intent = handler_input.request_envelope.request.intent
        
        activity = None
        activity_name_slot = intent.slots.get("activity_name")
        activity_number_slot = intent.slots.get("activity_number")
        
        if activity_name_slot and activity_name_slot.value:
            activity = self._find_activity_by_name(
                session_state.recent_activities or [],
                activity_name_slot.value
            )
        elif activity_number_slot and activity_number_slot.value:
            try:
                activity_index = int(activity_number_slot.value) - 1
                if session_state.recent_activities and 0 <= activity_index < len(session_state.recent_activities):
                    activity = session_state.recent_activities[activity_index]
            except (ValueError, IndexError):
                pass
        
        if not activity:
            speech_text = "I couldn't find that activity. Please try listing activities needing approval first."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Check if activity requires permission
        if not activity.get("requires_permission", False):
            speech_text = "This activity doesn't require permission."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Get PIN from slots
        intent_slots = intent.slots
        pin_slot = intent_slots.get("pin")
        
        if not pin_slot or not pin_slot.value:
            # PIN not provided in this request - ask for it
            activity_name = activity.get("activity_name") or activity.get("name", "this activity")
            speech_text = f"To approve {activity_name}, please provide your 4-digit PIN."
            
            # Store activity in session for next request
            session_state.recent_activities = [activity] + (session_state.recent_activities or [])[1:]
            handler_input.attributes_manager.session_attributes = session_state.to_dict()
            
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["permission_ask_for_pin"]) \
                .response
        
        # Verify PIN
        pin = pin_slot.value
        if not session_state.pin or pin != session_state.pin:
            logger.warning("Invalid PIN provided")
            speech_text = RESPONSE_MESSAGES["permission_check_failed"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask("Would you like to try again?") \
                .response
        
        # PIN is correct, grant permission
        activity_id = activity.get("activity_id")
        if not activity_id:
            speech_text = "Could not process permission - activity ID not found."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        if not session_state.selected_child:
            speech_text = "Could not process permission - child not selected."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Call API to grant permission
        youth_id = session_state.selected_child.child_id
        permission_code = session_state.selected_child.permission_code
        
        success, result, error = self.api_client.grant_permission(
            youth_id,
            activity_id,
            permission_code
        )
        
        if not success:
            logger.error(f"Failed to grant permission: {error}")
            speech_text = error or RESPONSE_MESSAGES["api_error"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Permission granted successfully
        activity_name = activity.get("activity_name") or activity.get("name", "the activity")
        speech_text = RESPONSE_MESSAGES["permission_granted"].format(activity_name=activity_name)
        
        logger.info(f"Permission granted for activity {activity_id}")
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Is there anything else I can help you with?") \
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
