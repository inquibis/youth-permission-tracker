"""
Session and Authentication Management Intents
Handles user setup, authentication, and child selection
"""

import logging
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from utils.constants import RESPONSE_MESSAGES, SESSION_KEYS
from models.session import SessionState, ChildInfo
from api.auth import HybridAuthManager

logger = logging.getLogger(__name__)


class UserTypeIntentHandler:
    """Handle user type selection (parent or youth)"""
    
    def __init__(self, auth_manager: HybridAuthManager):
        self.auth_manager = auth_manager
    
    def handle_parent_selected(self, handler_input: HandlerInput) -> Response:
        """User selected parent mode"""
        logger.info("Parent mode selected")
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        session_state.user_type = "parent"
        session_state.setup_step = "awaiting_permission_code"
        
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        speech_text = RESPONSE_MESSAGES["welcome_parent"]
        reprompt = RESPONSE_MESSAGES["permission_code_prompt"]
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask(reprompt) \
            .response
    
    def handle_youth_selected(self, handler_input: HandlerInput) -> Response:
        """User selected youth mode"""
        logger.info("Youth mode selected")
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        session_state.user_type = "youth"
        session_state.setup_step = "awaiting_permission_code"
        
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        speech_text = RESPONSE_MESSAGES["welcome_youth"]
        reprompt = RESPONSE_MESSAGES["permission_code_prompt"]
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask(reprompt) \
            .response


class PermissionCodeIntentHandler:
    """Handle permission code entry"""
    
    def __init__(self, auth_manager: HybridAuthManager):
        self.auth_manager = auth_manager
    
    def handle(self, handler_input: HandlerInput, permission_code: str) -> Response:
        """Process permission code"""
        logger.info(f"Permission code provided: {permission_code[:2]}****")
        
        # Validate permission code
        is_valid, user_info, error = self.auth_manager.setup_with_permission_code(permission_code)
        
        if not is_valid:
            logger.warning(f"Invalid permission code: {error}")
            speech_text = RESPONSE_MESSAGES["permission_code_invalid"]
            reprompt = RESPONSE_MESSAGES["permission_code_prompt"]
            
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(reprompt) \
                .response
        
        # Permission code is valid
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        session_state.permission_code = permission_code
        session_state.setup_step = "awaiting_pin" if session_state.is_parent() else "complete"
        
        # For now, assume single child
        session_state.selected_child = ChildInfo(
            child_id="youth_1",  # Will be updated with real data in future
            child_name="Your child",
            org_group="general",
            permission_code=permission_code
        )
        
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        if session_state.is_parent():
            # Parent needs to set PIN
            speech_text = RESPONSE_MESSAGES["pin_setup_prompt"]
            reprompt = "What 4-digit PIN would you like to use?"
        else:
            # Youth setup complete
            session_state.setup_step = "complete"
            handler_input.attributes_manager.session_attributes = session_state.to_dict()
            speech_text = RESPONSE_MESSAGES["setup_complete"] + " " + RESPONSE_MESSAGES["help_text"]
            reprompt = RESPONSE_MESSAGES["help_text"]
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask(reprompt) \
            .response


class PINSetupIntentHandler:
    """Handle PIN setup for parents"""
    
    def handle(self, handler_input: HandlerInput, pin: str) -> Response:
        """Process PIN setup"""
        logger.info("PIN setup requested")
        
        # Validate PIN is 4 digits
        if not pin or len(pin) != 4 or not pin.isdigit():
            speech_text = "Please provide a 4-digit PIN."
            reprompt = RESPONSE_MESSAGES["pin_setup_prompt"]
            
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(reprompt) \
                .response
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        session_state.pin = pin
        session_state.setup_step = "complete"
        
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        speech_text = RESPONSE_MESSAGES["pin_setup_confirm"] + " " + RESPONSE_MESSAGES["setup_complete"] + " " + RESPONSE_MESSAGES["help_text"]
        reprompt = RESPONSE_MESSAGES["help_text"]
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask(reprompt) \
            .response


class ChildSelectionIntentHandler:
    """Handle child selection for parents"""
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Handle child selection"""
        logger.info("ChildSelectionIntent received")
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        if not session_state.is_parent():
            speech_text = "This feature is only for parents."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # For MVP, we're assuming single child
        # In future, this will support multiple children
        if len(session_state.children) <= 1:
            # Only one child, no need to select
            return handler_input.response_builder \
                .speak("You only have one child registered.") \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Multiple children - present selection
        speech_text = "Which child? "
        choices = []
        for i, child in enumerate(session_state.children, 1):
            choices.append(f"{i}) {child.child_name}")
        
        speech_text += ", ".join(choices)
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask(speech_text) \
            .response
