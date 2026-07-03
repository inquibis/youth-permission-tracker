# Alexa Skill Deployment Guide

This guide walks through deploying the Youth Permission Tracker Alexa skill to AWS Lambda.

## Prerequisites

- AWS Account with Lambda access
- ASK CLI installed (`npm install -g ask-cli`)
- Python 3.9+ with pip
- Alexa Developer Console access (https://developer.amazon.com/alexa)
- Access to the Youth Permission Tracker API (http://api-youth.lthome.us)

## Option 1: Deploy via ASK CLI (Recommended)

### Step 1: Install ASK CLI

```bash
npm install -g ask-cli
ask --version
```

### Step 2: Configure ASK CLI

```bash
ask init
```

This will:
- Open a browser to authenticate with your Amazon account
- Create `.ask/config.json` with your credentials
- Store your profile

### Step 3: Initialize Skill Project Structure

Navigate to a parent directory and run:

```bash
ask create --url https://github.com/inquibis/youth-permission-tracker.git
```

Or manually set up the structure:

```
skill-project/
├── skill.json                  # Skill metadata
├── models/
│   └── en-US.json             # Interaction model
└── lambda/
    └── custom/
        ├── lambda_function.py
        ├── requirements.txt
        └── [all modules]
```

### Step 4: Update skill.json

Edit `skill.json` with your skill ID and Lambda ARN (after deployment):

```json
{
  "skillId": "amzn1.ask.skill.XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "apis": {
    "custom": {
      "endpoint": {
        "uri": "arn:aws:lambda:us-east-1:123456789:function:ask-custom-skill"
      }
    }
  }
}
```

### Step 5: Update Interaction Model

Copy the interaction model to `models/en-US.json`:

```bash
cp interaction_model.json models/en-US.json
```

### Step 6: Configure Lambda Environment

Create `lambda/custom/.env` with:

```
API_URL=http://api-youth.lthome.us
API_TIMEOUT=10
ALEXA_SKILL_ID=amzn1.ask.skill.XXXXXXXX
ENVIRONMENT=development
DEBUG=false
```

### Step 7: Deploy

```bash
ask deploy
```

This will:
1. Package Python code and dependencies
2. Create/update Lambda function
3. Update interaction model in Alexa
4. Test connectivity

Watch the output for:
- Lambda ARN
- Skill ID
- Region deployed to

---

## Option 2: Manual AWS Lambda Deployment

If not using ASK CLI, you can manually upload to Lambda.

### Step 1: Create Deployment Package

```bash
cd alexa/

# Create a temporary directory for the package
mkdir lambda-package
cd lambda-package

# Copy all files
cp ../lambda_function.py .
cp -r ../utils/ .
cp -r ../models/ .
cp -r ../api/ .
cp -r ../intents/ .

# Install dependencies locally
pip install -r ../requirements.txt -t .

# Create ZIP file
zip -r ../alexa-skill.zip .

cd ..
```

### Step 2: Create Lambda Function in AWS Console

1. Go to AWS Lambda Console (https://console.aws.amazon.com/lambda)
2. Click "Create function"
3. Choose "Author from scratch"
4. Name: `ask-custom-skill` (or your preferred name)
5. Runtime: Python 3.9
6. Role: Create new role with basic Lambda execution permissions

### Step 3: Upload Code

In the Lambda function:

1. **Code upload**:
   - Click "Upload from" → ".zip file"
   - Select `alexa-skill.zip`
   - Click "Save"

2. **Handler**:
   - Set to: `lambda_function.lambda_handler`

3. **Environment variables**:
   - Add from your `.env` file:
     - `API_URL`: `http://api-youth.lthome.us`
     - `API_TIMEOUT`: `10`
     - `ALEXA_SKILL_ID`: (your skill ID)
     - `ENVIRONMENT`: `development`
     - `DEBUG`: `false`

4. **Timeout**:
   - Increase to 30 seconds (from default 3)
   - This accommodates API latency

5. **VPC** (if needed):
   - If API is behind VPN, configure VPC access

### Step 4: Get Lambda ARN

Copy the ARN from the top right of the Lambda console. Looks like:
```
arn:aws:lambda:us-east-1:123456789:function:ask-custom-skill
```

### Step 5: Configure Skill in ASK Developer Console

1. Go to https://developer.amazon.com/alexa/console/ask
2. Create new skill or select existing
3. Choose "Custom" model
4. Go to "Build" → "Endpoint"
5. Choose "AWS Lambda ARN"
6. Paste your Lambda ARN
7. Save

### Step 6: Upload Interaction Model

1. Go to "Build" → "Intents"
2. Use "Code Editor" or "Skill Builder"
3. Copy JSON from `interaction_model.json` into the code editor
4. Click "Save Model"
5. Click "Build Model" (waits 1-2 minutes)

---

## Testing

### Via ASK Console Simulator

1. Go to Alexa Skills Kit console
2. Click "Test" tab
3. Enable testing for development
4. Type or click microphone to test utterances

Example test flow:
```
User: Open Youth Permission Tracker
Alexa: Welcome to Youth Permission Tracker. Are you a parent or a youth?

User: Parent
Alexa: Great! I'm set up for parent mode. To get started, I'll need your 6-digit permission code.

User: 123456
Alexa: Now let's set up a 4-digit PIN to verify permission grants. What PIN would you like to use?

User: 1234
Alexa: Your PIN is set. You're all set to use the skill...
```

### Via Alexa Device

1. Enable testing on the skill
2. Say "Alexa, open youth permission tracker" on your Alexa device
3. Follow the setup flow

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests
python -m pytest test_skill.py

# Or with unittest
python -m unittest test_skill.py
```

---

## Troubleshooting

### Lambda Function Not Responding

**Error**: "The request to the remote Alexa service failed"

**Solutions**:
1. Check Lambda CloudWatch logs:
   ```bash
   aws logs tail /aws/lambda/ask-custom-skill --follow
   ```
2. Verify handler is set correctly: `lambda_function.lambda_handler`
3. Check environment variables are set
4. Verify Lambda has internet access (not in restrictive VPC)

### API Connection Issues

**Error**: "I'm having trouble connecting to the service"

**Solutions**:
1. Verify API URL is correct in `.env`
2. Test API accessibility from Lambda:
   ```bash
   curl http://api-youth.lthome.us/activities-all
   ```
3. Check CORS settings on API (should allow Lambda IPs)
4. Increase timeout if API is slow:
   - In Lambda: increase timeout to 30+ seconds
   - In constants.py: increase API_TIMEOUT

### Permission Code Not Recognized

**Solutions**:
1. Verify permission code format (6 digits)
2. Test permission code directly with API:
   ```bash
   curl "http://api-youth.lthome.us/activities-all-parents?permission_code=123456"
   ```
3. Check that code exists in `youth_medical` table
4. Verify code is for the correct youth

### Interaction Model Not Updating

**Solutions**:
1. Rebuild model after updating:
   - Console: Click "Build Model" button
   - ASK CLI: `ask deploy`
2. Clear browser cache and refresh
3. Wait 2-3 minutes for model to rebuild
4. Check for JSON syntax errors in interaction model

---

## Updating After Deployment

### Code Changes

```bash
# ASK CLI
ask deploy

# Manual
zip -r alexa-skill.zip lambda_function.py utils/ models/ api/ intents/
# Upload via AWS Lambda console
```

### Interaction Model Changes

1. Update `interaction_model.json`
2. Upload to ASK Developer Console
3. Click "Build Model"

### Environment Variable Changes

1. Update in Lambda console or `.env`
2. Changes take effect immediately

---

## Monitoring

### CloudWatch Logs

```bash
# View logs in real-time
aws logs tail /aws/lambda/ask-custom-skill --follow

# View specific time range
aws logs get-log-events \
  --log-group-name /aws/lambda/ask-custom-skill \
  --log-stream-name 2024/01/15/[\$LATEST]xxxxx \
  --start-time $(date -d '1 hour ago' +%s)000
```

### Debug Logging

Set `DEBUG=true` in Lambda environment variables to get detailed logs:

```
INFO - User type detected: parent
DEBUG - Permission code validated: 12****
INFO - Retrieved 3 activities
DEBUG - Formatted activity list for voice output
```

---

## Best Practices

1. **Use Lambda Layers** for dependencies (advanced):
   - Keeps code smaller
   - Faster deployments
   - Easier to update libraries

2. **Add API Caching** if frequent queries:
   - Cache activity lists in session
   - Reduce API calls

3. **Monitor Costs**:
   - Lambda free tier: 1M requests/month
   - Each skill invocation = ~1 Lambda invocation
   - Monitor CloudWatch for usage spikes

4. **Version Control**:
   - Keep interaction model in git
   - Tag releases after deployment
   - Document API changes

5. **Backup**:
   - Download skill configuration periodically
   - Version control `.env` template
   - Document custom intents

---

## Rollback

If deployment causes issues:

### Roll Back Lambda Code

```bash
# View function versions
aws lambda list-versions-by-function --function-name ask-custom-skill

# Deploy previous version
aws lambda update-function-code \
  --function-name ask-custom-skill \
  --zip-file fileb://previous-deployment.zip
```

### Roll Back Interaction Model

1. Go to ASK console
2. Click "View History"
3. Select previous version
4. Click "Restore"

---

## Support

For issues:
1. Check CloudWatch logs for error messages
2. Test API endpoints directly
3. Review this guide's Troubleshooting section
4. Check ASK Developer Forum: https://forums.developer.amazon.com/
