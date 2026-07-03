# Youth Data Editor - Usage Guide

## Overview

The Youth Data Editor (`youth_editor.html`) is a web interface that allows you to:
- Search for youth by last name and/or permission code
- View and edit all available information (birth date, parent/guardian, medical, emergency contact)
- Capture signatures using a canvas-based drawing tool
- Save all changes back to `youth_data.json`

## Getting Started

### 1. Start the API Server

From the workspace root:
```bash
python run_local.py
```

Or directly with uvicorn:
```bash
cd api_base
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

The API will be available at `http://localhost:5000` (or `http://localhost:8000` depending on your setup).

### 2. Access the Web Editor

**Option A: Via Static File Serving**
If your API serves static files, place or link `youth_editor.html`:
```
http://localhost:5000/youth_editor.html
```

**Option B: Direct File Access (for testing)**
Open the file directly in your browser:
```
file:///path/to/youth-permission-tracker/file_load/youth_editor.html
```

**Option C: Copy to Website Directory**
Copy the file to the website folder:
```bash
cp file_load/youth_editor.html website/
```
Then access via the web server.

## Using the Editor

### Search for a Youth

1. Enter the youth's **Last Name** (e.g., "Cahoon")
   - Search is case-insensitive
   - Can search by last name alone

2. Optionally enter **Permission Code** (e.g., "072709")
   - Format: 6 digits (MMDDYY)
   - Can search by permission code alone if first_name/last_name search would be ambiguous

3. Click **Search**
   - Youth info will display with editable form below
   - Status message confirms "Youth found!"

4. To start over, click **Clear**

### Edit Youth Information

The editor displays the following sections:

#### Basic Information
- **Permission Code**: Read-only (for reference)
- **Birth Date**: Edit to add or update birth date
  - Format: YYYY-MM-DD
  - Generates permission code if changed

#### Parent / Guardian Information
- **Name**: Parent/guardian full name
- **Relationship**: e.g., "Father", "Mother", "Grandmother"
- **Phone**: Contact phone number
- **Email**: Contact email address

#### Medical Information
- **Conditions**: Any medical conditions (e.g., "asthma, diabetes")
- **Medications**: Medications they take
- **Allergies**: Known allergies
- **Dietary Restrictions**: e.g., "vegetarian", "gluten-free"
- **Limitations**: Physical limitations or restrictions
- **Special Accommodations**: Any special needs

#### Emergency Contact
- **Name**: Emergency contact person's name
- **Phone**: Emergency contact phone number

#### Signature
- **Signed By**: Name of person signing (usually same as youth name)
- **Signature Canvas**: 
  - Draw your signature in the white box
  - Use mouse or touch on mobile devices
  - **Clear**: Erase entire signature
  - **Undo**: Undo last stroke

### Save Changes

1. Complete all editable fields
2. Draw signature in the canvas (or leave blank to keep as "missing")
3. Click **Save Changes**
   - Status message shows success/error
   - If successful, form clears and you can search for another youth
   - Changes are immediately written to `youth_data.json`

4. If you want to cancel without saving, click **Cancel**

## Data Format

### What Gets Saved

All updates are saved with the following structure:
- **Phase 1 (Extracted from PDF)**: first_name, last_name, age, gender, group, permission_code
- **Phase 2 (Filled via Editor)**: birth_date, parent_guardian, medical, emergency_contact, signature, signed_at

### Missing Data Placeholder

Fields left blank are saved as `"missing"` to distinguish from intentionally blank fields.

### Signature Data

Signatures are stored as:
- **signed_by**: Name of person who signed
- **signature_image_base64**: PNG image as base64 data URL
- **signed_at**: ISO 8601 timestamp of when data was saved

## Data Persistence

All changes are written directly to:
```
file_load/youth_data.json
```

Make sure this file is not locked by other processes before saving.

## Troubleshooting

### "Error loading youth data"
- **Cause**: API server not running or youth_data.json not found
- **Fix**: 
  1. Ensure API is running: `python run_local.py`
  2. Check that `file_load/youth_data.json` exists
  3. Check browser console for more details (F12 → Console tab)

### "Youth not found"
- **Cause**: Youth name/permission code combination doesn't match
- **Fix**:
  1. Check spelling of last name (case-insensitive, but characters must match)
  2. Verify permission code format (6 digits, e.g., "072709")
  3. Try searching by just last name without permission code

### "Error saving: Youth not found in database"
- **Cause**: Youth record changed or deleted after search
- **Fix**: 
  1. Search again to reload current data
  2. Check that youth_data.json hasn't been modified
  3. Check file permissions (file must be writable)

### "Permission denied" on save
- **Cause**: File is read-only or locked by another process
- **Fix**:
  1. Close any other programs editing youth_data.json
  2. Check file permissions: `file_load/youth_data.json`
  3. Ensure the API process has write access to the directory

### Signature not saving
- **Cause**: Canvas may not have drawn properly or JavaScript error
- **Fix**:
  1. Check browser console (F12 → Console tab) for errors
  2. Try drawing again with clear strokes
  3. Refresh page and search again

## Browser Support

Works on:
- Chrome/Chromium (desktop and mobile)
- Firefox (desktop and mobile)
- Safari (desktop and mobile)
- Edge

Touch/stylus signature drawing supported on all platforms.

## Advanced: Adding to Static Files

To serve the editor from your API, add to `api_base/main.py`:

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Mount static files
static_dir = Path(__file__).parent.parent / "file_load"
app.mount("/editor", StaticFiles(directory=static_dir, html=True), name="editor")
```

Then access at: `http://localhost:5000/editor/youth_editor.html`

## For Administrators

### Backup Before Editing
```bash
# Create backup before allowing mass edits
cp file_load/youth_data.json file_load/youth_data.json.backup
```

### View All Changes
```bash
# See what changed since last backup
diff file_load/youth_data.json.backup file_load/youth_data.json
```

### Restore from Backup
```bash
# If something goes wrong
cp file_load/youth_data.json.backup file_load/youth_data.json
```

## Statistics

Currently **40 youth** in system:
- **19 males**: 10 Priests, 9 Teachers
- **21 females**: YW group
- **25 with birth dates**: Permission codes generated
- **15 without birth dates**: Permission code shows "missing"

All 40 youth ready for Phase 2 data completion via this editor.
