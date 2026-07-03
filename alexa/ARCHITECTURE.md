# Youth Permission Tracker Alexa Skill - Implementation Summary

## Overview

✅ **Complete modular Alexa skill** for managing youth group activities and parental permissions through voice.

### Key Capabilities

**For Parents & Youth:**
- 📋 **List Activities** - Get all upcoming activities with dates
- ⏭️ **Find Next Activity** - Instantly find your next event
- ℹ️ **Activity Details** - Full information (time, location, description, cost, overnight/coed status)

**For Parents Only:**
- ✅ **Check Permissions** - List activities requiring approval
- 🔐 **Grant Permission** - Approve with PIN verification for security

---

## Project Structure

```
alexa/
├── lambda_function.py              # Main Alexa skill entry point + all intent handlers
├── requirements.txt                # Dependencies (ask-sdk, requests, python-dotenv)
├── .env.example                    # Configuration template
├── .gitignore                      # Git ignore file
├── skill.json                      # Skill metadata for ASK
├── interaction_model.json          # Voice intents and utterances
│
├── api/
│   ├── __init__.py
│   ├── client.py                   # API client (5 endpoints: get_activities, get_details, grant_permission, etc.)
│   └── auth.py                     # Hybrid authentication (permission codes + PIN)
│
├── models/
│   ├── __init__.py
│   └── session.py                  # Session state management (user type, PIN, selected child, auth tokens)
│
├── intents/
│   ├── __init__.py
│   ├── list_activities.py          # ListActivitiesIntent (modular, not used by lambda_function)
│   ├── next_activity.py            # NextActivityIntent (modular reference)
│   ├── activity_details.py         # ActivityDetailsIntent (modular reference)
│   ├── permission_check.py         # ActivitiesNeedingPermissionIntent (modular reference)
│   ├── grant_permission.py         # GrantPermissionIntent (modular reference)
│   └── session_management.py       # Session management (modular reference)
│
├── utils/
│   ├── __init__.py
│   ├── constants.py                # API URLs, response messages, configuration
│   └── response_formatter.py       # Natural language formatting (dates, times, costs, activity lists)
│
├── test_skill.py                   # Comprehensive unit tests (API, auth, formatting, session state)
│
├── README.md                       # Feature overview, setup, testing, troubleshooting
├── DEPLOYMENT_GUIDE.md             # Step-by-step AWS Lambda deployment (both ASK CLI and manual)
├── DEVELOPMENT_GUIDE.md            # Local development, testing, debugging
└── ARCHITECTURE.md                 # (This file) Complete technical summary
```

---

## Architecture

### Handler Flow

```
Alexa Request
    ↓
Lambda Entry Point (lambda_function.lambda_handler)
    ↓
ASK Skill Builder Routes to Intent Handler
    ↓
Intent Handler (e.g., ListActivitiesIntentHandler)
    ├─→ Authenticate: Verify session state
    ├─→ Call API: api_client.get_activities_for_youth()
    ├─→ Format Response: ResponseFormatter.format_activity_list()
    └─→ Return Voice Response
    ↓
Alexa Speaks Response & Saves Session
```

### Component Details

#### 1. **API Client** (`api/client.py`)

Methods for backend communication:
- `get_all_activities(include_past, org_group)` → All activities
- `get_activity_details(activity_id)` → Full activity info
- `get_activities_for_youth(permission_code)` → Activities for a youth
- `get_activities_needing_permission(permission_code)` → Permission-required activities
- `grant_permission(youth_id, activity_id, permission_code)` → Record permission grant

All methods return: `(success: bool, data: Any, error: str)`

#### 2. **Authentication Manager** (`api/auth.py`)

**HybridAuthManager** supports two auth methods:

**Primary (MVP):**
- Permission code (6-digit numeric code)
- Parent provides code to access child's activities
- Youth provides code to view own activities

**Future Upgrade Path:**
- Username/password → JWT tokens
- Enable admin/leadership features

#### 3. **Session State** (`models/session.py`)

`SessionState` dataclass stores:
- `user_type`: "parent" or "youth"
- `permission_code`: 6-digit code
- `pin`: 4-digit PIN (parents only)
- `selected_child`: Child info for parents managing multiple children
- `setup_step`: Progress through setup flow
- `recent_activities`: Cached activity list from last query

Converts to/from Alexa session attributes automatically.

#### 4. **Intent Handlers** (in `lambda_function.py`)

All handlers check session state and call appropriate APIs:

| Intent | Slots | Action |
|--------|-------|--------|
| `UserTypeIntent` | `user_type` | Parent/Youth selection |
| `PermissionCodeIntent` | `permission_code` | Enter 6-digit code |
| `PINSetupIntent` | `pin` | Set 4-digit PIN |
| `ListActivitiesIntent` | None | Get all activities |
| `NextActivityIntent` | None | Get next activity |
| `ActivityDetailsIntent` | `activity_name`, `activity_number` | Get activity details |
| `ActivitiesNeedingPermissionIntent` | None | List permissions needed (parent only) |
| `GrantPermissionIntent` | `activity_name`, `activity_number`, `pin` | Grant permission (parent only) |

#### 5. **Response Formatter** (`utils/response_formatter.py`)

Converts API data to natural voice language:
- Dates: "2026-12-15" → "December 15th"
- Times: "14:30" → "2:30 PM"
- Costs: `5.5` → "five dollars and fifty cents"
- Lists: Limits to 3-5 items, formats with numbers
- Activity details: Combines all fields into conversational text

#### 6. **Constants** (`utils/constants.py`)

Configuration and response messages:
- `API_URL`: Backend API base URL
- `RESPONSE_MESSAGES`: All voice prompts and responses
- `INTENTS`, `SLOTS`: Intent/slot definitions
- `API_ENDPOINTS`: Endpoint paths
- `SESSION_KEYS`: Session attribute names

---

## Authentication Flow

### Initial Setup (Parent)

```
User: "Alexa, open Youth Permission Tracker"
       ↓ Launch Request
Alexa: "Are you a parent or a youth?"
User: "Parent"
       ↓ UserTypeIntent
Alexa: "I'm set up for parent mode. What's your 6-digit permission code?"
User: "123456"
       ↓ PermissionCodeIntent (validates code format)
Alexa: "What 4-digit PIN would you like to use?"
User: "1234"
       ↓ PINSetupIntent
Alexa: "Your PIN is set. You're ready to use the skill!"
       ↓ setup_step = "complete"
       ↓ Session persists: {user_type, permission_code, pin, selected_child}
```

### Initial Setup (Youth)

```
Same as parent, but:
- Skip PIN setup (not needed for youth)
- setup_step = "complete" after permission code
```

### Subsequent Sessions

Session attributes restored from Alexa:
- User already authenticated
- Direct access to all intents

---

## API Integration

### Endpoints Used

| Endpoint | Method | Purpose | Query Params |
|----------|--------|---------|--------------|
| `/activities-all` | GET | All activities | `include_past`, `org_group` |
| `/activities/{id}` | GET | Activity details | None |
| `/activities-all-parents` | GET | Activities for youth | `permission_code` |
| `/activity-permissions` | POST | Grant permission | None (JSON body) |
| `/activities-pending-approval` | GET | Approval-needed activities | `org_group` |

### Error Handling

All API calls wrapped with error handling:
- Timeout errors (>10 seconds)
- Connection errors
- Invalid HTTP status codes
- JSON parsing errors

Returns meaningful error messages for voice:
- "The service is temporarily unavailable"
- "I'm having trouble connecting to the service"
- "That code isn't recognized"

---

## Session State Persistence

### Stored in Alexa Session Attributes

```json
{
  "user_type": "parent",
  "permission_code": "123456",
  "pin": "1234",
  "setup_step": "complete",
  "selected_child": {
    "child_id": "youth_1",
    "child_name": "Emma",
    "org_group": "young women",
    "permission_code": "123456"
  },
  "recent_activities": [
    {"activity_id": "1", "name": "Soccer", "date": "2026-12-15"}
  ]
}
```

### Session Lifecycle

- Created on first request (LaunchRequest)
- Persisted across turns in same session
- Cleared when user exits skill or session expires (24 hours)
- User must re-authenticate for new sessions

---

## Voice Response Examples

### Setup Flow
```
Alexa: "Welcome to Youth Permission Tracker. Are you a parent or a youth?"
User: "Parent"
Alexa: "Great! I'm set up for parent mode. To get started, I'll need your 6-digit permission code."
User: "123456"
Alexa: "Now let's set up a 4-digit PIN to verify permission grants. What PIN would you like to use?"
User: "1234"
Alexa: "Your PIN is set. You're all set to use the skill. I can help you..."
```

### Activity Query
```
User: "What activities do I have?"
Alexa: "You have 3 upcoming activities. Here are the first few: 1) Soccer Practice on December 15th, 2) Pizza Night on December 18th, 3) Hiking Trip on December 22nd. Would you like details about any of these?"

User: "Tell me about the hiking trip"
Alexa: "Hiking Trip is on December 22nd at 9 AM in Red Rock Canyon. It's a day activity, not coed. Join us for an amazing outdoor adventure! The cost is five dollars."

User: "What's next?"
Alexa: "Your next activity is Soccer Practice on December 15th at 2 PM in Central Park."
```

### Permission Grant
```
User: "Do I need to approve anything?"
Alexa: "You have 2 activities that need your permission approval: 1) Overnight Campout on December 22-23, 2) Water Rafting on January 5th. Which activity would you like to approve?"

User: "Approve the campout"
Alexa: "To approve Overnight Campout, please provide your 4-digit PIN."

User: "1234"
Alexa: "Permission granted for Overnight Campout. Is there anything else I can help you with?"
```

---

## Testing

### Unit Tests (`test_skill.py`)

Comprehensive tests for:
- **API Client**: HTTP requests, error handling, response parsing
- **Auth Manager**: Permission code validation, token expiry
- **Response Formatter**: Date/time formatting, activity list creation
- **Session State**: Serialization/deserialization, state transitions
- **Integration**: End-to-end permission grant flow

Run tests:
```bash
cd alexa/
python -m pytest test_skill.py -v
python -m pytest test_skill.py --cov=. --cov-report=html
```

### Local Development Testing

Use `DEVELOPMENT_GUIDE.md` for:
- Manual testing with mock requests
- Local debugging with IDE
- Performance profiling
- CI/CD setup with GitHub Actions

### Alexa Simulator Testing

1. Deploy to Lambda (see DEPLOYMENT_GUIDE.md)
2. Enable testing in ASK Developer Console
3. Type or speak test utterances
4. View responses and CloudWatch logs

---

## Deployment

### Quick Start

**Option 1: ASK CLI (Recommended)**
```bash
npm install -g ask-cli
ask init
ask deploy
```

**Option 2: Manual AWS Lambda**
```bash
zip -r skill.zip lambda_function.py utils/ models/ api/ intents/ requirements.txt
# Upload to Lambda via console
# Set handler: lambda_function.lambda_handler
# Add environment variables from .env
```

See `DEPLOYMENT_GUIDE.md` for detailed instructions.

### Environment Variables

```
API_URL=http://api-youth.lthome.us
API_TIMEOUT=10
ALEXA_SKILL_ID=amzn1.ask.skill.XXXXXXXX
ENVIRONMENT=development
DEBUG=false
```

### Lambda Configuration

- Runtime: Python 3.9+
- Handler: `lambda_function.lambda_handler`
- Timeout: 30 seconds (accommodates API latency)
- Memory: 256 MB (default is sufficient)

---

## Performance Considerations

### Response Times

- **Setup flow**: 1-2 seconds (permission code validation)
- **Activity query**: 2-5 seconds (API call + formatting)
- **Permission grant**: 3-6 seconds (API call + verification)
- **Timeout**: 30 seconds (Lambda limit, Alexa expects <10 seconds ideal)

### Optimization Opportunities

- Cache activity list in session (recent_activities)
- Implement activity pagination with "more" intent
- Pre-format dates during API response handling
- Use Lambda Layers for dependencies

### Costs

- **AWS Lambda**: Free tier 1M requests/month
- **CloudWatch**: Minimal logging costs
- **Typical usage**: <$1/month for small deployment

---

## Security Considerations

### Current Implementation (MVP)

- Permission codes stored in session (temporary only)
- PINs stored in session (unencrypted, for MVP)
- No HTTPS enforcement in code (provided by AWS/Alexa)
- No rate limiting (rely on Alexa request throttling)

### Production Recommendations

- Hash PINs before storing in session
- Implement rate limiting (failed PIN attempts)
- Add audit logging (all permission grants)
- Use CORS validation on API
- Encrypt session attributes in transit
- Implement account linking with OAuth2 (future)

---

## Known Limitations & Future Work

### MVP Limitations

1. **Single Child Only** - Parents can't select between children
   - Future: `ChildSelectionIntent` with multi-child menu

2. **No SMS Confirmations** - Permission grants not sent via SMS
   - Future: Integrate Twilio SMS notifications

3. **No Admin Features** - Can't check attendance, view health info
   - Future: Admin-only intents with role-based access

4. **No Historical Data** - Can't view past activities or grants
   - Feature: `PastActivitiesIntent`, `PermissionHistoryIntent`

5. **Limited Filtering** - No advanced search or filters
   - Future: Filter by activity type, cost, group, date range

### Planned Enhancements

- Interest survey intent (youth voice feedback)
- Personal goals tracking (youth goals + progress)
- Calendar export (`.ics` file generation)
- QR code generation (activity links)
- Multi-language support (Spanish, etc.)
- Alexa Skill Monetization (in-app purchases)

---

## Troubleshooting Quick Guide

| Issue | Solution |
|-------|----------|
| "Skill not responding" | Check Lambda CloudWatch logs, verify internet access |
| "Permission code not recognized" | Verify format (6 digits), check API database |
| "API timeout" | Increase Lambda timeout to 30s, check API health |
| "PIN verification fails" | Ensure PIN is 4 digits, check session state saved |
| "Activities not showing" | Verify youth in participants_youth_ids, check org_group filtering |
| "No module named ask_sdk" | Run `pip install -r requirements.txt` |

See `README.md` for detailed troubleshooting.

---

## Development Workflow

1. **Local Testing**: Use `test_local.py` to test intents
2. **Unit Tests**: Run `pytest test_skill.py`
3. **Manual Deployment**: `ask deploy` or manual Lambda upload
4. **Alexa Simulator**: Test in ASK Developer Console
5. **Device Testing**: Test on actual Alexa device
6. **Iterate**: Fix issues, re-deploy, repeat

---

## Files & Responsibilities

### Core Files

- **lambda_function.py** - All intent handlers, request routing
- **api/client.py** - API communication, 5 main methods
- **api/auth.py** - Hybrid authentication logic
- **models/session.py** - Session state management
- **utils/response_formatter.py** - Voice response formatting
- **utils/constants.py** - Configuration, messages, endpoints

### Modular Intent Files (Reference Structure)

These are kept for reference but logic is in `lambda_function.py`:
- **intents/list_activities.py**
- **intents/next_activity.py**
- **intents/activity_details.py**
- **intents/permission_check.py**
- **intents/grant_permission.py**
- **intents/session_management.py**

### Documentation

- **README.md** - User guide, setup, features
- **DEPLOYMENT_GUIDE.md** - AWS Lambda deployment
- **DEVELOPMENT_GUIDE.md** - Local development
- **.env.example** - Configuration template

### Testing

- **test_skill.py** - Comprehensive unit tests
- **DEVELOPMENT_GUIDE.md** - Local test scripts

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Lines of Code (excluding tests) | ~1,500 |
| Intent Handlers | 8 |
| API Endpoints | 5 |
| Voice Response Formats | 20+ |
| Unit Test Cases | 20+ |
| Configuration Parameters | 15 |
| Session Attributes | 9 |

---

## Getting Started

1. **Review** `README.md` for feature overview
2. **Setup** Python environment and dependencies
3. **Test Locally** using `DEVELOPMENT_GUIDE.md`
4. **Deploy** to Lambda using `DEPLOYMENT_GUIDE.md`
5. **Test** with Alexa Simulator and devices
6. **Iterate** based on feedback

---

## Support & Questions

For issues or questions:
1. Check CloudWatch logs: `/aws/lambda/ask-custom-skill`
2. Review troubleshooting in `README.md`
3. Test API endpoints directly
4. Review code comments and docstrings
5. Check ASK Developer Forum

---

**Status**: ✅ **Complete MVP Implementation** - Ready for deployment and testing.

**Next Steps**: Deploy to AWS Lambda and test with actual Alexa devices.
