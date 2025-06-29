# youth-permission-tracker
*Youth permission &amp; medical form tracker*

## Overview

The system will allow youth leaders to create an activity and track requisite forms.  At this point they can select which individuals, or groups, to be included in the activity.  At this stage the information about the activity will be entered (e.g dates, location, description of the activity, adult leaders from a multi-select option).  When the activity is then submitted (viz created) an electronic notification is then sent to the guardian of each youth invited.  This email gives some information about the activity and includes a hyperlink.  This link takes the guardian to a page where they can electronically sign to give permission as well as ask medical information.  Youth leaders will be able to track compliance on a separate page which will show the activity, who was invited and for which individuals are forms extant.  It will also show if any supervisory signatures, and required credentials, are needed and if they are required.  It will also include "alerts", such as allergies or potential medical limitations of any participants to an activity.

## Pages
### User Management
- Creates adult leaders, youth, groups and their guardian's contact information
- Create adult leaders who can access health information and create activities
- Guardian setup (2FA and unique pin for digital signing)
### Activity Creation
- Can create an activity.  Risk events are identified (e.g. aquatics, climbing, etc), dates of the activity, information about the activity, drivers are identified
- Can submit activity for approval (supervisory and guardians)
### Guardian Signing
- Guardian receives a unique link for the activity and their child (each child)
- Form information is prefilled based on activity information
- Child information is prefilled based on previous form information to reduce time typing
### Activity Tracking
- Per activity one can view who was invited and whose guardians have submitted approval.
- Can view aggregated list of "risks" (e.g. allergies, physical limitations, guardian's notes)
- Can view is supervisory signatures have been obtained
- Can view is requisite trainings are achieved
- Can re-request approvals from those from whom an approval is missing


## Local Setup
1. Update migrate.sh (as needed)
2. Update docker-compose env info
3. Update api/.env file
4. Run docker-compose `docker-compose up`

###  Testing
Unit tests are located in /tests.  
- Make sure required test libraries are installed (test-requirements.txt)
- Run with `pytest --cov=api tests/`
- To run from docker `docker compose exec app pytest --cov=api --cov-report=term-missing`
To reset the database use api/reset_db.py.  From inside api folder run `python reset_db.py`


## Security & Compliance
**Hippa**
Per HIPPA adult users will be required to use credentials in order to access health information.  Credentials will be stored hashed and salted.  PHI will be stored in a table separate from PII.  A UID will be used to correlate PII to PHI.

**Signing**
- 2FA and unique guardian code for signing
- Audit Trail: Keep detailed logs (IP address, timestamp, device info, consent).
- Consent to Sign Electronically: Present a checkbox or agreement before signing.
- Document Integrity: Lock the document post-signature (no edits).

**Safety**
Depending on the nature of the activity corresponding training/certifications will be automatically identified.

**Supervisory Permissions**
Persuant the handbook all activity requests will be sent to the Bishop for approval.  All activities which are co-ed or of *n* distance from the home ward will also require Stake Presidency approval.  These individuals will receive an electronic notification with a link which will describe the activity and allow for an electronic signature.  

## Versions
- 1.0:  Activity creation and approval tracking
- 1.1:  Activity Resource Page (individuals: trainings, certs, equipment, skills), can be sent to members to fill out; Activity Planning (purpose, description, how meet purpose, resources, budget, youth president approval)
- 1.2:  Attendance & reporting

## Architecture
- REST API:  Python with FASTAPI framework
- DB: MYSQL db
- Web Pages: HTML 5, CSS, JS
- Environment:  Containerized (Docker)
### Digital Signing
1. Identity Verification (KYC)
- Before signing, verify the user’s identity
- Basic SES: Email confirmation or 2FA
- AES/QES: Government-issued ID + liveness test
2. Capture the Signature
- Drawn signature using a touchscreen or mouse.
- Typed name with a selected font.
- Upload an image of signature.
- You can store the signature image or render it onto the document (e.g., with reportlab, PDFLib, or pdf-lib.js).
3.  Cryptographic Binding
- Digitally bind the signature to the document so it’s tamper-evident
- Use public key cryptography (PKI).
- Hash the PDF document (SHA256), sign the hash with the private key of the signer.
- Embed signature + certificate into the PDF's metadata.
4. Timestamp
- Add a timestamp token from a Time Stamp Authority (TSA) for non-repudiation.

# Run Program
1. Make sure that alembic/alembic.ini file uses `sqlalchemy.url = mysql+mysqlconnector://${DB_USER}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}` instead of `sqlalchemy.url = driver://user:pass@host/dbname`
    This file is created with: `alembic init alembic`
2. 

