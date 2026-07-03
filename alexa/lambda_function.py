"""
Main Lambda entry point for Alexa Skill
Handles all Alexa requests and routes them to appropriate handlers
"""

import logging
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from utils.constants import RESPONSE_MESSAGES, API_URL, API_TIMEOUT, DEBUG
from models.session import SessionState, ChildInfo
from api.client import APIClient
from api.auth import HybridAuthManager

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Initialize API clients
api_client = APIClient(API_URL, API_TIMEOUT)
auth_manager = HybridAuthManager(API_URL, API_TIMEOUT)

# Initialize Skill Builder
sb = SkillBuilder()


# ============================================================================
# Launch Request Handler - Entry point when skill is opened
# ============================================================================

class LaunchRequestHandler:
    """Handle LaunchRequest - called when user opens the skill"""
    
    can_handle_func = staticmethod(lambda handler_input: is_request_type("LaunchRequest")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("LaunchRequest received")
        
        # Get or initialize session state
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        # If setup is complete, ask what they want to do
        if session_state.is_setup_complete():
            speech_text = "Welcome back! " + RESPONSE_MESSAGES["help_text"]
        else:
            speech_text = RESPONSE_MESSAGES["welcome"]
        
        # Save session state
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask(speech_text if not session_state.is_setup_complete() else RESPONSE_MESSAGES["help_text"]) \
            .response


# ============================================================================
# Setup Intent Handlers (for authentication flow)
# ============================================================================

class UserTypeIntentHandler:
    """Handle user type selection - parent or youth"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("UserTypeIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("UserTypeIntent received")
        
        intent = handler_input.request_envelope.request.intent
        user_type_slot = intent.slots.get("user_type")
        
        if not user_type_slot or not user_type_slot.value:
            speech_text = RESPONSE_MESSAGES["welcome"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask("Are you a parent or a youth?") \
                .response
        
        user_type = user_type_slot.value.lower()
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        if "parent" in user_type:
            session_state.user_type = "parent"
            welcome_msg = RESPONSE_MESSAGES["welcome_parent"]
        elif "youth" in user_type or "kid" in user_type or "child" in user_type:
            session_state.user_type = "youth"
            welcome_msg = RESPONSE_MESSAGES["welcome_youth"]
        else:
            speech_text = "I didn't understand that. Are you a parent or a youth?"
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(speech_text) \
                .response
        
        session_state.setup_step = "awaiting_permission_code"
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        return handler_input.response_builder \
            .speak(welcome_msg) \
            .ask(RESPONSE_MESSAGES["permission_code_prompt"]) \
            .response


class PermissionCodeIntentHandler:
    """Handle permission code entry during setup"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("PermissionCodeIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("PermissionCodeIntent received")
        
        intent = handler_input.request_envelope.request.intent
        code_slot = intent.slots.get("permission_code")
        
        if not code_slot or not code_slot.value:
            return handler_input.response_builder \
                .speak(RESPONSE_MESSAGES["permission_code_prompt"]) \
                .ask(RESPONSE_MESSAGES["permission_code_prompt"]) \
                .response
        
        permission_code = code_slot.value
        
        # Validate permission code
        is_valid, user_info, error = auth_manager.setup_with_permission_code(permission_code)
        
        if not is_valid:
            logger.warning(f"Invalid permission code: {error}")
            return handler_input.response_builder \
                .speak(RESPONSE_MESSAGES["permission_code_invalid"]) \
                .ask(RESPONSE_MESSAGES["permission_code_prompt"]) \
                .response
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        session_state.permission_code = permission_code
        session_state.selected_child = ChildInfo(
            child_id="youth_1",
            child_name="Your child",
            org_group="general",
            permission_code=permission_code
        )
        
        if session_state.is_parent():
            session_state.setup_step = "awaiting_pin"
            handler_input.attributes_manager.session_attributes = session_state.to_dict()
            return handler_input.response_builder \
                .speak(RESPONSE_MESSAGES["pin_setup_prompt"]) \
                .ask("What 4-digit PIN would you like to use?") \
                .response
        else:
            session_state.setup_step = "complete"
            handler_input.attributes_manager.session_attributes = session_state.to_dict()
            return handler_input.response_builder \
                .speak(RESPONSE_MESSAGES["setup_complete"] + " " + RESPONSE_MESSAGES["help_text"]) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response


class PINSetupIntentHandler:
    """Handle PIN setup for parents"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("PINSetupIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("PINSetupIntent received")
        
        intent = handler_input.request_envelope.request.intent
        pin_slot = intent.slots.get("pin")
        
        if not pin_slot or not pin_slot.value:
            return handler_input.response_builder \
                .speak(RESPONSE_MESSAGES["pin_setup_prompt"]) \
                .ask(RESPONSE_MESSAGES["pin_setup_prompt"]) \
                .response
        
        pin = pin_slot.value
        
        # Validate PIN is 4 digits
        if not pin or len(pin) != 4 or not pin.isdigit():
            speech_text = "Please provide a 4-digit PIN."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["pin_setup_prompt"]) \
                .response
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        session_state.pin = pin
        session_state.setup_step = "complete"
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        return handler_input.response_builder \
            .speak(RESPONSE_MESSAGES["pin_setup_confirm"] + " " + RESPONSE_MESSAGES["setup_complete"] + " " + RESPONSE_MESSAGES["help_text"]) \
            .ask(RESPONSE_MESSAGES["help_text"]) \
            .response



class HelpIntentHandler:
    """Handle Help intent"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("AMAZON.HelpIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("HelpIntent received")
        
        speech_text = RESPONSE_MESSAGES["help_text"]
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask(speech_text) \
            .response


# ============================================================================
# Stop/Cancel Intent Handler
# ============================================================================

class StopIntentHandler:
    """Handle Stop/Cancel intent"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("AMAZON.StopIntent")(handler_input) or is_intent_name("AMAZON.CancelIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("StopIntent/CancelIntent received")
        
        speech_text = "Goodbye!"
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .response


# ============================================================================
# Fallback Handler - catch unhandled requests
# ============================================================================

class FallbackHandler:
    """Handle requests that don't match any other handlers"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("AMAZON.FallbackIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.warning("FallbackIntent received - no matching handler")
        
        speech_text = "I didn't understand that. " + RESPONSE_MESSAGES["help_text"]
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask(speech_text) \
            .response


# ============================================================================
# Exception Handler
# ============================================================================

class GlobalExceptionHandler:
    """Handle any exceptions that occur during skill execution"""
    
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True
    
    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.error(f"Exception occurred: {exception}", exc_info=True)
        
        speech_text = RESPONSE_MESSAGES["generic_error"]
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("What would you like to do?") \
            .response


# ============================================================================
# Placeholder Intent Handlers (to be implemented in Phase 3)
# ============================================================================

class ListActivitiesIntentHandler:
    """Handle ListActivitiesIntent - list upcoming activities"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("ListActivitiesIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
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
            success, activities, error = api_client.get_activities_for_youth(
                session_state.selected_child.permission_code
            )
        elif session_state.is_youth() and session_state.permission_code:
            success, activities, error = api_client.get_activities_for_youth(
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
        
        from utils.response_formatter import ResponseFormatter
        from utils.constants import MAX_ACTIVITIES_IN_RESPONSE
        
        # Format and cache activities
        session_state.recent_activities = activities
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        speech_text = ResponseFormatter.format_activity_list(activities, MAX_ACTIVITIES_IN_RESPONSE)
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Would you like more details or help with something else?") \
            .response


class NextActivityIntentHandler:
    """Handle NextActivityIntent - get next upcoming activity"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("NextActivityIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("NextActivityIntent received")
        
        from datetime import datetime
        from utils.response_formatter import ResponseFormatter
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        if not session_state.is_setup_complete():
            speech_text = "Please complete setup first. " + RESPONSE_MESSAGES["welcome"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(speech_text) \
                .response
        
        if session_state.is_parent() and session_state.selected_child:
            success, activities, error = api_client.get_activities_for_youth(
                session_state.selected_child.permission_code
            )
        elif session_state.is_youth() and session_state.permission_code:
            success, activities, error = api_client.get_activities_for_youth(
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
        
        # Find next activity
        now = datetime.now()
        upcoming = []
        for activity in activities:
            date_str = activity.get("date_start") or activity.get("date", "")
            if not date_str:
                continue
            try:
                if "T" in date_str:
                    activity_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    activity_date = datetime.strptime(date_str, "%Y-%m-%d")
                if activity_date >= now:
                    upcoming.append((activity_date, activity))
            except (ValueError, TypeError):
                continue
        
        if not upcoming:
            speech_text = RESPONSE_MESSAGES["no_activities"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        upcoming.sort(key=lambda x: x[0])
        next_activity = upcoming[0][1]
        
        activity_details = ResponseFormatter.format_activity_details(next_activity)
        speech_text = RESPONSE_MESSAGES["next_activity_intro"] + activity_details
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Would you like more details about this activity?") \
            .response


class ActivityDetailsIntentHandler:
    """Handle ActivityDetailsIntent - get details about specific activity"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("ActivityDetailsIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("ActivityDetailsIntent received")
        from utils.response_formatter import ResponseFormatter
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        if not session_state.is_setup_complete():
            speech_text = "Please complete setup first. " + RESPONSE_MESSAGES["welcome"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(speech_text) \
                .response
        
        intent = handler_input.request_envelope.request.intent
        activity = None
        
        activity_name_slot = intent.slots.get("activity_name")
        activity_number_slot = intent.slots.get("activity_number")
        
        if activity_name_slot and activity_name_slot.value:
            search_lower = activity_name_slot.value.lower()
            for act in session_state.recent_activities or []:
                act_name = (act.get("activity_name") or act.get("name", "")).lower()
                if search_lower in act_name or act_name in search_lower:
                    activity = act
                    break
        elif activity_number_slot and activity_number_slot.value:
            try:
                idx = int(activity_number_slot.value) - 1
                if session_state.recent_activities and 0 <= idx < len(session_state.recent_activities):
                    activity = session_state.recent_activities[idx]
            except (ValueError, IndexError):
                pass
        
        if not activity:
            speech_text = "I couldn't find that activity. Please try listing activities first."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        activity_id = activity.get("activity_id")
        if activity_id and len(activity.get("description", "")) < 50:
            success, full_activity, error = api_client.get_activity_details(activity_id)
            if success and full_activity:
                activity = full_activity
        
        speech_text = ResponseFormatter.format_activity_details(activity)
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Is there anything else you'd like to know?") \
            .response


class ActivitiesNeedingPermissionIntentHandler:
    """Handle ActivitiesNeedingPermissionIntent - check activities needing permission"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("ActivitiesNeedingPermissionIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("ActivitiesNeedingPermissionIntent received")
        from utils.response_formatter import ResponseFormatter
        from utils.constants import MAX_PERMISSION_ITEMS_IN_RESPONSE
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        if not session_state.is_setup_complete():
            speech_text = "Please complete setup first. " + RESPONSE_MESSAGES["welcome"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(speech_text) \
                .response
        
        if not session_state.is_parent():
            speech_text = "This feature is only available for parents."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        if not session_state.selected_child:
            speech_text = "No child selected. Please set up your child first."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        success, activities, error = api_client.get_activities_needing_permission(
            session_state.selected_child.permission_code
        )
        
        if not success:
            logger.error(f"Failed to retrieve activities needing permission: {error}")
            speech_text = error or RESPONSE_MESSAGES["api_error"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        session_state.recent_activities = activities
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        speech_text = ResponseFormatter.format_permission_list(activities, MAX_PERMISSION_ITEMS_IN_RESPONSE)
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Which activity would you like to approve?") \
            .response


class GrantPermissionIntentHandler:
    """Handle GrantPermissionIntent - grant permission for activity"""
    
    can_handle_func = staticmethod(lambda handler_input: is_intent_name("GrantPermissionIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("GrantPermissionIntent received")
        
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        if not session_state.is_setup_complete():
            speech_text = "Please complete setup first. " + RESPONSE_MESSAGES["welcome"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(speech_text) \
                .response
        
        if not session_state.is_parent():
            speech_text = "This feature is only available for parents."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        intent = handler_input.request_envelope.request.intent
        activity = None
        
        activity_name_slot = intent.slots.get("activity_name")
        activity_number_slot = intent.slots.get("activity_number")
        
        if activity_name_slot and activity_name_slot.value:
            search_lower = activity_name_slot.value.lower()
            for act in session_state.recent_activities or []:
                act_name = (act.get("activity_name") or act.get("name", "")).lower()
                if search_lower in act_name or act_name in search_lower:
                    activity = act
                    break
        elif activity_number_slot and activity_number_slot.value:
            try:
                idx = int(activity_number_slot.value) - 1
                if session_state.recent_activities and 0 <= idx < len(session_state.recent_activities):
                    activity = session_state.recent_activities[idx]
            except (ValueError, IndexError):
                pass
        
        if not activity:
            speech_text = "I couldn't find that activity. Please try listing activities needing approval first."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        if not activity.get("requires_permission", False):
            speech_text = "This activity doesn't require permission."
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Get PIN from slots
        pin_slot = intent.slots.get("pin")
        
        if not pin_slot or not pin_slot.value:
            activity_name = activity.get("activity_name") or activity.get("name", "this activity")
            speech_text = f"To approve {activity_name}, please provide your 4-digit PIN."
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
        
        # Grant permission via API
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
        
        youth_id = session_state.selected_child.child_id
        permission_code = session_state.selected_child.permission_code
        
        success, result, error = api_client.grant_permission(youth_id, activity_id, permission_code)
        
        if not success:
            logger.error(f"Failed to grant permission: {error}")
            speech_text = error or RESPONSE_MESSAGES["api_error"]
            return handler_input.response_builder \
                .speak(speech_text) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        activity_name = activity.get("activity_name") or activity.get("name", "the activity")
        speech_text = RESPONSE_MESSAGES["permission_granted"].format(activity_name=activity_name)
        logger.info(f"Permission granted for activity {activity_id}")
        
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask("Is there anything else I can help you with?") \
            .response


# ============================================================================
# Register Handlers with Skill Builder
# ============================================================================

# Add handlers to skill builder
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(UserTypeIntentHandler())
sb.add_request_handler(PermissionCodeIntentHandler())
sb.add_request_handler(PINSetupIntentHandler())
sb.add_request_handler(ListActivitiesIntentHandler())
sb.add_request_handler(NextActivityIntentHandler())
sb.add_request_handler(ActivityDetailsIntentHandler())
sb.add_request_handler(ActivitiesNeedingPermissionIntentHandler())
sb.add_request_handler(GrantPermissionIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(StopIntentHandler())
sb.add_request_handler(FallbackHandler())
sb.add_exception_handler(GlobalExceptionHandler())

# Create the skill lambda handler
lambda_handler = sb.lambda_handler()
