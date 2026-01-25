# youth-permission-tracker
*Youth permission &amp; medical form tracker*

## Overview

The system will allow youth leaders to create an activity and track requisite forms.  At this point they can select which individuals, or groups, to be included in the activity.  At this stage the information about the activity will be entered (e.g dates, location, description of the activity, adult leaders from a multi-select option).  When the activity is then submitted (viz created) an electronic notification is then sent to the guardian of each youth invited.  This email gives some information about the activity and includes a hyperlink.  This link takes the guardian to a page where they can electronically sign to give permission as well as ask medical information.  Youth leaders will be able to track compliance on a separate page which will show the activity, who was invited and for which individuals are forms extant.  It will also show if any supervisory signatures, and required credentials, are needed and if they are required.  It will also include "alerts", such as allergies or potential medical limitations of any participants to an activity.

Front end is a website.  Backend is REST API and relational database.

# Website
## Pages
### Youth Pages
- Creates adult leaders, youth, groups and their guardian's contact information
- Create adult leaders who can access health information and create activities
- Guardian setup (2FA and unique pin for digital signing)
### Parent Pages
### Leader Pages
### Admin Pages

# Database
Current version uses SQLITE as the backend db.  
erDiagram
  INTEREST_SURVEY {
    INTEGER id PK
    TEXT youth_id
    TEXT interests "JSON string"
    TEXT org_group
    TEXT submitted_at
    TEXT created_at
  }

  CONCERN_SURVEY {
    INTEGER id PK
    TEXT concerns "JSON string"
    TEXT org_group
    TEXT submitted_at
    TEXT created_at
  }

  ADMIN_USERS {
    INTEGER id PK
    TEXT username "UNIQUE"
    TEXT password
    TEXT role
    TEXT org_group
    TEXT created_at
  }

  VISITS {
    INTEGER id PK
    TEXT created_at
  }

  YOUTH_MEDICAL {
    TEXT youth_id PK
    TEXT permission_code
    TEXT youth
    TEXT parent_guardian
    TEXT medical
    TEXT emergency_contact
    TEXT signature
    TEXT signed_at
    TEXT created_at
    TEXT updated_at
  }

  ACTIVITIES {
    INTEGER id PK
    TEXT activity_id "UNIQUE"
    TEXT activity_name
    TEXT description
    TEXT location
    TEXT budget
    REAL total_cost
    REAL actual_cost
    TEXT participants_youth_ids
    TEXT groups
    TEXT drivers
    datetime date_start
    datetime date_end
    INTEGER is_overnight
    INTEGER is_coed
    INTEGER requires_permission
    TEXT thoughts
    INTEGER bishop_approval
    TEXT bishop_approval_date
    INTEGER stake_approval
    TEXT stake_approval_date
    TEXT created_at
  }

  PERMISSION_GIVEN {
    INTEGER id PK
    TEXT youth_id
    TEXT activity_id
    TEXT permission_code
    JSON data
    TEXT created_at
  }

  AUDIT_LOG {
    INTEGER id PK
    TEXT ts
    TEXT actor_username
    TEXT actor_role
    TEXT action
    TEXT resource_type
    TEXT resource_id
    INTEGER success
    TEXT details
    TEXT client_ip
    TEXT user_agent
  }

  %% Logical relationships (not enforced by foreign keys in the DDL)
  YOUTH_MEDICAL ||--o{ INTEREST_SURVEY : "youth_id (logical)"
  YOUTH_MEDICAL ||--o{ PERMISSION_GIVEN : "youth_id (logical)"
  ACTIVITIES   ||--o{ PERMISSION_GIVEN : "activity_id (logical)"
  YOUTH_MEDICAL ||--o{ PERMISSION_GIVEN : "permission_code (logical)"
  ADMIN_USERS  ||--o{ AUDIT_LOG : "actor_username (logical)"


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
View [local setup file](./manual-startup.md)

###  Testing
Unit tests are located in /tests.  
- Make sure required test libraries are installed (test-requirements.txt)
- Run with `pytest --cov=api tests/`
- To run from docker `docker compose exec app pytest --cov=api --cov-report=term-missing`
To reset the database use api/reset_db.py.  From inside api folder run `python reset_db.py`


## Security & Compliance
**Hippa**
Per HIPPA adult users will be required to use credentials in order to access health information.  Credentials will be stored hashed and salted.  PHI will be stored in a table separate from PII.  A UID will be used to correlate PII to PHI.
HIPAA requires (not optional):
* Access controls
* Audit logs
* Encryption
* Risk assessments
* Written policies & training

**Signing**
- 2FA and unique guardian code for signing
- Audit Trail: Keep detailed logs (IP address, timestamp, device info, consent).
- Consent to Sign Electronically: Present a checkbox or agreement before signing.
- Document Integrity: Lock the document post-signature (no edits).

### Technical Security Controls (HIPAA Security Rule core)
**A. Encryption (Non-Negotiable)**
At Rest
* AES-256
* Encrypted disks, databases, backups
* Separate key management (KMS / HSM)

In Transit
* TLS 1.2+ (prefer 1.3)
* mTLS for internal services
* No plaintext APIs

**B. Identity & Access Management (IAM)**
* Principle of Least Privilege
* Role-based access (RBAC)
* Attribute-based access (ABAC) for PHI
* No shared accounts
* Authentication
* MFA for all admin access
* MFA for clinicians/users accessing PHI
* Strong password policies

**C. Audit Logging (HIPAA requires this)**
Logging
* Who accessed PHI
* What was accessed
* When
* From where
* What was changed

Logs must be:
* Tamper-resistant
* Retained per policy (often 6+ years)
* Monitored for anomalies

**D. Application-Level Protections**
* Secure Development Practices
* Input validation everywhere
* Parameterized queries (no SQL injection)
* Secure file upload handling
* Strict CORS rules
* Rate limiting & abuse detection
* Session & Token Security
* Short-lived access tokens
* Refresh token rotation
* Secure cookies (HttpOnly, Secure, SameSite)

**E. Infrastructure & Hosting Compliance**
Hosting Environment Must Be:
* Hardened OS images
* Regular patching
* Network segmentation
* Firewalls & WAFs
* Intrusion detection (IDS/IPS)
 
**F. Data Lifecycle Management**
* Data Minimization
* Collect only what you need
* Avoid “future use” hoarding
* Retention Policies
* Define retention period per data type
* Auto-delete after expiration
* Secure deletion (crypto-shred)

Backups
* Encrypted
* Access-controlled

Tested restores
* Same compliance level as primary data

**G. Incident Response & Breach Handling**
HIPAA expects:
* Written incident response plan
* Defined escalation paths
* Breach assessment procedures
* Timelines for notification (as short as 60 days)
* You must assume breach will happen and plan accordingly.

**H. Administrative Safeguards**
You need:
* Security officer designation
* Software use & HIPAA training
* Vendor risk assessments
* Business Associate Agreements
* Annual risk analysis documentation
⚠️ Lack of paperwork alone can cause penalties, even without a breach.

**I. Architecture Patterns That Reduce Risk**
Recommended Patterns
* Split-system architecture
* Identity service separate from health data
* Tokenization
* Replace PHI with tokens in most services
* Zero Trust networking
* Read-only replicas for analytics
* Air-gapped backups

Avoid
* Monolithic databases with mixed data
* Shared admin credentials
* Logging PHI by accident
* Dev/test environments with real data

## Practical Compliance Checklist
Minimum baseline before production
- [ ] Legal determination: HIPAA / GDPR applicability
- [ ] Threat model & risk assessment
- [ ] Encryption everywhere
- [ ] RBAC + MFA
- [ ] Audit logging
- [ ] Secure backups
- [ ] Incident response plan
- [ ] Vendor BAAs
- [ ] Written policies
- [ ] User training

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

