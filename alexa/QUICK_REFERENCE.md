# Quick Reference Guide

## File Structure

```
alexa/
├── lambda_function.py                # ⭐ Main entry point - ALL intent handlers
├── requirements.txt                  # Dependencies for pip install
├── .env.example                      # Configuration template (copy to .env)
├── .gitignore                        # Git ignore patterns
├── skill.json                        # Alexa skill metadata
├── interaction_model.json            # Voice intents and utterances
├── test_skill.py                     # Unit tests
│
├── api/                              # API Communication
│   ├── __init__.py
│   ├── client.py                     # APIClient class (5 methods for API calls)
│   └── auth.py                       # HybridAuthManager (permission codes + PIN)
│
├── models/                           # Data Structures
│   ├── __init__.py
│   └── session.py                    # SessionState & ChildInfo dataclasses
│
├── intents/                          # Reference Intent Handlers (logic in lambda_function.py)
│   ├── __init__.py
│   ├── list_activities.py
│   ├── next_activity.py
│   ├── activity_details.py
│   ├── permission_check.py
│   ├── grant_permission.py
│   └── session_management.py
│
├── utils/                            # Utilities
│   ├── __init__.py
│   ├── constants.py                  # Config, messages, endpoints
│   └── response_formatter.py         # Voice response formatting
│
└── Documentation/
    ├── README.md                     # Feature overview & setup
    ├── ARCHITECTURE.md               # Technical architecture (this folder)
    ├── DEPLOYMENT_GUIDE.md           # AWS Lambda deployment steps
    ├── DEVELOPMENT_GUIDE.md          # Local testing & debugging
    └── QUICK_REFERENCE.md            # This file
```

## Key Classes & Functions

### SessionState (`models/session.py`)
```python
state = SessionState(
    user_type="parent",              # "parent" or "youth"
    permission_code="123456",
    pin="1234",
    selected_child=ChildInfo(...),
    setup_step="complete"            # "awaiting_user_type" → "complete"
)

state.is_parent()                    # True if parent
state.is_setup_complete()            # True if ready to use
state.is_token_expired()             # True if JWT expired
state.to_dict()                      # Convert to session attributes
SessionState.from_dict(attrs)        # Restore from session attributes
```

### APIClient (`api/client.py`)
```python
client = APIClient("http://api-youth.lthome.us", timeout=10)

# Get all activities
success, activities, error = client.get_all_activities(include_past=False)

# Get activities for a youth
success, activities, error = client.get_activities_for_youth("123456")

# Get activities needing permission
success, activities, error = client.get_activities_needing_permission("123456")

# Get activity details
success, activity, error = client.get_activity_details("activity_123")

# Grant permission
success, result, error = client.grant_permission("youth_1", "activity_123", "123456")
```

### ResponseFormatter (`utils/response_formatter.py`)
```python
formatter = ResponseFormatter()

# Format individual elements
date_str = formatter.format_date("2026-12-15")        # "December 15th"
time_str = formatter.format_time("14:30")             # "2:30 PM"
cost_str = formatter.format_cost(5.50)                # "five dollars and fifty cents"

# Format collections
activities_text = formatter.format_activity_list(
    activities,
    max_items=3
)

details_text = formatter.format_activity_details(activity)

permission_text = formatter.format_permission_list(
    activities_needing_permission,
    max_items=5
)
```

### Authentication (`api/auth.py`)
```python
auth = HybridAuthManager("http://api-youth.lthome.us")

# Validate permission code
is_valid, user_info, error = auth.validate_permission_code("123456")

# Check token validity
is_valid = auth.is_token_valid("token_string", "2024-01-15T10:00:00Z")

# Set up with permission code
is_valid, user_info, error = auth.setup_with_permission_code("123456")
```

## Constants & Configuration

### From `utils/constants.py`
```python
API_URL                              # Base API URL
API_TIMEOUT                          # Request timeout in seconds
RESPONSE_MESSAGES                    # Dict of all voice responses
INTENTS                              # Intent name constants
SLOTS                                # Slot name constants
API_ENDPOINTS                        # API endpoint paths
SESSION_KEYS                         # Session attribute keys
MAX_ACTIVITIES_IN_RESPONSE           # Limit list to 3 items
MAX_PERMISSION_ITEMS_IN_RESPONSE    # Limit to 5 items
```

### Response Messages (Sample)
```
"welcome": "Welcome to Youth Permission Tracker..."
"permission_code_invalid": "That code isn't recognized..."
"permission_granted": "Permission granted for {activity_name}."
"no_activities": "You don't have any upcoming activities..."
"api_error": "I'm having trouble connecting to the service..."
```

## Common Intent Handler Pattern

All intent handlers in `lambda_function.py` follow this pattern:

```python
class SomeIntentHandler:
    can_handle_func = staticmethod(
        lambda handler_input: is_intent_name("SomeIntent")(handler_input)
    )
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("SomeIntent received")
        
        # Get session state
        session_attrs = handler_input.attributes_manager.session_attributes or {}
        session_state = SessionState.from_dict(session_attrs)
        
        # Check authentication
        if not session_state.is_setup_complete():
            return handler_input.response_builder \
                .speak("Please complete setup first") \
                .ask("...") \
                .response
        
        # Call API
        success, data, error = api_client.some_method()
        
        if not success:
            return handler_input.response_builder \
                .speak(error or RESPONSE_MESSAGES["api_error"]) \
                .ask(RESPONSE_MESSAGES["help_text"]) \
                .response
        
        # Format response
        speech_text = ResponseFormatter.format_something(data)
        
        # Save session state
        handler_input.attributes_manager.session_attributes = session_state.to_dict()
        
        # Return response
        return handler_input.response_builder \
            .speak(speech_text) \
            .ask(reprompt_text) \
            .response
```

## Setup Flow Diagram

```
Launch Request
    ↓
LaunchRequest Handler
    ├─→ Check: is setup complete?
    ├─→ Yes: Ask what to do
    └─→ No: Welcome message
    
User: "Parent"
    ↓
UserTypeIntent Handler
    ├─→ Set: user_type = "parent"
    ├─→ Set: setup_step = "awaiting_permission_code"
    └─→ Ask: What's your permission code?

User: "123456"
    ↓
PermissionCodeIntent Handler
    ├─→ Validate: 6 digits? Yes
    ├─→ Set: permission_code = "123456"
    ├─→ Set: selected_child = {permission_code: "123456", ...}
    ├─→ Is parent? Yes
    ├─→ Set: setup_step = "awaiting_pin"
    └─→ Ask: Set up your 4-digit PIN

User: "1234"
    ↓
PINSetupIntent Handler
    ├─→ Validate: 4 digits? Yes
    ├─→ Set: pin = "1234"
    ├─→ Set: setup_step = "complete"
    └─→ Say: Setup complete! Ready to use.

Next request uses cached session state
    ↓
Activity intent (e.g., ListActivitiesIntent)
    ├─→ Check: setup_complete? Yes
    ├─→ Call: api_client.get_activities_for_youth("123456")
    ├─→ Format: ResponseFormatter.format_activity_list()
    └─→ Speak: "You have 3 activities..."
```

## Activity Query Flow Diagram

```
User: "What activities do I have?"
    ↓
ListActivitiesIntent Handler
    ├─→ Get: permission_code from session
    ├─→ Call: api_client.get_activities_for_youth(permission_code)
    ├─→ Cache: session_state.recent_activities = activities
    ├─→ Format: ResponseFormatter.format_activity_list(activities, max=3)
    └─→ Speak: "You have X activities: 1) Soccer on Dec 15..."

User: "Tell me about the soccer game"
    ↓
ActivityDetailsIntent Handler
    ├─→ Parse: activity_name = "soccer"
    ├─→ Find: Search recent_activities for "soccer"
    ├─→ Get: activity object
    ├─→ Format: ResponseFormatter.format_activity_details(activity)
    └─→ Speak: "Soccer Practice is on Dec 15 at 2 PM in Central Park..."

User: "Approve it"
    ↓
GrantPermissionIntent Handler
    ├─→ Verify: Is parent? Yes
    ├─→ Find: activity from recent_activities
    ├─→ Ask: Enter your PIN
    
User: "1234"
    ├─→ Verify: pin == session_state.pin? Yes
    ├─→ Call: api_client.grant_permission(youth_id, activity_id, permission_code)
    └─→ Speak: "Permission granted for Soccer Practice"
```

## Environment Variables

```
API_URL=http://api-youth.lthome.us         # Backend API
API_TIMEOUT=10                             # Seconds
ALEXA_SKILL_ID=amzn1.ask.skill...          # From ASK Console
ENVIRONMENT=development|production         # Log level
DEBUG=true|false                           # Enable debug logging
```

## Common Commands

### Setup & Installation
```bash
cd alexa/
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Testing
```bash
# Unit tests
python -m pytest test_skill.py -v

# With coverage
python -m pytest test_skill.py --cov=. --cov-report=html

# Syntax check
python -m py_compile lambda_function.py
```

### Deployment
```bash
# ASK CLI
ask deploy

# Manual: Create ZIP
zip -r alexa-skill.zip lambda_function.py utils/ models/ api/ intents/ requirements.txt
```

### Local Testing
```bash
# Run local test script
python test_local.py

# Debug mode
DEBUG=true python lambda_function.py
```

## Debugging Tips

### Print Debugging
```python
logger.debug(f"Session: {session_state.to_dict()}")
logger.info(f"Activities: {activities}")
logger.error(f"API Error: {error}")
```

### View CloudWatch Logs
```bash
# Real-time
aws logs tail /aws/lambda/ask-custom-skill --follow

# Or in AWS Console
CloudWatch → Log Groups → /aws/lambda/ask-custom-skill
```

### Test API Directly
```bash
# Test endpoint
curl "http://api-youth.lthome.us/activities-all-parents?permission_code=123456"

# Test with JSON
curl -X POST http://api-youth.lthome.us/activity-permissions \
  -H "Content-Type: application/json" \
  -d '{"youth_id":"1","activity_id":"1","permission_code":"123456"}'
```

## Slots Reference

| Slot | Purpose | Example |
|------|---------|---------|
| `user_type` | Parent or Youth | "parent", "youth", "kid" |
| `permission_code` | 6-digit code | "123456" |
| `pin` | 4-digit PIN | "1234" |
| `activity_name` | Activity name | "soccer", "campout" |
| `activity_number` | Activity list index | "1", "2", "3" |

## Response Phrase Samples

```
# Greeting
"Welcome to Youth Permission Tracker. Are you a parent or a youth?"

# Activity List
"You have 3 upcoming activities. Here are the first few: 1) Soccer on December 15, 2) Pizza Night on December 18, 3) Hiking on December 22."

# Activity Details
"Soccer Practice is on December 15 at 2 PM in Central Park. Come join us for soccer! The cost is five dollars."

# Permission Check
"You have 2 activities that need your permission approval: 1) Overnight Campout on December 22-23, 2) Water Rafting on January 5. Which would you like to approve?"

# Permission Grant
"To approve Overnight Campout, please provide your 4-digit PIN."
"Permission granted for Overnight Campout!"

# Error
"That code isn't recognized. Please check and try again."
"I wasn't able to verify your PIN. Please try again."
"The service is temporarily unavailable. Please try again in a moment."
```

## Skill Invocation Examples

```
"Alexa, open Youth Permission Tracker"
"Alexa, ask Youth Permission Tracker to list activities"
"Alexa, tell Youth Permission Tracker what's next"
"Alexa, ask Youth Permission Tracker to approve the campout"
```

---

**Note**: For more detailed information, see:
- `README.md` - Feature overview
- `DEPLOYMENT_GUIDE.md` - Deployment steps
- `DEVELOPMENT_GUIDE.md` - Local development
- `ARCHITECTURE.md` - Technical deep dive
