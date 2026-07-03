# Youth Permission Tracker - Alexa Skill

A voice-first Alexa skill that enables parents and youth to manage youth group activities, check permissions, and grant parental approval through voice commands.

## Features

### For Parents & Youth
- **List Activities** - "Alexa, list my activities" - Get all upcoming activities for your child(ren)
- **Find Next Activity** - "Alexa, what's next?" - Quickly find your immediately next activity with date, time, and location
- **Activity Details** - "Alexa, tell me about [activity name]" - Get comprehensive details including description, time, location, and cost

### For Parents Only
- **Check Permissions** - "Alexa, do I need to approve anything?" - List activities that require parental permission
- **Grant Permission** - "Alexa, approve [activity name]" - Grant permission with PIN verification for security

## Architecture

```
alexa/
├── lambda_function.py          # Main Alexa skill entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Configuration template
├── api/
│   ├── client.py               # API client for backend communication
│   └── auth.py                 # Authentication management (hybrid auth)
├── models/
│   └── session.py              # Session state management
├── intents/
│   ├── list_activities.py       # ListActivitiesIntent
│   ├── next_activity.py         # NextActivityIntent
│   ├── activity_details.py      # ActivityDetailsIntent
│   ├── permission_check.py      # ActivitiesNeedingPermissionIntent
│   ├── grant_permission.py      # GrantPermissionIntent
│   └── session_management.py    # Setup and auth intents
└── utils/
    ├── constants.py             # API URLs, messages, configuration
    └── response_formatter.py     # Formats API responses for voice
```

## Authentication

The skill uses a hybrid authentication approach:

1. **Permission Code (Primary)** - 6-digit code provided by parents/youth to access their activities
   - Used for parents to view their children's activities and grant permissions
   - Used for youth to view their own activities
   
2. **PIN Verification** - 4-digit PIN set up by parents during initial setup
   - Required before granting permission to any activity
   - Ensures only the parent can approve activities

3. **Future Upgrade Path** - Support for username/password authentication
   - Enables full admin/leadership features
   - Optional upgrade from permission code auth

## Setup & Installation

### Prerequisites
- Python 3.9+
- AWS Lambda (or local testing)
- Alexa Developer Console access
- Access to http://api-youth.lthome.us API

### Local Development Setup

1. **Clone/Navigate to the Alexa directory**
   ```bash
   cd alexa/
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration:
   # - API_URL: http://api-youth.lthome.us
   # - ALEXA_SKILL_ID: (get from ASK Developer Console)
   # - ENVIRONMENT: development
   ```

### Deployment to AWS Lambda

1. **Install ASK CLI** (if not already installed)
   ```bash
   npm install -g ask-cli
   ```

2. **Initialize ASK project** (one time)
   ```bash
   ask init
   ```

3. **Deploy the skill**
   ```bash
   ask deploy
   ```

   This will:
   - Package the Python code and dependencies
   - Upload to AWS Lambda
   - Update the Alexa skill configuration
   - Make the skill available on Alexa devices

### Manual Lambda Upload

If using ASK CLI manually:

1. **Create deployment package**
   ```bash
   # Create a zip with lambda_function.py and all modules
   zip -r alexa-skill.zip lambda_function.py utils/ models/ api/ requirements.txt
   pip install -r requirements.txt -t .
   zip -r alexa-skill.zip .
   ```

2. **Upload to Lambda**
   - Go to AWS Lambda console
   - Create new function (Python 3.9+)
   - Upload ZIP file
   - Set handler to: `lambda_function.lambda_handler`
   - Add environment variables (from .env)

3. **Link to Alexa Skill**
   - In ASK Developer Console, add Lambda ARN as the endpoint

## Testing

### Via Alexa Simulator

1. In ASK Developer Console, go to "Test" tab
2. Enable testing for development
3. Use the Alexa Simulator to test utterances

### Example Test Flows

**Parent Setup Flow:**
```
User: Alexa, open Youth Permission Tracker
Alexa: Welcome to Youth Permission Tracker. Are you a parent or a youth?

User: Parent
Alexa: Great! I'm set up for parent mode. To get started, I'll need your 6-digit permission code.

User: 123456
Alexa: Now let's set up a 4-digit PIN to verify permission grants. What PIN would you like to use?

User: 1234
Alexa: Your PIN is set. You're all set to use the skill. I can help you manage activities and permissions...
```

**Activity Query Flow:**
```
User: What activities do I have?
Alexa: You have 3 upcoming activities. Here are the first few: 1) Soccer Practice on December 15th, 2) Pizza Night on December 18th, 3) Hiking Trip on December 22nd. Would you like details about any of these?

User: Tell me about the hiking trip
Alexa: Hiking Trip is on December 22nd at 9 AM in Red Rock Canyon. It's a day activity, not coed. Join us for an amazing outdoor adventure...

User: What's next?
Alexa: Your next activity is Soccer Practice on December 15th at 2 PM in Central Park.
```

**Permission Grant Flow:**
```
User: Do I need to approve anything?
Alexa: You have 2 activities that need your permission approval: 1) Overnight Campout on December 22-23, 2) Water Rafting on January 5th. Which activity would you like to approve?

User: Approve the campout
Alexa: To approve Overnight Campout, please provide your 4-digit PIN.

User: 1234
Alexa: Permission granted for Overnight Campout. Is there anything else I can help you with?
```

## Interaction Model

The skill supports the following intents and slots:

### Intents

| Intent | Slots | Purpose |
|--------|-------|---------|
| `ListActivitiesIntent` | None | Get all upcoming activities |
| `NextActivityIntent` | None | Get the next activity |
| `ActivityDetailsIntent` | `activity_name`, `activity_number` | Get details about a specific activity |
| `ActivitiesNeedingPermissionIntent` | None | (Parent) List activities needing approval |
| `GrantPermissionIntent` | `activity_name`, `activity_number`, `pin` | (Parent) Grant permission for activity |
| `UserTypeIntent` | `user_type` | During setup: parent or youth |
| `PermissionCodeIntent` | `permission_code` | During setup: enter 6-digit code |
| `PINSetupIntent` | `pin` | During parent setup: set 4-digit PIN |
| `AMAZON.HelpIntent` | None | Built-in: Help |
| `AMAZON.StopIntent` | None | Built-in: Stop/Exit |
| `AMAZON.CancelIntent` | None | Built-in: Cancel |
| `AMAZON.FallbackIntent` | None | Built-in: Unrecognized request |

### Sample Utterances

```
# ListActivitiesIntent
- list my activities
- what activities do I have
- show my activities
- what activities are coming up

# NextActivityIntent
- what's next
- what's my next activity
- when's the next activity
- what's coming up

# ActivityDetailsIntent
- tell me about {activity_name}
- details on number {activity_number}
- what's {activity_name}
- more details on {activity_name}

# ActivitiesNeedingPermissionIntent
- do I need to approve anything
- what needs my permission
- are there activities needing approval
- show me activities that need permission

# GrantPermissionIntent
- approve {activity_name}
- grant permission for number {activity_number}
- allow {activity_name}
- say yes to {activity_name}

# UserTypeIntent
- I'm a {user_type}
- I'm a {user_type} account

# PermissionCodeIntent
- my code is {permission_code}
- {permission_code}

# PINSetupIntent
- {pin}
- my PIN is {pin}
```

## Environment Variables

Create a `.env` file or set environment variables:

```
API_URL=http://api-youth.lthome.us      # Base URL for the backend API
API_TIMEOUT=10                           # Request timeout in seconds
ALEXA_SKILL_ID=amzn1.ask.skill.xxx       # Your Alexa Skill ID
ENVIRONMENT=development                  # development or production
DEBUG=true                               # Enable debug logging
```

## API Endpoints Used

The skill communicates with these API endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/token` | POST | Get JWT token (future use) |
| `/activities-all` | GET | Get all activities |
| `/activity-groups` | GET | Get activities for a group |
| `/activities/{activity_id}` | GET | Get activity details |
| `/activities-all-parents` | GET | Get activities for a youth (by permission code) |
| `/activity-permissions` | POST | Grant permission for an activity |
| `/activities-pending-approval` | GET | Get activities needing approval |
| `/activities/permission-info/{activity_id}` | GET | Get permission requirements |

## Session Management

Session attributes are stored in Alexa and persist during a single session:

- `user_type` - "parent" or "youth"
- `permission_code` - 6-digit code
- `pin` - 4-digit PIN (parents only)
- `selected_child` - Child info (parents only)
- `setup_step` - Current setup progress
- `recent_activities` - Cached activity list from last query

## Error Handling

The skill handles common errors gracefully:

- **Invalid Permission Code** - "That code isn't recognized. Please check and try again."
- **Invalid PIN** - "I wasn't able to verify your PIN. Please try again."
- **API Timeout** - "The service is taking too long to respond. Please try again."
- **Connection Error** - "I'm having trouble connecting to the service. Please try again in a moment."
- **No Activities** - "You don't have any upcoming activities scheduled."
- **Activity Not Found** - "I couldn't find that activity. Please try listing activities first."

## Logging

Debug logs are available in AWS CloudWatch:

```
# Via AWS Console
CloudWatch → Log Groups → /aws/lambda/ask-custom-[skill-id]

# Or via AWS CLI
aws logs tail /aws/lambda/ask-custom-[skill-id] --follow
```

## Architecture Notes

### Voice Response Optimization
- Activities are presented in natural language (e.g., "December 15th" not "2026-12-15")
- Lists limited to 3-5 items to avoid overwhelming users
- Long descriptions truncated for voice clarity
- Costs spoken naturally (e.g., "five dollars and fifty cents")

### Session State
- User state is stored in Alexa session (not persistent between sessions)
- Permission codes and PINs stored temporarily for session duration
- Recent activities cached to enable activity reference by number

### API Communication
- All API calls include error handling and timeouts
- Hybrid auth supports permission codes for MVP, upgrade path to JWT
- Response validation ensures data consistency

## Future Enhancements

- **SMS Confirmations** - Send permission confirmation via SMS
- **Multi-Child Support** - Full parent management of multiple children
- **Interest Survey** - Voice-based youth interest collection
- **Personal Goals** - Youth goal tracking and progress updates
- **Admin Features** - Admin can check activity attendance via voice
- **Calendar Export** - Generate .ics file for calendar integration
- **QR Code Generation** - Create QR codes for activity links
- **Production Deployment** - Automated ASK CLI deployment pipeline

## Troubleshooting

**Skill not responding:**
- Check CloudWatch logs for errors
- Verify Lambda has internet access and CORS allowed
- Confirm API_URL is accessible from Lambda

**Permission code not recognized:**
- Verify code format (must be 6 digits)
- Confirm code matches records in API database
- Check permission_code field in youth_medical table

**Activities not showing:**
- Verify youth_id is in participants_youth_ids for activity
- Check activity is not in the past (unless include_past=true)
- Confirm API is returning data (test directly)

**PIN verification failing:**
- Ensure PIN was set correctly during setup
- PIN must be exactly 4 digits
- Check session_state.pin is being saved

## Support

For issues or questions:
1. Check CloudWatch logs for detailed error messages
2. Test API endpoints directly: `curl http://api-youth.lthome.us/activities-all`
3. Verify environment variables are set correctly in Lambda
4. Review interaction model in ASK Developer Console

## License

MIT - See LICENSE file in parent directory
