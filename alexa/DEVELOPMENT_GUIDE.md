# Local Development Guide

This guide explains how to develop and test the Alexa skill locally without needing to deploy to AWS.

## Setup

### 1. Install Dependencies

```bash
cd alexa/

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Also install testing and development tools
pip install pytest pytest-cov pytest-mock
```

### 2. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env with your settings
# Important: Make sure API_URL points to your local or test API
```

## Local Testing

### Unit Tests

Run all tests:
```bash
python -m pytest test_skill.py -v
```

Run specific test:
```bash
python -m pytest test_skill.py::TestAPIClient::test_get_all_activities_success -v
```

With coverage:
```bash
python -m pytest test_skill.py --cov=. --cov-report=html
```

### Manual Testing with Mock Alexa

Create a test script `test_local.py`:

```python
#!/usr/bin/env python3
"""
Local testing script to simulate Alexa skill interactions
"""

import json
from unittest.mock import Mock, patch
from lambda_function import lambda_handler
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput


def create_alexa_request(intent_name, slots=None, session_attrs=None):
    """Create a mock Alexa request"""
    return {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "test-session-id",
            "attributes": session_attrs or {},
            "user": {
                "userId": "test-user-id"
            }
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "test-request-id",
            "locale": "en-US",
            "timestamp": "2024-01-15T10:00:00Z",
            "intent": {
                "name": intent_name,
                "slots": {
                    slot_name: {"name": slot_name, "value": slot_value}
                    for slot_name, slot_value in (slots or {}).items()
                }
            }
        },
        "context": {
            "System": {
                "application": {
                    "applicationId": "amzn1.ask.skill.test"
                }
            }
        }
    }


def test_launch_request():
    """Test launching the skill"""
    request = {
        "version": "1.0",
        "session": {
            "new": True,
            "attributes": {}
        },
        "request": {
            "type": "LaunchRequest",
            "requestId": "test",
            "locale": "en-US",
            "timestamp": "2024-01-15T10:00:00Z"
        },
        "context": {"System": {"application": {"applicationId": "test"}}}
    }
    
    response = lambda_handler(request, None)
    print("Launch Response:")
    print(json.dumps(response, indent=2))
    assert response["statusCode"] == 200


def test_setup_flow():
    """Test user setup flow"""
    print("\n=== Testing Setup Flow ===\n")
    
    # Step 1: User type
    print("Step 1: Select user type (parent)")
    request = create_alexa_request("UserTypeIntent", {"user_type": "parent"})
    response = lambda_handler(request, None)
    print(f"Response: {response['body']['response']['outputSpeech']['text']}")
    
    # Extract session attributes for next request
    session_attrs = response.get("sessionAttributes", {})
    
    # Step 2: Permission code
    print("\nStep 2: Enter permission code")
    request = create_alexa_request("PermissionCodeIntent", 
                                   {"permission_code": "123456"},
                                   session_attrs)
    response = lambda_handler(request, None)
    print(f"Response: {response['body']['response']['outputSpeech']['text']}")
    
    session_attrs = response.get("sessionAttributes", {})
    
    # Step 3: PIN setup
    print("\nStep 3: Set PIN")
    request = create_alexa_request("PINSetupIntent",
                                   {"pin": "1234"},
                                   session_attrs)
    response = lambda_handler(request, None)
    print(f"Response: {response['body']['response']['outputSpeech']['text']}")


@patch('api.client.APIClient.get_activities_for_youth')
def test_list_activities(mock_api):
    """Test listing activities"""
    print("\n=== Testing List Activities ===\n")
    
    # Mock API response
    mock_api.return_value = (True, [
        {
            "activity_id": "1",
            "name": "Soccer Practice",
            "date": "2026-12-15",
            "requires_permission": False
        },
        {
            "activity_id": "2",
            "name": "Pizza Night",
            "date": "2026-12-18",
            "requires_permission": False
        }
    ], None)
    
    session_attrs = {
        "user_type": "parent",
        "permission_code": "123456",
        "selected_child": {
            "child_id": "1",
            "child_name": "Emma",
            "org_group": "youth",
            "permission_code": "123456"
        },
        "setup_step": "complete"
    }
    
    request = create_alexa_request("ListActivitiesIntent", {}, session_attrs)
    response = lambda_handler(request, None)
    
    print(f"Response: {response['body']['response']['outputSpeech']['text']}")
    mock_api.assert_called_once()


def test_response_formatter():
    """Test response formatting"""
    print("\n=== Testing Response Formatter ===\n")
    
    from utils.response_formatter import ResponseFormatter
    
    # Test date formatting
    date_str = "2026-12-15"
    formatted_date = ResponseFormatter.format_date(date_str)
    print(f"Formatted date: '{date_str}' → '{formatted_date}'")
    
    # Test time formatting
    time_str = "14:30"
    formatted_time = ResponseFormatter.format_time(time_str)
    print(f"Formatted time: '{time_str}' → '{formatted_time}'")
    
    # Test cost formatting
    formatted_cost = ResponseFormatter.format_cost(5.50)
    print(f"Formatted cost: 5.50 → '{formatted_cost}'")
    
    # Test activity list
    activities = [
        {"name": "Activity 1", "date": "2026-12-15"},
        {"name": "Activity 2", "date": "2026-12-18"},
    ]
    formatted_list = ResponseFormatter.format_activity_list(activities)
    print(f"Activity list:\n{formatted_list}")


def test_session_state():
    """Test session state management"""
    print("\n=== Testing Session State ===\n")
    
    from models.session import SessionState, ChildInfo
    
    # Create state
    child = ChildInfo(
        child_id="1",
        child_name="Emma",
        org_group="youth",
        permission_code="123456"
    )
    
    state = SessionState(
        user_type="parent",
        permission_code="123456",
        selected_child=child,
        setup_step="complete",
        pin="1234"
    )
    
    print(f"User type: {state.user_type}")
    print(f"Is parent: {state.is_parent()}")
    print(f"Setup complete: {state.is_setup_complete()}")
    print(f"Child name: {state.selected_child.child_name}")
    
    # Serialize and deserialize
    state_dict = state.to_dict()
    restored_state = SessionState.from_dict(state_dict)
    
    print(f"\nSerialization test:")
    print(f"Original: {state_dict['user_type']}")
    print(f"Restored: {restored_state.user_type}")
    assert state.user_type == restored_state.user_type


if __name__ == "__main__":
    print("Starting local skill tests...\n")
    
    try:
        test_launch_request()
        test_setup_flow()
        test_response_formatter()
        test_session_state()
        
        print("\n✓ All local tests passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
```

Run it:
```bash
python test_local.py
```

### Debug Logging

Set `DEBUG=true` in `.env` to enable detailed logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In your code:
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.error("This is an error message")
```

## Development Workflow

### 1. Make Code Changes

Edit files in the `alexa/` directory:
```bash
# Example: Fix response formatter
vim utils/response_formatter.py
```

### 2. Run Tests

```bash
# Run all tests
pytest test_skill.py -v

# Or specific module
pytest test_skill.py::TestResponseFormatter -v
```

### 3. Test Locally

```bash
# Run manual test script
python test_local.py

# Or test specific flow
python -c "from test_local import test_list_activities; test_list_activities()"
```

### 4. Commit and Deploy

```bash
# Commit changes
git add .
git commit -m "Fix response formatting for costs"

# Deploy to Lambda
ask deploy
# Or manual: zip and upload
```

## Tips

### Mock API Responses

```python
from unittest.mock import patch

@patch('api.client.APIClient.get_activities_for_youth')
def test_with_mock(mock_api):
    mock_api.return_value = (True, [
        {"activity_id": "1", "name": "Test Activity", "date": "2026-12-15"}
    ], None)
    
    # Your test code
    assert mock_api.called
```

### Test Auth Manager

```python
from api.auth import HybridAuthManager

auth = HybridAuthManager("http://api-youth.lthome.us")

# Test permission code validation
is_valid, info, error = auth.validate_permission_code("123456")
print(f"Valid: {is_valid}, Error: {error}")

# Test token validation
is_valid = auth.is_token_valid("token_string", "2024-01-15T10:00:00")
print(f"Token valid: {is_valid}")
```

### Simulate Session State Changes

```python
from models.session import SessionState, ChildInfo

# Initialize
state = SessionState()
state.user_type = "parent"
state.setup_step = "awaiting_permission_code"

# Convert for Alexa
state_dict = state.to_dict()

# Later request restores state
restored = SessionState.from_dict(state_dict)
assert restored.user_type == "parent"
```

## Debugging

### Print Statement Debugging

```python
# In lambda_function.py or any handler
logger.debug(f"Session state: {session_state.to_dict()}")
logger.debug(f"API response: {activities}")
```

View in CloudWatch logs after deployment.

### Local Debugging with IDE

Use VSCode or PyCharm debugger:

```python
# Set breakpoint in test_local.py
import pdb; pdb.set_trace()

# Run test
python test_local.py
# Stops at breakpoint, use commands: c (continue), n (next), s (step), p (print)
```

## Performance Testing

```bash
# Time how long requests take
time python test_local.py

# Profile with cProfile
python -m cProfile -s cumulative test_local.py | head -20
```

## Continuous Integration

For GitHub Actions CI/CD:

Create `.github/workflows/test.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r alexa/requirements.txt pytest
      - run: cd alexa && pytest test_skill.py -v
```

## Next Steps

1. Complete local testing
2. Deploy to AWS Lambda (see DEPLOYMENT_GUIDE.md)
3. Test with actual Alexa device or simulator
4. Iterate based on feedback
