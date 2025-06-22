# youth-permission-tracker
Youth permission &amp; medical form tracker

## Overview

The system will allow youth leaders to create an activity and track requisit forms.  At this point they can select which individuals, or groups, to be included in the activity.  At this stage the information about the activity will be entered (e.g dates, location, description of the activity, adult leaders from a mult-select option).  When the activity is then submitted (viz created) an electronic notification is then sent to the guardian of each youth invited.  This email gives some information about the activity and includes a hyperlink.  This link takes the guardian to a page where they can electronically sign to give permission as well as ask medical information.  Youth leaders will be able to track compliance on a seperate page which will show the activity, who was invited and for which individuals are forms extant.  It will also show if any supervisotry signatures, and required credentials, are needed and if they are aquired.  It will also include "alerts", such as allergies or potential medical limitations of any participants to an activity.

### Security & Compliance
-- **Hippa**
Per HIPPA adult users will be required to use credentials in order to access health information.  Credentials will be stored hashed and salted.  Medical information will be stored in a table separate from PII.  UID will be used to correlate PII to health information
-- **Safety**
Depending on the nature of the activity corresponding training/certifications will be automatically identified.
-- **Supervisory Permissions**
Persuant the handbook all activity requests will be sent to the Bishop for approval.  All activities which are co-ed or of *n* distance from the home ward will also require Stake Presidency approval.  These individuals will receive an electronic notification with a link which will describe the activity and allow for an electronic siganture.  
